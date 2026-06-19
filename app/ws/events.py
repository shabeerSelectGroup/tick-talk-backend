"""WebSocket event types and message envelopes."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any


class WsEventType(str, enum.Enum):
    PARTICIPANT_JOINED = "participant_joined"
    TASK_COMPLETED = "task_completed"
    SELFIE_UPLOADED = "selfie_uploaded"
    LEADERBOARD_UPDATED = "leaderboard_updated"
    EVENT_STARTED = "event_started"
    EVENT_PAUSED = "event_paused"
    EVENT_ENDED = "event_ended"
    # Control plane
    PING = "ping"
    PONG = "pong"
    SUBSCRIBED = "subscribed"
    ERROR = "error"


# Channels that receive each event type (subset also get legacy `activity` on feed)
EVENT_CHANNELS = {
    WsEventType.PARTICIPANT_JOINED: ["feed", "wall", "participants"],
    WsEventType.TASK_COMPLETED: ["feed", "wall", "participants"],
    WsEventType.SELFIE_UPLOADED: ["feed", "wall"],
    WsEventType.LEADERBOARD_UPDATED: ["feed", "leaderboard", "participants"],
    WsEventType.EVENT_STARTED: ["feed", "wall", "participants", "leaderboard"],
    WsEventType.EVENT_PAUSED: ["feed", "wall", "participants"],
    WsEventType.EVENT_ENDED: ["feed", "wall", "participants", "leaderboard"],
}


def event_channel(event_id: int, suffix: str) -> str:
    return f"event:{event_id}:{suffix}"


def channels_for_event(event_id: int, event_type: WsEventType) -> list[str]:
    suffixes = EVENT_CHANNELS.get(event_type, ["feed"])
    return [event_channel(event_id, s) for s in suffixes]


def build_envelope(
    event_type: WsEventType | str,
    event_id: int,
    payload: dict[str, Any],
    *,
    message_id: str | None = None,
) -> dict[str, Any]:
    et = event_type.value if isinstance(event_type, WsEventType) else event_type
    return {
        "id": message_id or uuid.uuid4().hex,
        "type": et,
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
