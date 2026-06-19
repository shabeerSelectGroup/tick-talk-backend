from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, StringEnum
from app.models.enums import MatchType

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.participant import Participant
    from app.models.selfie import Selfie
    from app.models.task import Task


class Match(Base):
    """
    Completed networking interaction between two participants.
    Directed: initiator performed the action toward partner (e.g. QR scan).
    """

    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("event_id", "initiator_id", "partner_id", name="uq_match_event_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    initiator_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    partner_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    match_type: Mapped[MatchType] = mapped_column(
        StringEnum(MatchType, name="matchtype"),
        default=MatchType.QR_SCAN,
        nullable=False,
    )
    points_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relationship_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    event: Mapped["Event"] = relationship(back_populates="matches")
    initiator: Mapped["Participant"] = relationship(
        back_populates="matches_initiated", foreign_keys=[initiator_id]
    )
    partner: Mapped["Participant"] = relationship(
        back_populates="matches_received", foreign_keys=[partner_id]
    )
    task: Mapped["Task | None"] = relationship(back_populates="matches")
    selfies: Mapped[list["Selfie"]] = relationship(back_populates="match")
