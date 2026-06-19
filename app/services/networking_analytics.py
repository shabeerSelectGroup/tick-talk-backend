"""Analytics for networking-mode events (connections-focused, no scores)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.enums import ActivityType, EventMode, ParticipantTaskStatus, SelfieStatus
from app.models.event import Event
from app.models.match import Match
from app.models.participant import Participant, ParticipantTask
from app.models.selfie import Selfie
from app.models.task import Task
from app.services.event_mode import get_capabilities
from app.services.event_settings import get_settings_for_event


async def get_networking_analytics(db: AsyncSession, event: Event) -> dict:
    from app.services.event_mode import EventMode as EM

    if event.mode != EM.NETWORKING:
        return {"error": "Analytics endpoint is for networking mode only"}

    settings = await get_settings_for_event(db, event.id)
    caps = get_capabilities(event, settings)

    participants = await db.scalar(
        select(func.count(Participant.id)).where(
            Participant.event_id == event.id, Participant.is_active.is_(True)
        )
    ) or 0

    matches = await db.scalar(
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

    selfies_total = await db.scalar(
        select(func.count(Selfie.id)).where(Selfie.event_id == event.id)
    ) or 0

    selfies_pending = await db.scalar(
        select(func.count(Selfie.id)).where(
            Selfie.event_id == event.id,
            Selfie.status == SelfieStatus.PENDING,
        )
    ) or 0

    avg_matches = await db.scalar(
        select(func.avg(Participant.matches_count)).where(
            Participant.event_id == event.id, Participant.is_active.is_(True)
        )
    )

    task_rows = await db.execute(
        select(Task.title, func.count(ParticipantTask.id))
        .join(ParticipantTask, ParticipantTask.task_id == Task.id)
        .join(Participant, ParticipantTask.participant_id == Participant.id)
        .where(
            Participant.event_id == event.id,
            ParticipantTask.status == ParticipantTaskStatus.COMPLETED,
        )
        .group_by(Task.id, Task.title)
        .order_by(func.count(ParticipantTask.id).desc())
        .limit(10)
    )
    top_tasks = [{"title": t, "completions": c} for t, c in task_rows.all()]

    recent = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.event_id == event.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(15)
    )
    activity_feed = [
        {
            "type": a.activity_type.value,
            "summary": a.summary,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in recent.scalars().all()
    ]

    return {
        "mode": "networking",
        "capabilities": caps.to_dict(),
        "participants_active": participants,
        "total_connections": matches,
        "tasks_completed": tasks_completed,
        "selfies_uploaded": selfies_total,
        "selfies_pending_review": selfies_pending,
        "avg_connections_per_participant": round(float(avg_matches or 0), 2),
        "connection_rate": round(matches / participants, 2) if participants else 0,
        "top_tasks": top_tasks,
        "recent_activity": activity_feed,
        "features": {
            "shared_tasks": True,
            "selfie_verification": caps.selfie_verification_enabled,
            "public_wall": caps.public_wall_enabled,
            "scores_disabled": True,
            "leaderboard_disabled": True,
        },
    }
