"""Backward-compatible WebSocket helpers — prefer app.services.ws_events."""

from app.services.ws_events import publish_event
from app.ws.events import WsEventType, build_envelope
from app.ws.manager import ws_manager
from app.ws.redis_bridge import redis_bridge


async def connect(ws, channel: str, connection_id: str | None = None) -> str:
    import uuid

    cid = connection_id or uuid.uuid4().hex
    await ws_manager.register(ws, channel, cid)
    return cid


def disconnect(connection_id: str) -> None:
    ws_manager.disconnect(connection_id)


async def broadcast_channel(channel: str, message: dict) -> None:
    """Publish to Redis; local delivery via pub/sub listener (scalable)."""
    await redis_bridge.publish(channel, message)


async def broadcast_event(event_id: int, message: dict) -> None:
    """Legacy activity envelope — maps to feed/wall channels."""
    from app.ws.events import event_channel

    channels = [
        event_channel(event_id, "feed"),
        event_channel(event_id, "wall"),
        event_channel(event_id, "leaderboard"),
    ]
    for ch in channels:
        await broadcast_channel(ch, message)


async def start_websocket_stack() -> None:
    await ws_manager.start()
    await redis_bridge.start()


async def stop_websocket_stack() -> None:
    await redis_bridge.stop()
    await ws_manager.stop()
