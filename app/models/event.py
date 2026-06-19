from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, StringEnum
from app.models.enums import EventMode, EventStatus

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.admin import Admin
    from app.models.event_settings import EventSettings
    from app.models.award import Award
    from app.models.export_job import ExportJob
    from app.models.leaderboard import Leaderboard
    from app.models.match import Match
    from app.models.participant import Participant
    from app.models.selfie import Selfie
    from app.models.task import Task


class Event(Base):
    """Corporate event. Mode controls networking vs competition behavior."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[EventMode] = mapped_column(
        StringEnum(EventMode, name="eventmode"),
        default=EventMode.NETWORKING,
        nullable=False,
        index=True,
    )
    status: Mapped[EventStatus] = mapped_column(
        StringEnum(EventStatus, name="eventstatus"),
        default=EventStatus.DRAFT,
        nullable=False,
        index=True,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    created_by_admin: Mapped["Admin | None"] = relationship(back_populates="events")
    settings: Mapped["EventSettings"] = relationship(
        back_populates="event", uselist=False, cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", order_by="Task.sort_order"
    )
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    matches: Mapped[list["Match"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    selfies: Mapped[list["Selfie"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    leaderboard_entries: Mapped[list["Leaderboard"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    awards: Mapped[list["Award"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    export_jobs: Mapped[list["ExportJob"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
