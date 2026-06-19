from datetime import datetime, timezone

from app.models.enums import TaskType
from app.services.scoring import (
    compute_speed_bonus,
    get_task_base_points,
    calculate_task_completion_score,
)


class FakeSettings:
    task_completion_points = 100
    speed_bonus_enabled = True
    speed_bonus_max_points = 25
    speed_bonus_window_seconds = 300


class FakeTask:
    type = TaskType.SCAN
    points = 30


class FakePT:
    completed_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    metadata_json = {
        "flow": {"started_at": "2026-01-01T12:00:00+00:00"},
    }


def test_task_base_points_scan_uses_settings():
    assert get_task_base_points(FakeSettings(), FakeTask()) == 100


def test_speed_bonus_high_when_fast():
    settings = FakeSettings()
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    completed = datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc)
    bonus = compute_speed_bonus(settings, started_at=started, completed_at=completed)
    assert bonus >= 24


def test_speed_bonus_zero_after_window():
    settings = FakeSettings()
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    completed = datetime(2026, 1, 1, 12, 10, 0, tzinfo=timezone.utc)
    assert compute_speed_bonus(settings, started_at=started, completed_at=completed) == 0


def test_calculate_task_completion_score_total():
    result = calculate_task_completion_score(FakeSettings(), FakeTask(), FakePT())
    assert result["points_awarded"] <= 100
    assert result["speed_bonus"] > 0
    assert result["points_awarded"] == result["base_points"] + result["speed_bonus"]
    assert result["points_awarded"] == 100
