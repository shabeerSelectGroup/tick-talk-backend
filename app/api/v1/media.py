from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.participant import Participant
from app.models.selfie import Selfie
from app.models.task import Task
from app.services.image_processing import render_name_sign_card
from app.storage import get_storage_backend
from app.storage.local import LocalStorageBackend

router = APIRouter()


async def _fallback_jpeg(db: AsyncSession, storage_path: str) -> bytes | None:
    """Build a stand-in card when the original file is missing from disk."""
    result = await db.execute(
        select(Selfie, Participant, Task)
        .join(Participant, Selfie.participant_id == Participant.id)
        .outerjoin(Task, Selfie.task_id == Task.id)
        .where(
            or_(
                Selfie.storage_key == storage_path,
                Selfie.thumbnail_storage_key == storage_path,
            )
        )
        .limit(1)
    )
    row = result.first()
    if not row:
        return None
    selfie, participant, task = row
    meta = selfie.metadata_json or {}
    name = str(meta.get("partner_name") or participant.display_name or "Guest").strip()
    subtitle = task.title if task else None
    return render_name_sign_card(name, subtitle)


@router.get("/media/{storage_path:path}")
async def serve_local_media(storage_path: str, db: AsyncSession = Depends(get_db)):
    """Serve files from local storage backend (development)."""
    storage = get_storage_backend()
    if not isinstance(storage, LocalStorageBackend):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        path = storage.resolve_path(storage_path)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found") from None
    if path.is_file():
        media_type = "image/png" if storage_path.endswith(".png") else "image/jpeg"
        return FileResponse(
            path, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"}
        )

    fallback = await _fallback_jpeg(db, storage_path)
    if fallback:
        return Response(
            content=fallback,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-cache"},
        )
    raise HTTPException(status_code=404, detail="Not found")
