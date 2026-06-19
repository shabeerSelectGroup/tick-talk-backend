from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EventMode, EventStatus
from app.models.event import Event
from app.models.event_settings import EventSettings


async def get_settings_for_event(db: AsyncSession, event_id: int) -> EventSettings | None:
    result = await db.execute(select(EventSettings).where(EventSettings.event_id == event_id))
    return result.scalar_one_or_none()


def is_leaderboard_visible(
    settings: EventSettings | None,
    event: Event,
    *,
    finisher_count: int = 0,
) -> bool:
    """
    When to expose rankings on wall / participant apps.
    - Live: show_live_ranking during the event
    - End-only: show_ranking_only_at_end when event ended
    - Default: show once someone has finished all tasks (finisher_count > 0)
    """
    if event.mode != EventMode.COMPETITION:
        return False
    if not settings or not settings.leaderboard_enabled:
        return False
    if event.status == EventStatus.ENDED:
        return True
    if settings.show_ranking_only_at_end:
        return False
    if settings.show_live_ranking:
        return True
    return finisher_count > 0


def is_public_wall_enabled(settings: EventSettings | None) -> bool:
    return settings is None or settings.enable_public_wall
