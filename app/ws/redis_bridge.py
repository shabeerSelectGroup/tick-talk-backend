"""Redis pub/sub bridge for horizontal WebSocket scaling."""

from __future__ import annotations

import asyncio
import json
import logging

from app.core.redis import get_redis
from app.ws.manager import ws_manager

logger = logging.getLogger(__name__)

REDIS_WS_PATTERN = "event:*"
INSTANCE_CHANNEL_PREFIX = "ws:instance:"


class RedisPubSubBridge:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._listen_loop())
        logger.info("Redis WebSocket pub/sub listener started")

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def publish(self, channel: str, message: dict) -> None:
        try:
            redis = await get_redis()
            await redis.publish(channel, json.dumps(message))
        except Exception as e:
            logger.warning("Redis publish skipped (%s): %s", channel, e)

    async def _listen_loop(self) -> None:
        while self._running:
            try:
                redis = await get_redis()
                pubsub = redis.pubsub()
                await pubsub.psubscribe(REDIS_WS_PATTERN)
                async for msg in pubsub.listen():
                    if not self._running:
                        break
                    if msg["type"] not in ("pmessage", "message"):
                        continue
                    channel = msg.get("channel") or ""
                    if isinstance(channel, bytes):
                        channel = channel.decode()
                    data = msg.get("data")
                    if isinstance(data, bytes):
                        data = data.decode()
                    try:
                        payload = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    await ws_manager.broadcast_local(channel, payload)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Redis pub/sub listener error: %s — retrying in 3s", e)
                await asyncio.sleep(3)


redis_bridge = RedisPubSubBridge()
