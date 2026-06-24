from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_participant
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.enums import ActivityType, EventMode
from app.models.event import Event
from app.models.leaderboard import Leaderboard
from app.models.participant import Participant
from app.models.selfie import Selfie
from app.schemas.common import ok
from app.schemas.event import EventPublicOut
from app.schemas.participant import (
    BadgeResponse,
    BadgeValidateRequest,
    BadgeValidateResponse,
    JoinPreviewOut,
    JoinRequest,
    JoinResponse,
    LeaderboardEntry,
    ParticipantBadgeOut,
    ParticipantOut,
    ScanRequest,
    ScanResponse,
    TimerResponse,
)
from app.services import participants as participant_service
from app.services.activity import log_activity
from app.services.ws_events import emit_participant_joined, emit_selfie_uploaded
from app.services.badge import BadgeError, build_badge_data, validate_badge_for_scanner
from app.services.join import JoinError, join_participant, validate_event_for_join
from app.services.leaderboard import get_leaderboard
from app.services.qr import generate_qr_png_bytes
from app.services.selfie_storage import SelfieStorageError, SelfieUploadContext, upload_selfie
from app.schemas.push import PushSubscribeRequest, PushUnsubscribeRequest
from app.schemas.selfie import SelfieOut, SelfieUploadOut

router = APIRouter()


