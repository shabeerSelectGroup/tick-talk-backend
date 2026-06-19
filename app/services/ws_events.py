"""Emit typed WebSocket events to Redis + local subscribers."""

from __future__ import annotations

from typing import Any

from app.ws.events import WsEventType, build_envelope, channels_for_event
from app.ws.manager import ws_manager
from app.ws.redis_bridge import redis_bridge


async def publish_event(
    event_id: int,
    event_type: WsEventType,
    payload: dict[str, Any],
) -> None:
    """Publish to all relevant channels via Redis (other instances) and local sockets."""
    envelope = build_envelope(event_type, event_id, payload)
    for channel in channels_for_event(event_id, event_type):
        await redis_bridge.publish(channel, envelope)


async def emit_participant_joined(
    event_id: int,
    *,
    participant_id: int,
    display_name: str,
    company: str | None = None,
) -> None:
    await publish_event(
        event_id,
        WsEventType.PARTICIPANT_JOINED,
        {
            "participant_id": participant_id,
            "display_name": display_name,
            "company": company,
        },
    )


async def emit_task_completed(
    event_id: int,
    *,
    participant_id: int,
    task_id: int,
    task_title: str,
    points: int = 0,
    partner_name: str | None = None,
) -> None:
    await publish_event(
        event_id,
        WsEventType.TASK_COMPLETED,
        {
            "participant_id": participant_id,
            "task_id": task_id,
            "task_title": task_title,
            "points": points,
            "partner_name": partner_name,
        },
    )


async def emit_selfie_uploaded(
    event_id: int,
    *,
    participant_id: int,
    selfie_id: int,
    task_id: int | None = None,
    match_id: int | None = None,
    image_url: str | None = None,
    thumbnail_url: str | None = None,
    display_name: str | None = None,
    task_title: str | None = None,
) -> None:
    await publish_event(
        event_id,
        WsEventType.SELFIE_UPLOADED,
        {
            "participant_id": participant_id,
            "selfie_id": selfie_id,
            "task_id": task_id,
            "match_id": match_id,
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "display_name": display_name,
            "task_title": task_title,
        },
    )


async def emit_leaderboard_updated(
    event_id: int,
    *,
    top: list[dict] | None = None,
    trigger_participant_id: int | None = None,
) -> None:
    await publish_event(
        event_id,
        WsEventType.LEADERBOARD_UPDATED,
        {
            "top": top or [],
            "trigger_participant_id": trigger_participant_id,
        },
    )


async def emit_event_started(event_id: int, *, event_name: str, mode: str) -> None:
    await publish_event(
        event_id,
        WsEventType.EVENT_STARTED,
        {"event_name": event_name, "mode": mode},
    )


async def emit_event_paused(event_id: int, *, event_name: str, reason: str | None = None) -> None:
    await publish_event(
        event_id,
        WsEventType.EVENT_PAUSED,
        {"event_name": event_name, "reason": reason},
    )


async def emit_event_ended(
    event_id: int,
    *,
    event_name: str,
    winner: dict | None = None,
    podium: list[dict] | None = None,
    awards: list[dict] | None = None,
) -> None:
    await publish_event(
        event_id,
        WsEventType.EVENT_ENDED,
        {
            "event_name": event_name,
            "winner": winner,
            "podium": podium or [],
            "awards": awards or [],
        },
    )
