from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, StringEnum
from app.models.enums import TaskType

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.match import Match
    from app.models.participant import ParticipantTask
    from app.models.selfie import Selfie


class Task(Base):
    """
    Event-scoped task shared by all participants.
    Admin configures the list per event.
    """

    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("event_id", "slug", name="uq_tasks_event_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[TaskType] = mapped_column(
        StringEnum(TaskType, name="tasktype"),
        default=TaskType.MANUAL,
        nullable=False,
    )
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    event: Mapped["Event"] = relationship(back_populates="tasks")
    participant_tasks: Mapped[list["ParticipantTask"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    matches: Mapped[list["Match"]] = relationship(back_populates="task")
    selfies: Mapped[list["Selfie"]] = relationship(back_populates="task")
