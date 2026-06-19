"""In-process WebSocket connection manager with heartbeats."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.ws.events import WsEventType, build_envelope

logger = logging.getLogger(__name__)


@dataclass
class WsConnection:
    websocket: WebSocket
    connection_id: str
    channels: set[str] = field(default_factory=set)
    last_pong_at: float = field(default_factory=time.monotonic)
    subscribed_at: float = field(default_factory=time.monotonic)


class WebSocketManager:
    """
    Tracks local WebSocket connections per channel.
    Cross-instance delivery uses Redis pub/sub (see redis_bridge).
    """

    def __init__(
        self,
        *,
        heartbeat_interval_sec: float = 30.0,
        heartbeat_timeout_sec: float = 90.0,
    ) -> None:
        self._connections: dict[str, set[str]] = {}
        self._by_id: dict[str, WsConnection] = {}
        self._heartbeat_interval = heartbeat_interval_sec
        self._heartbeat_timeout = heartbeat_timeout_sec
        self._heartbeat_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        self._heartbeat_task = None

    async def register(
        self, websocket: WebSocket, channel: str, connection_id: str
    ) -> WsConnection:
        await websocket.accept()
        conn = WsConnection(
            websocket=websocket,
            connection_id=connection_id,
            channels={channel},
        )
        async with self._lock:
            self._by_id[connection_id] = conn
            self._connections.setdefault(channel, set()).add(connection_id)
        await self._send_json(
            conn,
            build_envelope(
                WsEventType.SUBSCRIBED,
                _event_id_from_channel(channel) or 0,
                {"channels": list(conn.channels), "connection_id": connection_id},
            ),
        )
        return conn

    async def subscribe(self, connection_id: str, channels: list[str]) -> None:
        conn = self._by_id.get(connection_id)
        if not conn:
            return
        async with self._lock:
            for ch in channels:
                conn.channels.add(ch)
                self._connections.setdefault(ch, set()).add(connection_id)

    async def unsubscribe(self, connection_id: str, channels: list[str]) -> None:
        conn = self._by_id.get(connection_id)
        if not conn:
            return
        async with self._lock:
            for ch in channels:
                conn.channels.discard(ch)
                if ch in self._connections:
                    self._connections[ch].discard(connection_id)

    def disconnect(self, connection_id: str) -> None:
        conn = self._by_id.pop(connection_id, None)
        if not conn:
            return
        for ch in list(conn.channels):
            if ch in self._connections:
                self._connections[ch].discard(connection_id)
                if not self._connections[ch]:
                    del self._connections[ch]

    async def handle_client_message(self, connection_id: str, raw: str) -> None:
        conn = self._by_id.get(connection_id)
        if not conn:
            return
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        msg_type = msg.get("type")
        if msg_type == "ping":
            conn.last_pong_at = time.monotonic()
            await self._send_json(
                conn,
                {"type": WsEventType.PONG.value, "timestamp": msg.get("timestamp")},
            )
        elif msg_type == "pong":
            conn.last_pong_at = time.monotonic()
        elif msg_type == "subscribe":
            channels = msg.get("channels") or []
            if isinstance(channels, list):
                await self.subscribe(connection_id, [str(c) for c in channels])
        elif msg_type == "unsubscribe":
            channels = msg.get("channels") or []
            if isinstance(channels, list):
                await self.unsubscribe(connection_id, [str(c) for c in channels])

    async def broadcast_local(self, channel: str, message: dict) -> int:
        """Send to all local connections on channel. Returns delivery count."""
        payload = json.dumps(message)
        dead: list[str] = []
        sent = 0
        async with self._lock:
            target_ids = list(self._connections.get(channel, set()))

        for cid in target_ids:
            conn = self._by_id.get(cid)
            if not conn or conn.websocket.client_state != WebSocketState.CONNECTED:
                dead.append(cid)
                continue
            try:
                await conn.websocket.send_text(payload)
                sent += 1
            except Exception:
                dead.append(cid)

        for cid in dead:
            self.disconnect(cid)
        return sent

    async def _send_json(self, conn: WsConnection, message: dict) -> None:
        await conn.websocket.send_text(json.dumps(message))

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            now = time.monotonic()
            stale: list[str] = []
            async with self._lock:
                conns = list(self._by_id.values())

            for conn in conns:
                if now - conn.last_pong_at > self._heartbeat_timeout:
                    stale.append(conn.connection_id)
                    try:
                        await conn.websocket.close(code=1001, reason="heartbeat timeout")
                    except Exception:
                        pass
                    continue
                try:
                    await self._send_json(
                        conn,
                        {"type": WsEventType.PING.value, "timestamp": now},
                    )
                except Exception:
                    stale.append(conn.connection_id)

            for cid in stale:
                self.disconnect(cid)


def _event_id_from_channel(channel: str) -> int | None:
    # event:12:feed
    parts = channel.split(":")
    if len(parts) >= 2 and parts[0] == "event":
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


# Singleton for app lifespan
ws_manager = WebSocketManager()
