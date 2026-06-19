"""Event mode capabilities: networking vs competition."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.models.enums import EventMode
from app.models.event import Event
from app.models.event_settings import EventSettings


@dataclass(frozen=True)
class EventCapabilities:
    mode: EventMode
    scores_enabled: bool
    rankings_enabled: bool
    leaderboard_enabled: bool
    shared_tasks_enabled: bool = True
    selfie_verification_enabled: bool = True
    public_wall_enabled: bool = True
    analytics_enabled: bool = True
    show_task_points: bool = False
    show_match_points: bool = False

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "scores_enabled": self.scores_enabled,
            "rankings_enabled": self.rankings_enabled,
            "leaderboard_enabled": self.leaderboard_enabled,
            "shared_tasks_enabled": self.shared_tasks_enabled,
            "selfie_verification_enabled": self.selfie_verification_enabled,
            "public_wall_enabled": self.public_wall_enabled,
            "analytics_enabled": self.analytics_enabled,
            "show_task_points": self.show_task_points,
            "show_match_points": self.show_match_points,
        }


def get_capabilities(event: Event, settings: EventSettings | None = None) -> EventCapabilities:
    """Resolve feature flags from event mode + per-event settings."""
    if event.mode == EventMode.NETWORKING:
        selfie_on = settings.enable_selfie_verification if settings else True
        wall_on = settings.enable_public_wall if settings else True
        return EventCapabilities(
            mode=EventMode.NETWORKING,
            scores_enabled=False,
            rankings_enabled=False,
            leaderboard_enabled=False,
            shared_tasks_enabled=True,
            selfie_verification_enabled=selfie_on,
            public_wall_enabled=wall_on,
            analytics_enabled=True,
            show_task_points=False,
            show_match_points=False,
        )

    lb = bool(settings.leaderboard_enabled) if settings else True
    return EventCapabilities(
        mode=EventMode.COMPETITION,
        scores_enabled=True,
        rankings_enabled=lb,
        leaderboard_enabled=lb,
        shared_tasks_enabled=True,
        selfie_verification_enabled=settings.enable_selfie_verification if settings else True,
        public_wall_enabled=settings.enable_public_wall if settings else True,
        analytics_enabled=True,
        show_task_points=True,
        show_match_points=True,
    )


def public_wall_url(event: Event) -> str | None:
    settings = get_settings()
    return f"{settings.app_public_url.rstrip('/')}/wall/{event.code}"


def apply_competition_settings_defaults(settings: EventSettings) -> None:
    """Sensible defaults when creating/updating competition events."""
    if settings.task_completion_points < 1:
        settings.task_completion_points = 100
    settings.leaderboard_enabled = True
    settings.speed_bonus_enabled = True
    if settings.task_completion_points < 1:
        settings.task_completion_points = 100
    if settings.speed_bonus_max_points < 1:
        settings.speed_bonus_max_points = 25
    if settings.speed_bonus_window_seconds < 30:
        settings.speed_bonus_window_seconds = 300
    # Live rankings during the event; wall can still use finisher/end rules via is_leaderboard_visible.
    if not settings.show_ranking_only_at_end and not settings.show_live_ranking:
        settings.show_live_ranking = True


def apply_networking_settings_defaults(settings: EventSettings) -> None:
    """Enforce networking-mode configuration on stored settings."""
    settings.leaderboard_enabled = False
    settings.enable_awards = False
    settings.show_live_ranking = False
    settings.show_ranking_only_at_end = False
    settings.show_scores_on_wall = False
    settings.scan_match_points = 0


def sanitize_participant_stats(data: dict, caps: EventCapabilities) -> dict:
    if not caps.scores_enabled:
        data["score"] = 0
        data["rank"] = None
    return data
