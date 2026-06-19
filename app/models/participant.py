from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, StringEnum
from app.models.enums import ParticipantTaskStatus

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.award import Award
    from app.models.push_subscription import PushSubscription
    from app.models.leaderboard import Leaderboard
    from app.models.match import Match
    from app.models.selfie import Selfie
    from app.models.task import Task


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    qr_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Progress (denormalized; updated on task/match completion)
    tasks_completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matches_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00"), nullable=False
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    event: Mapped["Event"] = relationship(back_populates="participants")
    participant_tasks: Mapped[list["ParticipantTask"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )
    matches_initiated: Mapped[list["Match"]] = relationship(
        back_populates="initiator",
        foreign_keys="Match.initiator_id",
        cascade="all, delete-orphan",
    )
    matches_received: Mapped[list["Match"]] = relationship(
        back_populates="partner",
        foreign_keys="Match.partner_id",
    )
    selfies: Mapped[list["Selfie"]] = relationship(back_populates="participant", cascade="all, delete-orphan")
    leaderboard_entry: Mapped["Leaderboard | None"] = relationship(
        back_populates="participant", uselist=False, cascade="all, delete-orphan"
    )
    awards: Mapped[list["Award"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )
    push_subscriptions: Mapped[list["PushSubscription"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )

    # Backward-compatible alias for API layer
    @property
    def qr_token(self) -> str:
        return self.qr_code


class ParticipantTask(Base):
    __tablename__ = "participant_tasks"
    __table_args__ = (
        UniqueConstraint("participant_id", "task_id", name="uq_participant_task"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ParticipantTaskStatus] = mapped_column(
        StringEnum(ParticipantTaskStatus, name="participanttaskstatus"),
        default=ParticipantTaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    participant: Mapped["Participant"] = relationship(back_populates="participant_tasks")
    task: Mapped["Task"] = relationship(back_populates="participant_tasks")
