from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EventMode, EventStatus, MatchType, ParticipantTaskStatus, SelfieStatus
from app.models.event import Event
from app.models.event_settings import EventSettings
from app.models.match import Match
from app.models.participant import Participant, ParticipantTask
from app.models.selfie import Selfie
from app.models.task import Task
from app.services.leaderboard import add_score, ensure_leaderboard_entry
from app.services.scoring import display_task_points
from app.services.progress import refresh_participant_progress
from app.services.task_presenter import (
    meet_group_index,
    meet_group_total,
    meet_progress_count,
    meet_target_count,
    participant_task_description,
    participant_task_group_label,
    participant_task_instruction,
)
from app.services.session import generate_token, store_session


async def join_event(
    db: AsyncSession,
    event_code: str,
    display_name: str,
    email: str | None = None,
    company: str | None = None,
    title: str | None = None,
) -> tuple[Participant, Event]:
    """Legacy wrapper — prefer join.join_participant."""
    from app.services.join import join_participant

    result = await join_participant(db, event_code, display_name, email, company)
    return result["participant"], result["event"]


async def _selfie_urls_by_task_id(
    db: AsyncSession,
    participant_id: int,
    rows: list[tuple[ParticipantTask, Task]],
) -> dict[int, tuple[str | None, str | None]]:
    """Latest selfie image + thumbnail per task definition id."""
    from app.services.selfie_urls import resolve_selfie_urls
    from app.services.task_completion import _flow_meta

    completed_rows = [
        (pt, task)
        for pt, task in rows
        if pt.status == ParticipantTaskStatus.COMPLETED
    ]
    if not completed_rows:
        return {}

    task_ids = {task.id for _, task in completed_rows}
    flow_selfie_to_task: dict[int, int] = {}
    for pt, task in completed_rows:
        flow = _flow_meta(pt)
        selfie_id = flow.get("selfie_id")
        if isinstance(selfie_id, int):
            flow_selfie_to_task[selfie_id] = task.id

    urls: dict[int, tuple[str | None, str | None]] = {}

    if task_ids:
        result = await db.execute(
            select(Selfie)
            .where(
                Selfie.participant_id == participant_id,
                Selfie.task_id.in_(task_ids),
                Selfie.status != SelfieStatus.REJECTED,
            )
            .order_by(Selfie.uploaded_at.desc())
        )
        for selfie in result.scalars().all():
            if selfie.task_id is None or selfie.task_id in urls:
                continue
            image_url, thumbnail_url = resolve_selfie_urls(selfie)
            urls[selfie.task_id] = (image_url, thumbnail_url)

    missing_ids = [
        sid for sid, task_id in flow_selfie_to_task.items() if task_id not in urls
    ]
    if missing_ids:
        result = await db.execute(
            select(Selfie).where(
                Selfie.id.in_(missing_ids),
                Selfie.participant_id == participant_id,
                Selfie.status != SelfieStatus.REJECTED,
            )
        )
        for selfie in result.scalars().all():
            task_id = flow_selfie_to_task.get(selfie.id)
            if task_id is None or task_id in urls:
                continue
            image_url, thumbnail_url = resolve_selfie_urls(selfie)
            urls[task_id] = (image_url, thumbnail_url)

    return urls


async def get_participant_tasks(db: AsyncSession, participant: Participant) -> list[dict]:
    from app.services.event_mode import get_capabilities
    from app.services.event_settings import get_settings_for_event
    from app.services.networking_bingo_setup import ensure_participant_bingo_assignments

    event_result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = event_result.scalar_one()
    await ensure_participant_bingo_assignments(db, event, participant.id)
    settings = await get_settings_for_event(db, event.id)
    caps = get_capabilities(event, settings)

    result = await db.execute(
        select(ParticipantTask, Task)
        .join(Task, ParticipantTask.task_id == Task.id)
        .where(
            ParticipantTask.participant_id == participant.id,
            Task.is_active.is_(True),
        )
        .order_by(Task.sort_order)
    )
    rows = result.all()
    from app.services.networking_bingo_setup import event_uses_bingo_catalog

    if event_uses_bingo_catalog(event):
        rows = [
            (pt, task)
            for pt, task in rows
            if (task.slug or "").startswith("bingo-")
            or bool((task.config_json or {}).get("bingo"))
        ]

    selfie_urls = await _selfie_urls_by_task_id(db, participant.id, rows)

    return [
        {
            "id": pt.id,
            "task_id": task.id,
            "slug": task.slug,
            "bingo": bool((task.config_json or {}).get("bingo")),
            "category": (task.config_json or {}).get("category"),
            "title": task.title,
            "description": participant_task_description(task),
            "instruction": participant_task_instruction(task),
            "group_label": participant_task_group_label(task),
            "meet_group_total": meet_group_total(task),
            "meet_group_index": meet_group_index(task),
            "type": task.type.value,
            "target_count": meet_target_count(task),
            "progress_count": meet_progress_count(pt, task),
            "status": pt.status.value,
            "points": display_task_points(settings, task, show=caps.show_task_points),
            "completed_at": pt.completed_at,
            "selfie_image_url": selfie_urls.get(task.id, (None, None))[0],
            "selfie_thumbnail_url": selfie_urls.get(task.id, (None, None))[1],
        }
        for pt, task in rows
    ]


async def record_match(
    db: AsyncSession, initiator: Participant, partner_qr: str
) -> tuple[Participant, int, bool]:
    from app.services.badge import BadgeError, resolve_participant_from_badge

    try:
        partner = await resolve_participant_from_badge(
            db, partner_qr, scanner_event_id=initiator.event_id
        )
    except BadgeError as e:
        raise ValueError(e.message) from e
    if partner.id == initiator.id:
        raise ValueError("Cannot match with yourself")

    settings_result = await db.execute(
        select(EventSettings).where(EventSettings.event_id == initiator.event_id)
    )
    settings = settings_result.scalar_one_or_none()
    if settings and not settings.allow_self_scan and partner.id == initiator.id:
        raise ValueError("Cannot match with yourself")

    existing = await db.execute(
        select(Match).where(
            Match.event_id == initiator.event_id,
            Match.initiator_id == initiator.id,
            Match.partner_id == partner.id,
        )
    )
    if existing.scalar_one_or_none():
        return partner, 0, True

    event_result = await db.execute(select(Event).where(Event.id == initiator.event_id))
    event = event_result.scalar_one()
    points = 0 if event.mode == EventMode.NETWORKING else (settings.scan_match_points if settings else 10)
    db.add(
        Match(
            event_id=initiator.event_id,
            initiator_id=initiator.id,
            partner_id=partner.id,
            match_type=MatchType.QR_SCAN,
            points_awarded=points,
        )
    )
    initiator.matches_count += 1
    initiator.last_active_at = datetime.now(timezone.utc)
    await db.flush()

    if event.mode == EventMode.COMPETITION and points > 0:
        await add_score(db, initiator.event_id, initiator.id, points)

    await refresh_participant_progress(db, initiator)
    return partner, points, False


# Backward-compatible alias
record_scan = record_match
