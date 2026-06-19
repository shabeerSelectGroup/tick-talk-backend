"""Gather event data for reports and exports."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.enums import EventMode, ParticipantTaskStatus
from app.models.event import Event
from app.models.leaderboard import Leaderboard
from app.models.match import Match
from app.models.participant import Participant, ParticipantTask
from app.models.selfie import Selfie
from app.models.task import Task
from app.services.event_settings import get_settings_for_event
from app.services.leaderboard import get_leaderboard
from app.services.networking_analytics import get_networking_analytics


async def get_event_summary(db: AsyncSession, event: Event) -> dict:
    if event.mode == EventMode.NETWORKING:
        return await get_networking_analytics(db, event)

    from app.services.events import get_event_stats

    stats = await get_event_stats(db, event.id)
    matches = await db.scalar(select(func.count(Match.id)).where(Match.event_id == event.id)) or 0
    tasks_done = await db.scalar(
        select(func.count(ParticipantTask.id))
        .join(Participant, ParticipantTask.participant_id == Participant.id)
        .where(
            Participant.event_id == event.id,
            ParticipantTask.status == ParticipantTaskStatus.COMPLETED,
        )
    ) or 0
    selfies = await db.scalar(select(func.count(Selfie.id)).where(Selfie.event_id == event.id)) or 0
    top_board = await get_leaderboard(db, event.id, limit=10)

    return {
        "mode": "competition",
        **stats,
        "total_matches": matches,
        "total_tasks_completed": tasks_done,
        "selfies_uploaded": selfies,
        "leaderboard_top": top_board,
    }


async def fetch_participants_export(db: AsyncSession, event_id: int) -> list[dict]:
    result = await db.execute(
        select(Participant, Leaderboard)
        .outerjoin(
            Leaderboard,
            (Leaderboard.participant_id == Participant.id) & (Leaderboard.event_id == event_id),
        )
        .where(Participant.event_id == event_id, Participant.is_active.is_(True))
        .order_by(Participant.display_name)
    )
    return [
        {
            "id": p.id,
            "display_name": p.display_name,
            "email": p.email or "",
            "company": p.company or "",
            "title": p.title or "",
            "score": lb.score if lb else 0,
            "rank": lb.rank if lb else "",
            "tasks_completed": p.tasks_completed_count,
            "matches_count": p.matches_count,
            "progress_percent": float(p.progress_percent),
            "joined_at": p.joined_at.isoformat() if p.joined_at else "",
        }
        for p, lb in result.all()
    ]


async def fetch_matches_export(db: AsyncSession, event_id: int) -> list[dict]:
    initiator = aliased(Participant)
    partner = aliased(Participant)
    result = await db.execute(
        select(Match, initiator, partner, Task.title)
        .join(initiator, Match.initiator_id == initiator.id)
        .join(partner, Match.partner_id == partner.id)
        .outerjoin(Task, Match.task_id == Task.id)
        .where(Match.event_id == event_id)
        .order_by(Match.created_at.desc())
    )
    return [
        {
            "id": m.id,
            "initiator_name": ini.display_name,
            "initiator_company": ini.company or "",
            "partner_name": par.display_name,
            "partner_company": par.company or "",
            "task_title": title or "",
            "match_type": m.match_type.value,
            "points_awarded": m.points_awarded,
            "created_at": m.created_at.isoformat() if m.created_at else "",
        }
        for m, ini, par, title in result.all()
    ]


async def fetch_leaderboard_export(db: AsyncSession, event_id: int) -> list[dict]:
    board = await get_leaderboard(db, event_id, limit=500)
    return board


async def fetch_selfies_export(db: AsyncSession, event_id: int) -> list[dict]:
    result = await db.execute(
        select(Selfie, Participant)
        .join(Participant, Selfie.participant_id == Participant.id)
        .where(Selfie.event_id == event_id)
        .order_by(Selfie.uploaded_at.desc())
    )
    return [
        {
            "id": s.id,
            "participant_name": p.display_name,
            "storage_key": s.storage_key,
            "image_url": s.image_url,
            "status": s.status.value,
            "uploaded_at": s.uploaded_at.isoformat() if s.uploaded_at else "",
        }
        for s, p in result.all()
    ]


async def build_report_context(db: AsyncSession, event: Event) -> dict:
    settings = await get_settings_for_event(db, event.id)
    summary = await get_event_summary(db, event)
    return {
        "event": {
            "id": event.id,
            "code": event.code,
            "name": event.name,
            "description": event.description or "",
            "mode": event.mode.value,
            "status": event.status.value,
            "starts_at": event.starts_at.isoformat() if event.starts_at else "",
            "ends_at": event.ends_at.isoformat() if event.ends_at else "",
        },
        "settings": {
            "duration_minutes": settings.duration_minutes if settings else None,
            "leaderboard_enabled": settings.leaderboard_enabled if settings else False,
        },
        "summary": summary,
        "participants_count": summary.get("participants_active")
        or summary.get("participant_count")
        or 0,
    }
