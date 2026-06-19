"""Assign shared event tasks to participants."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ParticipantTaskStatus
from app.models.participant import Participant, ParticipantTask
from app.models.task import Task
from app.services.progress import refresh_participant_progress


async def assign_task_to_all_participants(
    db: AsyncSession, event_id: int, task_id: int
) -> int:
    """Create participant_tasks for every active participant. Returns count assigned."""
    participants = await db.execute(
        select(Participant.id).where(
            Participant.event_id == event_id, Participant.is_active.is_(True)
        )
    )
    assigned = 0
    for (participant_id,) in participants.all():
        existing = await db.execute(
            select(ParticipantTask.id).where(
                ParticipantTask.participant_id == participant_id,
                ParticipantTask.task_id == task_id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(
            ParticipantTask(
                participant_id=participant_id,
                task_id=task_id,
                status=ParticipantTaskStatus.PENDING,
            )
        )
        assigned += 1
    await db.flush()
    return assigned


async def assign_all_tasks_to_participant(
    db: AsyncSession, event_id: int, participant_id: int
) -> int:
    """Assign all active event tasks to one participant (on join)."""
    tasks = await db.execute(
        select(Task.id).where(Task.event_id == event_id, Task.is_active.is_(True))
    )
    count = 0
    for (task_id,) in tasks.all():
        existing = await db.execute(
            select(ParticipantTask.id).where(
                ParticipantTask.participant_id == participant_id,
                ParticipantTask.task_id == task_id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(
            ParticipantTask(
                participant_id=participant_id,
                task_id=task_id,
                status=ParticipantTaskStatus.PENDING,
            )
        )
        count += 1
    await db.flush()
    participant = await db.get(Participant, participant_id)
    if participant:
        await refresh_participant_progress(db, participant)
    return count