def _join_error(exc: JoinError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


async def _participant_out(
    db: AsyncSession, participant: Participant, event: Event | None = None
) -> dict:
    from app.services.event_mode import get_capabilities, sanitize_participant_stats
    from app.services.event_settings import get_settings_for_event

    if event is None:
        result = await db.execute(select(Event).where(Event.id == participant.event_id))
        event = result.scalar_one()
    settings = await get_settings_for_event(db, event.id)
    caps = get_capabilities(event, settings)

    data = ParticipantOut.model_validate(participant).model_dump()
    if caps.scores_enabled:
        lb = await db.execute(
            select(Leaderboard).where(
                Leaderboard.participant_id == participant.id,
                Leaderboard.event_id == participant.event_id,
            )
        )
        entry = lb.scalar_one_or_none()
        data["score"] = entry.score if entry else 0
        data["rank"] = entry.rank if entry else None
    else:
        data["score"] = 0
        data["rank"] = None
    data["progress_percent"] = float(participant.progress_percent)
    data["tasks_completed_count"] = participant.tasks_completed_count
    data["matches_count"] = participant.matches_count

    from app.services.leaderboard import participant_finished_all_tasks

    self_finished = await participant_finished_all_tasks(db, participant)
    data["all_tasks_completed"] = self_finished
    data["leaderboard_available"] = bool(
        event.mode == EventMode.COMPETITION and caps.leaderboard_enabled
    )
    return sanitize_participant_stats(data, caps)


@router.get("/events/{code}")
async def public_event(code: str, db: AsyncSession = Depends(get_db)):
    from app.services.event_presenter import event_public_dict
    from app.services.event_settings import get_settings_for_event
    from app.services.events import get_event_by_code

    event = await get_event_by_code(db, code)
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found")
    settings = await get_settings_for_event(db, event.id)
    return ok(event_public_dict(event, settings))


@router.get("/events/{code}/join-preview")
async def join_preview(code: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func

    from app.models.participant import Participant as P

    try:
        event = await validate_event_for_join(db, code)
        can_join = True
        message = None
    except JoinError as e:
        from app.services.events import get_event_by_code

        event = await get_event_by_code(db, code)
        if not event:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=e.message) from e
        can_join = False
        message = e.message

    count = await db.scalar(
        select(func.count(P.id)).where(P.event_id == event.id, P.is_active.is_(True))
    ) or 0

    from app.services.event_presenter import build_capabilities_out
    from app.services.event_settings import get_settings_for_event

    settings = await get_settings_for_event(db, event.id)
    caps_out = build_capabilities_out(event, settings)

    return ok(
        JoinPreviewOut(
            code=event.code,
            name=event.name,
            description=event.description,
            mode=event.mode,
            status=event.status,
            can_join=can_join,
            message=message,
            participant_count=count,
            max_participants=event.max_participants,
            capabilities=caps_out.model_dump(),
            public_wall_url=caps_out.public_wall_url,
        ).model_dump()
    )


@router.post("/join", status_code=status.HTTP_201_CREATED)
async def join(body: JoinRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await join_participant(
            db,
            body.event_code,
            body.display_name,
            body.email,
            body.company,
        )
    except JoinError as e:
        raise _join_error(e) from e

    participant = result["participant"]
    event = result["event"]

    if not result["resumed"]:
        await log_activity(
            db,
            event.id,
            ActivityType.PARTICIPANT_JOINED,
            participant.id,
            {"display_name": participant.display_name, "email": participant.email},
            summary=f"{participant.display_name} joined",
        )
        await emit_participant_joined(
            event.id,
            participant_id=participant.id,
            display_name=participant.display_name,
            company=participant.company,
        )

    from app.services.event_presenter import build_capabilities_out, event_public_dict
    from app.services.event_settings import get_settings_for_event

    participant_data = await _participant_out(db, participant, event)
    settings = await get_settings_for_event(db, event.id)
    caps_out = build_capabilities_out(event, settings)
    return ok(
        JoinResponse(
            session_token=result["session_token"],
            participant=ParticipantOut(**participant_data),
            event_code=result["event_code"],
            event_id=result["event_id"],
            participant_id=result["participant_id"],
            qr_code=result["qr_code"],
            qr_payload=result["qr_payload"],
            qr_code_data_url=result["qr_code_data_url"],
            resumed=result["resumed"],
            event=event_public_dict(event, settings),
            capabilities=caps_out.model_dump(),
        ).model_dump()
    )


@router.get("/me")
async def me(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    from app.services.event_presenter import build_capabilities_out, event_public_dict
    from app.services.event_settings import get_settings_for_event

    result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = result.scalar_one()
    settings = await get_settings_for_event(db, event.id)
    return ok(
        {
            "participant": await _participant_out(db, participant, event),
            "event": event_public_dict(event, settings),
            "capabilities": build_capabilities_out(event, settings).model_dump(),
        }
    )


@router.get("/tasks")
async def my_tasks(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    tasks = await participant_service.get_participant_tasks(db, participant)
    return ok(tasks)


@router.post("/scan")
async def scan(
    body: ScanRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    try:
        partner, points, already = await participant_service.record_match(
            db, participant, body.qr_token
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    from app.services.event_mode import get_capabilities
    from app.services.event_settings import get_settings_for_event

    result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = result.scalar_one()
    settings = await get_settings_for_event(db, event.id)
    caps = get_capabilities(event, settings)
    display_points = points if caps.show_match_points else 0

    if not already:
        await log_activity(
            db,
            participant.event_id,
            ActivityType.MATCH_CREATED,
            participant.id,
            {"partner_id": partner.id, "partner_name": partner.display_name, "points": display_points},
            summary=f"Connected with {partner.display_name}",
        )

    return ok(
        ScanResponse(
            scanned_name=partner.display_name,
            points_earned=display_points,
            already_scanned=already,
        ).model_dump()
    )


@router.get("/leaderboard")
async def leaderboard(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = result.scalar_one()
    from app.services.event_settings import get_settings_for_event

    ev_settings = await get_settings_for_event(db, event.id)
    if event.mode == EventMode.COMPETITION and (not ev_settings or not ev_settings.leaderboard_enabled):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Leaderboard is disabled for this event")

    board = await get_leaderboard(db, event.id)
    return ok([LeaderboardEntry(**e).model_dump() for e in board])


@router.get("/awards")
async def participant_awards(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    from app.models.enums import EventStatus
    from app.schemas.participant import AwardOut
    from app.services.awards import list_awards
    from app.services.event_settings import get_settings_for_event

    result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = result.scalar_one()
    if event.mode != EventMode.COMPETITION:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Awards are not available in networking mode")
    settings = await get_settings_for_event(db, event.id)
    if not settings or not settings.enable_awards:
        return ok([])
    if event.status != EventStatus.ENDED:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Awards are announced when the event ends",
        )
    rows = await list_awards(db, event.id)
    return ok([AwardOut(**r).model_dump() for r in rows])


async def _badge_out(db: AsyncSession, participant: Participant) -> dict:
    result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = result.scalar_one()
    badge = build_badge_data(participant, event)
    out = ParticipantBadgeOut(
        participant_id=badge.participant_id,
        event_id=badge.event_id,
        event_code=badge.event_code,
        display_name=badge.display_name,
        company=participant.company,
        secure_token=badge.secure_token,
        qr_payload=badge.qr_payload,
        qr_code_data_url=badge.qr_code_data_url,
        version=badge.version,
    )
    return BadgeResponse.from_badge(out).model_dump()


@router.get("/badge")
async def badge(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    return ok(await _badge_out(db, participant))


@router.get("/badge/download")
async def badge_download(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = result.scalar_one()
    badge = build_badge_data(participant, event)
    png = generate_qr_png_bytes(badge.qr_payload, size=512)
    filename = f"ticktalk-badge-{event.code}-{participant.id}.png"
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/badge/validate")
async def badge_validate(
    body: BadgeValidateRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    result = await validate_badge_for_scanner(db, body.qr_payload, participant)
    return ok(BadgeValidateResponse(**result.__dict__).model_dump())


@router.get("/timer")
async def timer(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = result.scalar_one()
    remaining = None
    if event.ends_at:
        now = datetime.now(timezone.utc)
        end = event.ends_at if event.ends_at.tzinfo else event.ends_at.replace(tzinfo=timezone.utc)
        remaining = max(0, int((end - now).total_seconds()))
    return ok(
        TimerResponse(
            status=event.status.value,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            remaining_seconds=remaining,
        ).model_dump()
    )


def _selfie_http_error(exc: SelfieStorageError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.post("/selfies/upload")
async def selfie_upload(
    file: UploadFile = File(...),
    task_id: int | None = None,
    match_id: int | None = None,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Upload selfie with server-side compression, thumbnail, and R2/local storage."""
    data = await file.read()
    ctx = SelfieUploadContext(
        event_id=participant.event_id,
        participant_id=participant.id,
        task_id=task_id,
        match_id=match_id,
    )
    try:
        result = await upload_selfie(db, participant, data, file.content_type, ctx)
    except SelfieStorageError as e:
        raise _selfie_http_error(e) from e

    await log_activity(
        db,
        participant.event_id,
        ActivityType.SELFIE_UPLOADED,
        participant.id,
        {"selfie_id": result.selfie_id, "match_id": result.match_id, "task_id": task_id},
    )
    task_title = None
    if task_id:
        from app.models.task import Task

        t = await db.get(Task, task_id)
        task_title = t.title if t else None
    await emit_selfie_uploaded(
        participant.event_id,
        participant_id=participant.id,
        selfie_id=result.selfie_id,
        task_id=task_id,
        match_id=result.match_id,
        image_url=result.image_url,
        thumbnail_url=result.thumbnail_url,
        display_name=participant.display_name,
        task_title=task_title,
    )
    return ok(
        SelfieUploadOut(
            selfie_id=result.selfie_id,
            image_url=result.image_url,
            thumbnail_url=result.thumbnail_url,
            storage_key=result.storage_key,
            thumbnail_storage_key=result.thumbnail_storage_key,
            match_id=result.match_id,
            direct_upload=True,
            metadata=result.metadata,
        ).model_dump()
    )


@router.post("/selfies/upload-url")
async def selfie_upload_url(
    participant: Participant = Depends(get_current_participant),
):
    """Deprecated — use POST /selfies/upload for processed storage."""
    return ok(
        {
            "direct_upload": True,
            "upload_url": None,
            "message": "Use POST /participant/selfies/upload with multipart file.",
        }
    )


@router.get("/selfies/{selfie_id}")
async def get_selfie(
    selfie_id: int,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Selfie).where(
            Selfie.id == selfie_id,
            Selfie.participant_id == participant.id,
        )
    )
    selfie = result.scalar_one_or_none()
    if not selfie:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Selfie not found")
    return ok(
        SelfieOut(
            id=selfie.id,
            event_id=selfie.event_id,
            participant_id=selfie.participant_id,
            task_id=selfie.task_id,
            match_id=selfie.match_id,
            image_url=selfie.image_url,
            thumbnail_url=selfie.thumbnail_url,
            storage_key=selfie.storage_key,
            status=selfie.status.value,
            metadata=selfie.metadata_json,
            captured_at=selfie.captured_at,
            uploaded_at=selfie.uploaded_at,
        ).model_dump()
    )


@router.post("/selfies/confirm")
async def selfie_confirm(
    selfie_id: int,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Selfie).where(Selfie.id == selfie_id, Selfie.participant_id == participant.id)
    )
    selfie = result.scalar_one_or_none()
    if not selfie:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Selfie not found")
    if not selfie.storage_key or not selfie.thumbnail_storage_key:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Selfie upload not finalized. Use POST /selfies/upload.",
        )
    return ok(
        {
            "selfie_id": selfie.id,
            "status": selfie.status.value,
            "image_url": selfie.image_url,
            "thumbnail_url": selfie.thumbnail_url,
            "match_id": selfie.match_id,
            "metadata": selfie.metadata_json,
            "uploaded_at": selfie.uploaded_at.isoformat() if selfie.uploaded_at else None,
        }
    )


@router.get("/push/config")
async def push_config():
    from app.services.push import get_vapid_public_key, vapid_configured

    key = get_vapid_public_key()
    return ok({"public_key": key or "", "enabled": vapid_configured()})


@router.post("/push/subscribe")
async def push_subscribe(
    body: PushSubscribeRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    from app.services.push import upsert_subscription, vapid_configured

    if not vapid_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Push not configured")
    keys = body.keys
    await upsert_subscription(
        db,
        participant.id,
        endpoint=body.endpoint,
        p256dh=keys.get("p256dh", ""),
        auth=keys.get("auth", ""),
    )
    return ok({"subscribed": True})


@router.post("/push/unsubscribe")
async def push_unsubscribe(
    body: PushUnsubscribeRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.services.push import remove_subscription

    await remove_subscription(db, body.endpoint)
    return ok({"unsubscribed": True})
