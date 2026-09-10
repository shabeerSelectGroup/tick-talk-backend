from pydantic import ValidationError

from app.schemas.event import EventClearDataRequest


def test_clear_data_request_defaults_confirm_false():
    req = EventClearDataRequest()
    assert req.confirm is False


def test_clear_data_request_accepts_confirm_true():
    req = EventClearDataRequest(confirm=True)
    assert req.confirm is True
