"""Clear all participant data and submissions for an event (keeps tasks & settings)."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EventError
from app.core.redis import get_redis
from app.models.activity_log import ActivityLog
from app.models.enums import EventStatus
from app.models.event import Event
from app.models.match import Match
from app.models.participant import Participant
from app.models.selfie import Selfie
from app.services.leaderboard import LEADERBOARD_PREFIX
from app.services.selfie_storage import delete_selfie_assets
from app.services.session import invalidate_session

logger = logging.getLogger(__name__)


async def clear_event_players_and_submissions(
    db: AsyncSession,
    event: Event,
) -> dict[str, int | str]:
    """
    Remove all players, selfies, scans, scores, and activity for an event.
    Event definition, tasks, and settings are kept.
    """
    event_id = event.id

    participants_removed = (
        await db.scalar(
            select(func.count()).select_from(Participant).where(Participant.event_id == event_id)
        )
        or 0
    )
    selfies_removed = (
        await db.scalar(select(func.count()).select_from(Selfie).where(Selfie.event_id == event_id))
        or 0
    )
    matches_removed = (
        await db.scalar(select(func.count()).select_from(Match).where(Match.event_id == event_id))
        or 0
    )
    activity_logs_removed = (
        await db.scalar(
            select(func.count()).select_from(ActivityLog).where(ActivityLog.event_id == event_id)
        )
        or 0
    )

    if not any((participants_removed, selfies_removed, matches_removed, activity_logs_removed)):
        raise EventError(
            "EVENT_ALREADY_EMPTY",
            "This event has no players or submissions to clear.",
            400,
        )

    selfie_rows = (
        await db.scalars(select(Selfie).where(Selfie.event_id == event_id))
    ).all()
    for selfie in selfie_rows:
        try:
            await asyncio.to_thread(delete_selfie_assets, selfie)
        except Exception as exc:
            logger.warning("Failed to delete selfie assets for selfie %s: %s", selfie.id, exc)

    session_tokens = (
        await db.scalars(
            select(Participant.session_token).where(Participant.event_id == event_id)
        )
    ).all()
    for token in session_tokens:
        await invalidate_session(token)

    await db.execute(delete(ActivityLog).where(ActivityLog.event_id == event_id))
    await db.execute(delete(Participant).where(Participant.event_id == event_id))

    try:
        redis = await get_redis()
        await redis.delete(f"{LEADERBOARD_PREFIX}{event_id}")
    except Exception as exc:
        logger.warning("Failed to clear leaderboard cache for event %s: %s", event_id, exc)

    previous_status = event.status.value
    if event.status == EventStatus.ENDED:
        event.status = EventStatus.SCHEDULED
        event.ends_at = None
        await db.flush()

    return {
        "participants_removed": participants_removed,
        "selfies_removed": selfies_removed,
        "matches_removed": matches_removed,
        "activity_logs_removed": activity_logs_removed,
        "previous_status": previous_status,
        "event_status": event.status.value,
    }
