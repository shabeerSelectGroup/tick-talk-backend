"""Selfie upload orchestration: process, store on R2/local, persist metadata, link match."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.match import Match
from app.models.selfie import Selfie
from app.models.participant import Participant
from app.services.image_processing import ImageProcessingError, process_selfie_image
from app.storage import get_storage_backend
from app.storage.base import StorageError
from app.storage.r2 import R2StorageBackend


class SelfieStorageError(AppError):
    pass


@dataclass
class SelfieUploadContext:
    event_id: int
    participant_id: int
    task_id: int | None = None
    match_id: int | None = None
    partner_id: int | None = None
    participant_task_id: int | None = None


@dataclass
class SelfieUploadResult:
    selfie_id: int
    image_url: str
    thumbnail_url: str
    storage_key: str
    thumbnail_storage_key: str
    match_id: int | None
    metadata: dict


async def _resolve_match(
    db: AsyncSession, participant: Participant, match_id: int | None
) -> Match | None:
    if not match_id:
        return None
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            Match.event_id == participant.event_id,
            Match.initiator_id == participant.id,
        )
    )
    match = result.scalar_one_or_none()
    if not match:
        raise SelfieStorageError(
            "MATCH_NOT_FOUND",
            "Associated match not found or does not belong to you.",
            404,
        )
    return match


def _build_metadata(
    processed,
    *,
    storage_backend: str,
    ctx: SelfieUploadContext,
    image_key: str,
    thumb_key: str,
) -> dict:
    return {
        "storage_backend": storage_backend,
        "image_key": image_key,
        "thumbnail_key": thumb_key,
        "original_size_bytes": processed.original_size_bytes,
        "compressed_size_bytes": processed.compressed_size_bytes,
        "thumbnail_size_bytes": processed.thumbnail_size_bytes,
        "width": processed.width,
        "height": processed.height,
        "thumbnail_width": processed.thumbnail_width,
        "thumbnail_height": processed.thumbnail_height,
        "content_type": processed.content_type,
        "task_id": ctx.task_id,
        "match_id": ctx.match_id,
        "partner_id": ctx.partner_id,
        "participant_task_id": ctx.participant_task_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }


async def _associate_match(db: AsyncSession, match: Match | None, selfie: Selfie) -> None:
    if not match:
        return
    meta = dict(match.metadata_json or {})
    meta["selfie_id"] = selfie.id
    match.metadata_json = meta
    await db.flush()


async def upload_selfie(
    db: AsyncSession,
    participant: Participant,
    image_data: bytes,
    content_type: str | None,
    ctx: SelfieUploadContext,
    *,
    existing_selfie: Selfie | None = None,
) -> SelfieUploadResult:
    """
    Process image, upload full + thumbnail, create/update Selfie row, link match.
    """
    try:
        processed = process_selfie_image(image_data, content_type)
    except ImageProcessingError as e:
        raise SelfieStorageError(e.code, e.message, e.status_code) from e

    storage = get_storage_backend()
    uid = R2StorageBackend.new_object_id()
    image_key, thumb_key = storage.generate_selfie_keys(
        ctx.event_id, ctx.participant_id, uid
    )
    backend_name = "r2" if isinstance(storage, R2StorageBackend) else "local"

    try:
        image_ref = storage.put_object(image_key, processed.image_bytes, processed.content_type)
        thumb_ref = storage.put_object(thumb_key, processed.thumbnail_bytes, processed.content_type)
    except StorageError as e:
        raise SelfieStorageError(e.code, e.message, e.status_code) from e

    match = await _resolve_match(db, participant, ctx.match_id)
    metadata = _build_metadata(
        processed,
        storage_backend=backend_name,
        ctx=ctx,
        image_key=image_key,
        thumb_key=thumb_key,
    )

    now = datetime.now(timezone.utc)
    if existing_selfie:
        if existing_selfie.storage_key and existing_selfie.storage_key != image_key:
            storage.delete_object(existing_selfie.storage_key)
        if existing_selfie.thumbnail_storage_key:
            storage.delete_object(existing_selfie.thumbnail_storage_key)
        selfie = existing_selfie
        selfie.image_url = image_ref.url
        selfie.thumbnail_url = thumb_ref.url
        selfie.storage_key = image_key
        selfie.thumbnail_storage_key = thumb_key
        selfie.metadata_json = metadata
        selfie.match_id = ctx.match_id
        selfie.task_id = ctx.task_id or selfie.task_id
        selfie.captured_at = now
        selfie.uploaded_at = now
    else:
        selfie = Selfie(
            event_id=ctx.event_id,
            participant_id=ctx.participant_id,
            task_id=ctx.task_id,
            match_id=ctx.match_id,
            image_url=image_ref.url,
            thumbnail_url=thumb_ref.url,
            storage_key=image_key,
            thumbnail_storage_key=thumb_key,
            metadata_json=metadata,
            captured_at=now,
        )
        db.add(selfie)

    await db.flush()
    await _associate_match(db, match, selfie)

    return SelfieUploadResult(
        selfie_id=selfie.id,
        image_url=selfie.image_url,
        thumbnail_url=selfie.thumbnail_url or thumb_ref.url,
        storage_key=image_key,
        thumbnail_storage_key=thumb_key,
        match_id=ctx.match_id,
        metadata=metadata,
    )


def delete_selfie_assets(selfie: Selfie) -> None:
    storage = get_storage_backend()
    if selfie.storage_key:
        storage.delete_object(selfie.storage_key)
    if selfie.thumbnail_storage_key:
        storage.delete_object(selfie.thumbnail_storage_key)
