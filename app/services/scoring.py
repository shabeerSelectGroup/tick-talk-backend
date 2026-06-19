"""Competition scoring: task completion base points + optional speed bonus."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.enums import TaskType
from app.models.event import Event
from app.models.event_settings import EventSettings
from app.models.participant import ParticipantTask
from app.models.task import Task

SCORABLE_TASK_TYPES = frozenset({TaskType.SCAN, TaskType.SELFIE})
DEFAULT_TASK_COMPLETION_POINTS = 100


def get_task_base_points(settings: EventSettings | None, task: Task) -> int:
    """Base points for completing a task (100 for scan/selfie in competition)."""
    if task.type in SCORABLE_TASK_TYPES:
        if settings:
            return max(0, settings.task_completion_points)
        return DEFAULT_TASK_COMPLETION_POINTS
    return max(0, task.points or 0)


def display_task_points(settings: EventSettings | None, task: Task, *, show: bool) -> int:
    if not show:
        return 0
    return get_task_base_points(settings, task)


def _parse_started_at(flow: dict[str, Any]) -> datetime | None:
    raw = flow.get("scanned_at") or flow.get("started_at")
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def compute_speed_bonus(
    settings: EventSettings | None,
    *,
    started_at: datetime | None,
    completed_at: datetime,
) -> int:
    """
    Linear speed bonus: full max at instant completion, zero at window end.
    """
    if not settings or not settings.speed_bonus_enabled:
        return 0
    if started_at is None:
        return 0

    window = max(1, settings.speed_bonus_window_seconds)
    max_pts = max(0, settings.speed_bonus_max_points)
    if max_pts == 0:
        return 0

    elapsed = (completed_at - started_at).total_seconds()
    if elapsed < 0:
        elapsed = 0
    if elapsed >= window:
        return 0

    ratio = 1.0 - (elapsed / window)
    return max(0, int(max_pts * ratio))


def calculate_task_completion_score(
    settings: EventSettings | None,
    task: Task,
    participant_task: ParticipantTask,
    *,
    completed_at: datetime | None = None,
) -> dict[str, int]:
    """
    Return base_points, speed_bonus, and points_awarded.
    task_completion_points is the maximum mark per task (default 100).
    Speed bonus only adjusts within that cap (fast ≈ 100, slow ≈ floor).
    """
    completed = completed_at or participant_task.completed_at or datetime.now(timezone.utc)
    max_total = get_task_base_points(settings, task)
    flow = (participant_task.metadata_json or {}).get("flow") or {}
    started = _parse_started_at(flow)

    if not settings or not settings.speed_bonus_enabled or not started:
        return {
            "base_points": max_total,
            "speed_bonus": 0,
            "points_awarded": max_total,
        }

    max_speed = min(max(0, settings.speed_bonus_max_points), max(0, max_total - 1))
    floor = max_total - max_speed
    bonus = min(
        compute_speed_bonus(settings, started_at=started, completed_at=completed),
        max_speed,
    )
    points = min(max_total, floor + bonus)
    return {
        "base_points": floor,
        "speed_bonus": bonus,
        "points_awarded": points,
    }
