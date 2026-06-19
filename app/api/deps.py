from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import decode_token
from app.db.session import get_db
from app.models.admin import Admin
from app.models.enums import AdminRole
from app.models.event import Event
from app.models.participant import Participant
SESSION_PREFIX = "session:"


async def get_current_admin(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> Admin:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(authorization[7:])
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    admin_id = int(payload["sub"])
    result = await db.execute(select(Admin).where(Admin.id == admin_id, Admin.is_active.is_(True)))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Admin not found or inactive")
    if admin.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin role is no longer supported")

    # Optional: verify role in token matches DB (detect role change)
    token_role = payload.get("role")
    if token_role and token_role != admin.role.value:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token invalidated; please sign in again")

    return admin


def require_roles(*roles: AdminRole) -> Callable:
    """Dependency factory: restrict route to specific admin roles."""

    async def _check(admin: Admin = Depends(get_current_admin)) -> Admin:
        if admin.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(r.value for r in roles)}",
            )
        return admin

    return _check


RequireSuperAdmin = Annotated[Admin, Depends(require_roles(AdminRole.SUPER_ADMIN))]
RequireAnyAdmin = Annotated[Admin, Depends(get_current_admin)]


async def get_admin_event(
    event_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> Event:
    """Load event for the authenticated admin."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


async def get_current_participant(
    authorization: Annotated[str | None, Header()] = None,
    x_session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    db: AsyncSession = Depends(get_db),
) -> Participant:
    token = None
    if authorization and authorization.startswith("Session "):
        token = authorization[8:]
    elif x_session_token:
        token = x_session_token
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing session")

    session_key = f"{SESSION_PREFIX}{token}"
    participant_id: str | None = None
    try:
        from redis.exceptions import RedisError

        redis = await get_redis()
        participant_id = await redis.get(session_key)
        if participant_id:
            result = await db.execute(
                select(Participant).where(
                    Participant.id == int(participant_id), Participant.is_active.is_(True)
                )
            )
            participant = result.scalar_one_or_none()
            if participant:
                return participant
    except (RedisError, OSError, ConnectionError, TimeoutError):
        participant_id = None

    result = await db.execute(
        select(Participant).where(
            Participant.session_token == token, Participant.is_active.is_(True)
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    try:
        from redis.exceptions import RedisError

        redis = await get_redis()
        await redis.setex(session_key, 86400, str(participant.id))
    except (RedisError, OSError, ConnectionError, TimeoutError):
        pass

    return participant
