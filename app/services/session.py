import logging
import secrets

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.redis import get_redis

SESSION_PREFIX = "session:"
logger = logging.getLogger(__name__)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def _skip_redis_in_dev(exc: Exception) -> bool:
    return get_settings().app_env == "development"


async def store_session(session_token: str, participant_id: int) -> None:
    """Cache session in Redis; DB session_token remains the source of truth if Redis is down."""
    try:
        settings = get_settings()
        redis = await get_redis()
        ttl = settings.session_expire_hours * 3600
        await redis.setex(f"{SESSION_PREFIX}{session_token}", ttl, str(participant_id))
    except (RedisError, OSError, ConnectionError, TimeoutError) as exc:
        if _skip_redis_in_dev(exc):
            logger.warning("Redis unavailable, session not cached: %s", exc)
            return
        raise


async def invalidate_session(session_token: str) -> None:
    try:
        redis = await get_redis()
        await redis.delete(f"{SESSION_PREFIX}{session_token}")
    except (RedisError, OSError, ConnectionError, TimeoutError) as exc:
        if _skip_redis_in_dev(exc):
            return
        raise


async def session_is_active(session_token: str | None) -> bool:
    """True if this token currently has an active device session in Redis."""
    if not session_token:
        return False
    active = await sessions_are_active([session_token])
    return active.get(session_token, False)


async def sessions_are_active(session_tokens: list[str]) -> dict[str, bool]:
    """Batch check which session tokens are active in Redis."""
    unique = [t for t in dict.fromkeys(session_tokens) if t]
    if not unique:
        return {}
    try:
        redis = await get_redis()
        keys = [f"{SESSION_PREFIX}{t}" for t in unique]
        flags = await redis.mget(keys)
        return {token: bool(flag) for token, flag in zip(unique, flags, strict=True)}
    except (RedisError, OSError, ConnectionError, TimeoutError) as exc:
        if _skip_redis_in_dev(exc):
            # Cannot verify — treat as claimed so a second person is not logged in as someone else.
            return dict.fromkeys(unique, True)
        return dict.fromkeys(unique, False)
