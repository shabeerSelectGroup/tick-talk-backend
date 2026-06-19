from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ParticipantTaskStatus
from app.models.participant import Participant, ParticipantTask
from app.models.task import Task


async def refresh_participant_progress(db: AsyncSession, participant: Participant) -> None:
    """Recompute tasks_completed_count, matches_count, and progress_percent."""
    total_tasks = await db.scalar(
        select(func.count(Task.id)).where(
            Task.event_id == participant.event_id, Task.is_active.is_(True)
        )
    )
    completed = await db.scalar(
        select(func.count(ParticipantTask.id)).where(
            ParticipantTask.participant_id == participant.id,
            ParticipantTask.status == ParticipantTaskStatus.COMPLETED,
        )
    )
    participant.tasks_completed_count = completed or 0
    if total_tasks and total_tasks > 0:
        participant.progress_percent = Decimal(
            str(round(100.0 * participant.tasks_completed_count / total_tasks, 2))
        )
    else:
        participant.progress_percent = Decimal("0.00")
    await db.flush()

    from app.models.enums import EventMode
    from app.models.event import Event
    from app.services.event_settings import get_settings_for_event
    from app.services.leaderboard import check_and_mark_finished, sync_leaderboard_stats

    event_result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = event_result.scalar_one_or_none()
    if event and event.mode == EventMode.COMPETITION:
        await sync_leaderboard_stats(db, participant)
        settings = await get_settings_for_event(db, participant.event_id)
        await check_and_mark_finished(db, participant, settings)
