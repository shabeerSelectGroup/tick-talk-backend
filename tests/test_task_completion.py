from app.models.enums import EventStatus, ParticipantTaskStatus
from app.services.task_completion import TaskCompletionError, assert_task_not_completed


def test_assert_task_not_completed_raises():
    class FakePT:
        status = ParticipantTaskStatus.COMPLETED

    try:
        assert_task_not_completed(FakePT())
        assert False, "expected error"
    except TaskCompletionError as e:
        assert e.code == "TASK_ALREADY_COMPLETED"


def test_event_live_required_constant():
    assert EventStatus.LIVE.value == "live"
