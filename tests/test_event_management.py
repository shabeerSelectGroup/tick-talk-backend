import pytest
from pydantic import ValidationError

from app.models.enums import EventMode
from app.schemas.event import EventCreateRequest, EventSettingsInput
from app.services.event_management import _build_task_templates, build_join_url


def test_build_join_url():
    url = build_join_url("DEMO2026")
    assert "/join/DEMO2026" in url


def test_task_templates_scaling():
    templates = _build_task_templates(12)
    assert len(templates) == 12
    assert templates[0]["slug"] == "intro"


def test_networking_mode_disables_leaderboard():
    req = EventCreateRequest(
        name="Test Event",
        duration_minutes=60,
        task_count=3,
        mode=EventMode.NETWORKING,
        settings=EventSettingsInput(
            leaderboard_enabled=True,
            enable_awards=True,
            show_live_ranking=True,
        ),
    )
    assert req.settings.leaderboard_enabled is False
    assert req.settings.enable_awards is False


def test_competition_ranking_requires_leaderboard():
    with pytest.raises(ValidationError):
        EventCreateRequest(
            name="Comp",
            duration_minutes=60,
            task_count=3,
            mode=EventMode.COMPETITION,
            settings=EventSettingsInput(
                leaderboard_enabled=False,
                show_live_ranking=True,
            ),
        )


def test_conflicting_ranking_flags():
    with pytest.raises(ValidationError):
        EventSettingsInput(
            show_live_ranking=True,
            show_ranking_only_at_end=True,
        )
