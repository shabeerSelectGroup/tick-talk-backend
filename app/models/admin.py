from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, StringEnum
from app.models.enums import AdminRole

if TYPE_CHECKING:
    from app.models.admin_refresh_token import AdminRefreshToken
    from app.models.event import Event
    from app.models.selfie import Selfie


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[AdminRole] = mapped_column(
        StringEnum(AdminRole, name="adminrole"),
        default=AdminRole.SUPER_ADMIN,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    events: Mapped[list["Event"]] = relationship(back_populates="created_by_admin")
    reviewed_selfies: Mapped[list["Selfie"]] = relationship(back_populates="reviewer")
    refresh_tokens: Mapped[list["AdminRefreshToken"]] = relationship(
        back_populates="admin", cascade="all, delete-orphan"
    )

    @property
    def is_super_admin(self) -> bool:
        return self.role == AdminRole.SUPER_ADMIN
