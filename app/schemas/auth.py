from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AdminRole


class AdminSecurityCodeLoginRequest(BaseModel):
    security_code: str = Field(..., min_length=1, max_length=256)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AdminOut(BaseModel):
    id: int
    email: str
    name: str
    role: AdminRole
    is_active: bool
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminSessionOut(BaseModel):
    admin: AdminOut
    token_type: str = "bearer"
