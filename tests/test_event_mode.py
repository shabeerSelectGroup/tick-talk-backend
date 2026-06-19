from app.models.enums import EventMode
from app.services.event_mode import EventCapabilities, get_capabilities


class FakeEvent:
    def __init__(self, mode: EventMode):
        self.mode = mode


class FakeSettings:
    leaderboard_enabled = True
    enable_selfie_verification = True
    enable_public_wall = True


def test_networking_disables_scores_and_leaderboard():
    caps = get_capabilities(FakeEvent(EventMode.NETWORKING), FakeSettings())
    assert caps.scores_enabled is False
    assert caps.leaderboard_enabled is False
    assert caps.rankings_enabled is False
    assert caps.selfie_verification_enabled is True
    assert caps.public_wall_enabled is True
    assert caps.show_task_points is False


def test_competition_enables_scores():
    caps = get_capabilities(FakeEvent(EventMode.COMPETITION), FakeSettings())
    assert caps.scores_enabled is True
    assert caps.leaderboard_enabled is True
    assert caps.show_match_points is True
