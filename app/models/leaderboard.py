from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.participant import Participant


class Leaderboard(Base):
    """
    Competition-mode scores and rankings per participant.
    One row per participant per event; updated on scoring events.
    """

    __tablename__ = "leaderboards"
    __table_args__ = (
        UniqueConstraint("event_id", "participant_id", name="uq_leaderboard_event_participant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matches_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    event: Mapped["Event"] = relationship(back_populates="leaderboard_entries")
    participant: Mapped["Participant"] = relationship(back_populates="leaderboard_entry")
