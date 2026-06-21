import logging
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
    verify_password,
)
from app.models.admin import Admin
from app.models.admin_refresh_token import AdminRefreshToken
from app.models.enums import AdminRole

LOGIN_ATTEMPT_PREFIX = "admin_login_attempts:"
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900

logger = logging.getLogger(__name__)


def _skip_redis_in_dev(exc: Exception) -> bool:
    return get_settings().app_env == "development"


async def check_login_rate_limit(email: str) -> None:
    """Block only after repeated failed attempts (see record_failed_login)."""
    try:
        redis = await get_redis()
        key = f"{LOGIN_ATTEMPT_PREFIX}{email.lower()}"
        attempts_raw = await redis.get(key)
        attempts = int(attempts_raw) if attempts_raw else 0
        if attempts >= LOGIN_MAX_ATTEMPTS:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again in 15 minutes.",
            )
    except HTTPException:
        raise
    except (RedisError, OSError, ConnectionError) as exc:
        if _skip_redis_in_dev(exc):
            logger.warning("Redis unavailable, skipping login rate limit: %s", exc)
            return
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login temporarily unavailable. Start Redis (docker compose up -d).",
        ) from exc


async def record_failed_login(key: str) -> None:
    try:
        redis = await get_redis()
        rate_key = f"{LOGIN_ATTEMPT_PREFIX}{key.lower()}"
        attempts = await redis.incr(rate_key)
        if attempts == 1:
            await redis.expire(rate_key, LOGIN_LOCKOUT_SECONDS)
    except (RedisError, OSError, ConnectionError) as exc:
        if _skip_redis_in_dev(exc):
            return
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login temporarily unavailable. Start Redis (docker compose up -d).",
        ) from exc


async def clear_login_attempts(email: str) -> None:
    try:
        redis = await get_redis()
        await redis.delete(f"{LOGIN_ATTEMPT_PREFIX}{email.lower()}")
    except (RedisError, OSError, ConnectionError) as exc:
        if _skip_redis_in_dev(exc):
            return
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login temporarily unavailable. Start Redis (docker compose up -d).",
        ) from exc


async def authenticate_admin(db: AsyncSession, email: str, password: str) -> Admin:
    await check_login_rate_limit(email)
    result = await db.execute(select(Admin).where(Admin.email == email.lower()))
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(password, admin.password_hash):
        await record_failed_login(email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not admin.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    if admin.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="This account role is no longer supported.",
        )
    await clear_login_attempts(email)
    return admin


ADMIN_CODE_RATE_LIMIT_KEY = "_admin_security_code"


async def authenticate_admin_by_security_code(
    db: AsyncSession, security_code: str, *, settings: Settings | None = None
) -> Admin:
    cfg = settings or get_settings()
    expected = (cfg.admin_security_code or "").strip()
    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin security code is not configured on the server",
        )

    await check_login_rate_limit(ADMIN_CODE_RATE_LIMIT_KEY)
    provided = security_code.strip()
    if not secrets.compare_digest(provided, expected):
        await record_failed_login(ADMIN_CODE_RATE_LIMIT_KEY)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid security code")

    result = await db.execute(
        select(Admin).where(
            Admin.email == cfg.admin_login_email.lower().strip(),
            Admin.is_active.is_(True),
        )
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin account is not set up. Run database seed.",
        )
    if admin.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="This account role is no longer supported.",
        )
    await clear_login_attempts(ADMIN_CODE_RATE_LIMIT_KEY)
    return admin


async def issue_tokens(
    db: AsyncSession,
    admin: Admin,
    request: Request | None = None,
) -> dict[str, str]:
    refresh_token, jti, expires_at = create_refresh_token(str(admin.id))
    token_hash = hash_refresh_token(refresh_token)

    user_agent = request.headers.get("user-agent") if request else None
    ip_address = request.client.host if request and request.client else None

    db.add(
        AdminRefreshToken(
            admin_id=admin.id,
            jti=jti,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent[:512] if user_agent else None,
            ip_address=ip_address,
        )
    )
    admin.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    access_token = create_access_token(str(admin.id), admin.role.value, jti=jti)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
) -> dict[str, str]:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    jti = payload.get("jti")
    admin_id = int(payload["sub"])
    if not jti:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(
        select(AdminRefreshToken).where(
            AdminRefreshToken.jti == jti,
            AdminRefreshToken.admin_id == admin_id,
        )
    )
    stored = result.scalar_one_or_none()
    if not stored or stored.is_revoked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    if stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    if stored.token_hash != hash_refresh_token(refresh_token):
        # Possible token reuse attack — revoke all tokens for this admin
        await revoke_all_refresh_tokens(db, admin_id)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    admin_result = await db.execute(
        select(Admin).where(Admin.id == admin_id, Admin.is_active.is_(True))
    )
    admin = admin_result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Admin not found")

    # Rotate refresh token
    stored.revoked_at = datetime.now(timezone.utc)
    await db.flush()
    return await issue_tokens(db, admin)


async def logout_admin(
    db: AsyncSession,
    admin_id: int,
    refresh_token: str | None = None,
) -> None:
    if refresh_token:
        payload = decode_token(refresh_token)
        if payload and payload.get("jti"):
            await db.execute(
                update(AdminRefreshToken)
                .where(
                    AdminRefreshToken.jti == payload["jti"],
                    AdminRefreshToken.admin_id == admin_id,
                )
                .values(revoked_at=datetime.now(timezone.utc))
            )
            await db.flush()
            return
    await revoke_all_refresh_tokens(db, admin_id)


async def revoke_all_refresh_tokens(db: AsyncSession, admin_id: int) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(AdminRefreshToken)
        .where(AdminRefreshToken.admin_id == admin_id, AdminRefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await db.flush()


