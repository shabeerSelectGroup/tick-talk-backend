"""Serialize events with mode capabilities for API responses."""

from app.core.config import get_settings
from app.models.event import Event
from app.models.event_settings import EventSettings
from app.schemas.event import EventPublicOut
from app.schemas.event_mode import EventCapabilitiesOut
from app.services.event_mode import get_capabilities, public_wall_url


def build_capabilities_out(event: Event, settings: EventSettings | None) -> EventCapabilitiesOut:
    caps = get_capabilities(event, settings)
    wall_url = public_wall_url(event) if caps.public_wall_enabled else None
    return EventCapabilitiesOut(
        mode=caps.mode,
        scores_enabled=caps.scores_enabled,
        rankings_enabled=caps.rankings_enabled,
        leaderboard_enabled=caps.leaderboard_enabled,
        shared_tasks_enabled=caps.shared_tasks_enabled,
        selfie_verification_enabled=caps.selfie_verification_enabled,
        public_wall_enabled=caps.public_wall_enabled,
        analytics_enabled=caps.analytics_enabled,
        show_task_points=caps.show_task_points,
        show_match_points=caps.show_match_points,
        public_wall_url=wall_url,
    )


def event_public_dict(event: Event, settings: EventSettings | None = None) -> dict:
    caps_out = build_capabilities_out(event, settings)
    data = EventPublicOut.model_validate(event).model_dump()
    data["capabilities"] = caps_out.model_dump()
    data["public_wall_url"] = caps_out.public_wall_url
    return data
