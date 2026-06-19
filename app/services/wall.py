"""Public live wall data: stats, selfies, timer, leaderboard."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import EventMode, ParticipantTaskStatus, SelfieStatus
from app.models.event import Event
from app.models.match import Match
from app.models.participant import Participant, ParticipantTask
from app.models.selfie import Selfie
from app.models.task import Task
from app.services.event_mode import get_capabilities
from app.services.event_settings import get_settings_for_event, is_leaderboard_visible
from app.services.leaderboard import count_finishers, get_leaderboard


async def get_wall_timer(db: AsyncSession, event: Event) -> dict:
    remaining = None
    if event.ends_at:
        now = datetime.now(timezone.utc)
        end = event.ends_at if event.ends_at.tzinfo else event.ends_at.replace(tzinfo=timezone.utc)
        remaining = max(0, int((end - now).total_seconds()))
    return {
        "status": event.status.value,
        "starts_at": event.starts_at.isoformat() if event.starts_at else None,
        "ends_at": event.ends_at.isoformat() if event.ends_at else None,
        "remaining_seconds": remaining,
    }


async def get_wall_stats(db: AsyncSession, event: Event) -> dict:
    settings = await get_settings_for_event(db, event.id)
    caps = get_capabilities(event, settings)

    participants = await db.scalar(
        select(func.count(Participant.id)).where(
            Participant.event_id == event.id, Participant.is_active.is_(True)
        )
    ) or 0

    connections = await db.scalar(
        select(func.count(Match.id)).where(Match.event_id == event.id)
    ) or 0

    tasks_completed = await db.scalar(
        select(func.count(ParticipantTask.id))
        .join(Participant, ParticipantTask.participant_id == Participant.id)
        .where(
            Participant.event_id == event.id,
            ParticipantTask.status == ParticipantTaskStatus.COMPLETED,
        )
    ) or 0

    selfies = await db.scalar(
        select(func.count(Selfie.id)).where(Selfie.event_id == event.id)
    ) or 0

    task_total = await db.scalar(
        select(func.count(Task.id)).where(
            Task.event_id == event.id, Task.is_active.is_(True)
        )
    ) or 0

    finisher_count = 0
    if event.mode == EventMode.COMPETITION:
        finisher_count = await count_finishers(db, event.id)

    leaderboard_visible = (
        caps.leaderboard_enabled
        and event.mode == EventMode.COMPETITION
        and is_leaderboard_visible(settings, event, finisher_count=finisher_count)
    )

    return {
        "mode": event.mode.value,
        "status": event.status.value,
        "participants": participants,
        "connections": connections,
        "tasks_completed": tasks_completed,
        "task_total": task_total,
        "selfies": selfies,
        "leaderboard_enabled": caps.leaderboard_enabled and event.mode == EventMode.COMPETITION,
        "leaderboard_visible": leaderboard_visible,
        "finisher_count": finisher_count,
        "show_scores": bool(settings and settings.show_scores_on_wall)
        or (caps.scores_enabled and event.mode == EventMode.COMPETITION),
    }


async def get_wall_selfies(
    db: AsyncSession,
    event_id: int,
    *,
    limit: int = 24,
    task_id: int | None = None,
) -> list[dict]:
    q = (
        select(Selfie, Participant, Task)
        .join(Participant, Selfie.participant_id == Participant.id)
        .outerjoin(Task, Selfie.task_id == Task.id)
        .where(
            Selfie.event_id == event_id,
            Selfie.status != SelfieStatus.REJECTED,
        )
    )
    if task_id is not None:
        q = q.where(Selfie.task_id == task_id)
    from app.services.selfie_urls import resolve_selfie_urls

    result = await db.execute(q.order_by(Selfie.uploaded_at.desc()).limit(limit))
    items = []
    for s, p, t in result.all():
        image_url, thumbnail_url = resolve_selfie_urls(s)
        items.append(
            {
                "id": s.id,
                "participant_id": p.id,
                "display_name": p.display_name,
                "company": p.company,
                "task_id": s.task_id,
                "task_title": t.title if t else None,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "uploaded_at": s.uploaded_at.isoformat() if s.uploaded_at else None,
                "status": s.status.value,
            }
        )
    return items


async def get_wall_leaderboard(db: AsyncSession, event: Event) -> list[dict]:
    if event.mode != EventMode.COMPETITION:
        return []
    settings = await get_settings_for_event(db, event.id)
    if not settings or not settings.leaderboard_enabled:
        return []
    finisher_count = await count_finishers(db, event.id)
    if not is_leaderboard_visible(settings, event, finisher_count=finisher_count):
        return []
    return await get_leaderboard(db, event.id, limit=settings.leaderboard_size)
