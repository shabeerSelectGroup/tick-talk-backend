"""Manual / human-bingo task toggle completion."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.activity_log import ActivityLog
from app.models.enums import ActivityType, EventStatus, ParticipantTaskStatus, TaskType
from app.models.event import Event
from app.models.participant import Participant
from app.services.progress import refresh_participant_progress
from app.services.task_completion import get_participant_task


class ManualTaskError(AppError):
    pass


async def assert_event_allows_bingo_toggle(db: AsyncSession, event_id: int) -> Event:
    from sqlalchemy import select

    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise ManualTaskError("EVENT_NOT_FOUND", "Event not found.", 404)
    if event.status == EventStatus.DRAFT:
        raise ManualTaskError(
            "EVENT_NOT_OPEN",
            "This event is not open yet. Wait for the host to go live.",
            403,
        )
    if event.status == EventStatus.ENDED:
        raise ManualTaskError("EVENT_ENDED", "This event has ended.", 403)
    return event


async def toggle_manual_participant_task(
    db: AsyncSession,
    participant: Participant,
    participant_task_id: int,
) -> dict:
    await assert_event_allows_bingo_toggle(db, participant.event_id)
    participant_task, task = await get_participant_task(db, participant, participant_task_id)

    if task.type != TaskType.MANUAL:
        raise ManualTaskError(
            "TASK_NOT_MANUAL",
            "This task cannot be checked off from the bingo list.",
            400,
        )

    if (task.config_json or {}).get("bingo"):
        raise ManualTaskError(
            "BINGO_REQUIRES_SELFIE",
            "Upload a selfie with someone who matches this prompt to complete the challenge.",
            400,
        )

    now = datetime.now(timezone.utc)
    if participant_task.status == ParticipantTaskStatus.COMPLETED:
        participant_task.status = ParticipantTaskStatus.PENDING
        participant_task.completed_at = None
        completed = False
    else:
        participant_task.status = ParticipantTaskStatus.COMPLETED
        participant_task.completed_at = now
        completed = True
        db.add(
            ActivityLog(
                event_id=participant.event_id,
                participant_id=participant.id,
                activity_type=ActivityType.TASK_COMPLETED,
                summary=f"Completed: {task.title}",
                payload_json={
                    "task_id": task.id,
                    "participant_task_id": participant_task.id,
                    "bingo": bool((task.config_json or {}).get("bingo")),
                },
            )
        )

    await refresh_participant_progress(db, participant)
    await db.flush()

    return {
        "participant_task_id": participant_task.id,
        "task_id": task.id,
        "status": participant_task.status.value,
        "completed": completed,
        "title": task.title,
    }
