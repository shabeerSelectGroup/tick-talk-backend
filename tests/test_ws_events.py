from app.ws.events import WsEventType, build_envelope, channels_for_event, event_channel


def test_event_channel_format():
    assert event_channel(42, "feed") == "event:42:feed"


def test_channels_for_participant_joined():
    ch = channels_for_event(1, WsEventType.PARTICIPANT_JOINED)
    assert "event:1:wall" in ch
    assert "event:1:feed" in ch


def test_build_envelope_shape():
    env = build_envelope(WsEventType.TASK_COMPLETED, 5, {"task_id": 9})
    assert env["type"] == "task_completed"
    assert env["event_id"] == 5
    assert env["payload"]["task_id"] == 9
    assert "id" in env
    assert "timestamp" in env
