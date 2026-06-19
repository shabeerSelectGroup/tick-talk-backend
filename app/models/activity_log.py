from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, StringEnum
from app.models.enums import ActivityType

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.participant import Participant


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        StringEnum(ActivityType, name="activitytype"),
        nullable=False,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    event: Mapped["Event"] = relationship(back_populates="activity_logs")
    participant: Mapped["Participant | None"] = relationship()
