import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_event, get_current_admin
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.admin import Admin
from app.models.enums import EventMode, EventStatus, ParticipantTaskStatus, SelfieStatus
from app.models.event import Event
from app.models.leaderboard import Leaderboard
from app.models.match import Match
from app.models.participant import Participant, ParticipantTask
from app.models.selfie import Selfie
from app.schemas.common import ok
from app.schemas.event import (
    EventCreateRequest,
    EventCreateResponse,
    EventDetailOut,
    EventOut,
    EventSettingsOut,
    EventUpdateRequest,
)
from app.schemas.participant import AdminParticipantBulkRequest, AdminParticipantCreate
from app.services import event_management as event_mgmt
from app.services import events as event_service
from app.services.event_management import build_join_url
from app.services.participant_registration import (
    RegistrationError,
    admin_register_participant,
    admin_register_participants_bulk,
)
from app.services.qr import generate_qr_data_url

router = APIRouter()
logger = logging.getLogger(__name__)


def _handle_service_error(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


@router.get("/events")
async def list_events(
    status_filter: EventStatus | None = Query(None, alias="status"),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    events = await event_service.list_events(db, status_filter)
    return ok([EventOut.model_validate(e).model_dump() for e in events])


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def create_event(
    body: EventCreateRequest,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await event_mgmt.create_event_managed(db, body, admin.id)
    except AppError as e:
        raise _handle_service_error(e) from e
    except ValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()) from e

    response = EventCreateResponse(
        event=EventOut.model_validate(result["event"]),
        settings=EventSettingsOut.model_validate(result["settings"]),
        join_url=result["join_url"],
        qr_code_data_url=result["qr_code_data_url"],
        tasks_created=result["tasks_created"],
    )
    return ok(response.model_dump())


@router.get("/events/{event_id}")
async def get_event(
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    detail = await event_mgmt.get_event_detail(db, event)
    event_out = EventOut.model_validate(detail["event"]).model_dump()
    settings_out = (
        EventSettingsOut.model_validate(detail["settings"]).model_dump()
        if detail["settings"]
        else None
    )
    return ok(
        EventDetailOut(
            **event_out,
            settings=settings_out,
            join_url=detail["join_url"],
            qr_code_data_url=detail["qr_code_data_url"],
            participant_count=detail["participant_count"],
            tasks_count=detail["tasks_count"],
        ).model_dump()
    )


@router.get("/events/{event_id}/join-assets")
async def get_join_assets(
    event: Event = Depends(get_admin_event),
):
    join_url = build_join_url(event.code)
    return ok(
        {
            "code": event.code,
            "join_url": join_url,
            "qr_code_data_url": generate_qr_data_url(join_url),
        }
    )


@router.patch("/events/{event_id}")
async def patch_event(
    body: EventUpdateRequest,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    try:
        updated = await event_mgmt.update_event_managed(db, event, body)
    except AppError as e:
        raise _handle_service_error(e) from e
    detail = await event_mgmt.get_event_detail(db, updated)
    event_out = EventOut.model_validate(detail["event"]).model_dump()
    return ok(
        EventDetailOut(
            **event_out,
            settings=EventSettingsOut.model_validate(detail["settings"]).model_dump()
            if detail["settings"]
            else None,
            join_url=detail["join_url"],
            qr_code_data_url=detail["qr_code_data_url"],
            participant_count=detail["participant_count"],
            tasks_count=detail["tasks_count"],
        ).model_dump()
    )


@router.post("/events/{event_id}/start")
async def start_event(
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    event.status = EventStatus.LIVE
    if not event.starts_at:
        from datetime import datetime, timezone

        event.starts_at = datetime.now(timezone.utc)
    await db.flush()
    try:
        from app.services.ws_events import emit_event_started

        await emit_event_started(event.id, event_name=event.name, mode=event.mode.value)
    except Exception as exc:
        logger.warning("event_started broadcast failed for event %s: %s", event.id, exc)
    detail = await event_mgmt.get_event_detail(db, event)
    return ok(EventOut.model_validate(detail["event"]).model_dump())


@router.post("/events/{event_id}/pause")
async def pause_event(
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    """Pause live event (returns to scheduled) and notify clients."""
    from app.services.ws_events import emit_event_paused

    if event.status != EventStatus.LIVE:
        from fastapi import HTTPException

        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Event is not live")
    event.status = EventStatus.SCHEDULED
    await db.flush()
    await emit_event_paused(event.id, event_name=event.name, reason="admin_pause")
    return ok(EventOut.model_validate(event).model_dump())


@router.post("/events/{event_id}/end")
async def end_event(
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    from app.services.awards import calculate_awards
    from app.services.event_settings import get_settings_for_event
    from app.services.leaderboard import (
        calculate_podium,
        calculate_winner,
        recalculate_ranks,
    )

    event.status = EventStatus.ENDED
    await db.flush()
    winner = None
    podium: list[dict] = []
    awards: list[dict] = []
    if event.mode == EventMode.COMPETITION:
        await recalculate_ranks(db, event.id, notify=False)
        winner = await calculate_winner(db, event.id)
        podium = await calculate_podium(db, event.id, size=3)
        settings = await get_settings_for_event(db, event.id)
        if settings and settings.enable_awards:
            awards = await calculate_awards(db, event.id)
    from app.services.ws_events import emit_event_ended

    await emit_event_ended(
        event.id,
        event_name=event.name,
        winner=winner,
        podium=podium,
        awards=awards,
    )
    return ok(
        {
            "event": EventOut.model_validate(event).model_dump(),
            "winner": winner,
            "podium": podium,
            "awards": awards,
        }
    )


@router.get("/events/{event_id}/leaderboard")
async def admin_leaderboard(
    limit: int = Query(50, ge=1, le=200),
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    if event.mode != EventMode.COMPETITION:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Leaderboard is only available for competition events",
        )
    from app.services.leaderboard import get_leaderboard
    from app.schemas.participant import LeaderboardEntry

    board = await get_leaderboard(db, event.id, limit=limit)
    return ok([LeaderboardEntry(**row).model_dump() for row in board])


@router.get("/events/{event_id}/awards")
async def admin_awards(
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    if event.mode != EventMode.COMPETITION:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Awards are only available for competition events",
        )
    from app.services.awards import list_awards

    return ok(await list_awards(db, event.id))


@router.get("/events/{event_id}/participants")
async def list_participants(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=500),
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.common import Meta

    total = await db.scalar(
        select(func.count(Participant.id)).where(Participant.event_id == event.id)
    )
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Participant, Leaderboard)
        .outerjoin(
            Leaderboard,
            (Leaderboard.participant_id == Participant.id) & (Leaderboard.event_id == event.id),
        )
        .where(Participant.event_id == event.id, Participant.is_active.is_(True))
        .order_by(Participant.display_name.asc())
        .offset(offset)
        .limit(per_page)
    )
    rows = result.all()
    from app.services.session import sessions_are_active

    signed_in_map = await sessions_are_active([p.session_token for p, _ in rows])
    items = []
    for p, lb in rows:
        items.append(
            {
                "id": p.id,
                "display_name": p.display_name,
                "email": p.email,
                "company": p.company,
                "score": lb.score if lb else 0,
                "rank": lb.rank if lb else None,
                "tasks_completed_count": p.tasks_completed_count,
                "matches_count": p.matches_count,
                "progress_percent": float(p.progress_percent),
                "joined_at": p.joined_at.isoformat() if p.joined_at else None,
                "signed_in": signed_in_map.get(p.session_token, False),
            }
        )
    return ok(items, meta=Meta(page=page, per_page=per_page, total=int(total or 0)))


@router.post("/events/{event_id}/participants", status_code=status.HTTP_201_CREATED)
async def register_participant(
    body: AdminParticipantCreate,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    from app.models.enums import ActivityType
    from app.services.activity import log_activity

    try:
        participant = await admin_register_participant(
            db,
            event,
            body.display_name,
            body.email,
            body.company,
        )
    except RegistrationError as e:
        raise _handle_service_error(e) from e

    await log_activity(
        db,
        event.id,
        ActivityType.PARTICIPANT_JOINED,
        participant.id,
        {"display_name": participant.display_name, "registered_by": "admin"},
        summary=f"{participant.display_name} added to roster",
    )
    return ok(
        {
            "id": participant.id,
            "display_name": participant.display_name,
            "email": participant.email,
            "company": participant.company,
            "signed_in": False,
        }
    )


@router.post("/events/{event_id}/participants/bulk")
async def register_participants_bulk(
    body: AdminParticipantBulkRequest,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    from app.models.enums import ActivityType
    from app.services.activity import log_activity

    try:
        result = await admin_register_participants_bulk(db, event, body.text)
    except RegistrationError as e:
        raise _handle_service_error(e) from e

    for row in result["created"]:
        await log_activity(
            db,
            event.id,
            ActivityType.PARTICIPANT_JOINED,
            row["id"],
            {"display_name": row["display_name"], "registered_by": "admin"},
            summary=f"{row['display_name']} added to roster",
        )
    return ok(result)


@router.get("/events/{event_id}/activity")
async def activity_feed(
    limit: int = Query(50, ge=1, le=200),
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.event_id == event.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    )
    items = [
        {
            "id": a.id,
            "type": a.activity_type.value,
            "participant_id": a.participant_id,
            "summary": a.summary,
            "payload": a.payload_json,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in result.scalars().all()
    ]
    return ok(items)


@router.get("/events/{event_id}/gallery")
async def gallery(
    status_filter: SelfieStatus | None = Query(None, alias="status"),
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    q = select(Selfie).where(Selfie.event_id == event.id)
    if status_filter:
        q = q.where(Selfie.status == status_filter)
    result = await db.execute(q.order_by(Selfie.uploaded_at.desc()).limit(100))
    from app.services.selfie_urls import resolve_selfie_urls

    items = []
    for s in result.scalars().all():
        image_url, thumbnail_url = resolve_selfie_urls(s)
        items.append(
            {
                "id": s.id,
                "participant_id": s.participant_id,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "status": s.status.value,
                "uploaded_at": s.uploaded_at.isoformat() if s.uploaded_at else None,
                "captured_at": s.captured_at.isoformat() if s.captured_at else None,
            }
        )
    return ok(items)


@router.get("/events/{event_id}/reports/summary")
async def report_summary(
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    from app.models.enums import EventMode as EM
    from app.services.networking_analytics import get_networking_analytics

    if event.mode == EM.NETWORKING:
        return ok(await get_networking_analytics(db, event))

    stats = await event_service.get_event_stats(db, event.id)
    matches = await db.execute(select(func.count(Match.id)).where(Match.event_id == event.id))
    tasks_done = await db.execute(
        select(func.count(ParticipantTask.id))
        .join(Participant)
        .where(
            Participant.event_id == event.id,
            ParticipantTask.status == ParticipantTaskStatus.COMPLETED,
        )
    )
    from app.services.leaderboard import get_leaderboard

    top_board = await get_leaderboard(db, event.id, limit=5)
    return ok(
        {
            "mode": "competition",
            **stats,
            "total_matches": matches.scalar() or 0,
            "total_tasks_completed": tasks_done.scalar() or 0,
            "leaderboard_top": top_board,
        }
    )


@router.get("/events/{event_id}/analytics/networking")
async def networking_analytics(
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    from app.models.enums import EventMode as EM
    from app.services.networking_analytics import get_networking_analytics

    if event.mode != EM.NETWORKING:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Networking analytics only applies to networking mode events",
        )
    return ok(await get_networking_analytics(db, event))
