from app.schemas.participant import JoinRequest
from app.services.badge import build_badge_payload
from app.services.qr import generate_qr_data_url


def test_join_request_normalizes_code():
    req = JoinRequest(event_code="  demo2026  ", display_name="Alex Kim")
    assert req.event_code == "DEMO2026"


def test_badge_payload_includes_ids_and_signature():
    payload = build_badge_payload(12, 34, "abc123token")
    assert "ticktalk://badge/v1/12/34/abc123token/" in payload
    assert len(payload.rsplit("/", 1)[-1]) == 16


def test_qr_data_url_is_png():
    url = generate_qr_data_url("ticktalk://badge/test")
    assert url.startswith("data:image/png;base64,")
