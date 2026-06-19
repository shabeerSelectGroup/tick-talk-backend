from fastapi import APIRouter, Body, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireAnyAdmin, get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.schemas.auth import (
    AdminOut,
    AdminSecurityCodeLoginRequest,
    AdminSessionOut,
    RefreshResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.common import ok
from app.services import admin_auth as auth_service

router = APIRouter()


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    body: AdminSecurityCodeLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    admin = await auth_service.authenticate_admin_by_security_code(db, body.security_code)
    tokens = await auth_service.issue_tokens(db, admin, request)
    admin_out = AdminOut.model_validate(admin)
    return ok(
        {
            **TokenResponse(**tokens).model_dump(),
            "admin": admin_out.model_dump(),
        }
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    body: RefreshTokenRequest | None = Body(None),
):
    refresh_token = body.refresh_token if body else None
    await auth_service.logout_admin(db, admin.id, refresh_token)
    return ok({"message": "Logged out successfully"})


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    tokens = await auth_service.refresh_access_token(db, body.refresh_token)
    return ok(RefreshResponse(**tokens).model_dump())


@router.get("/me")
async def me(admin: RequireAnyAdmin):
    return ok(
        {
            "admin": {
                "id": admin.id,
                "email": admin.email,
                "name": admin.name,
                "role": admin.role.value,
                "is_active": admin.is_active,
                "last_login_at": admin.last_login_at,
            }
        }
    )
