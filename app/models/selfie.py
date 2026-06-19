from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, StringEnum
from app.models.enums import SelfieStatus

if TYPE_CHECKING:
    from app.models.admin import Admin
    from app.models.event import Event
    from app.models.match import Match
    from app.models.participant import Participant
    from app.models.task import Task


class Selfie(Base):
    __tablename__ = "selfies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    match_id: Mapped[int | None] = mapped_column(
        ForeignKey("matches.id", ondelete="SET NULL"), nullable=True, index=True
    )

    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    thumbnail_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[SelfieStatus] = mapped_column(
        StringEnum(SelfieStatus, name="selfiestatus"),
        default=SelfieStatus.PENDING,
        nullable=False,
        index=True,
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"), nullable=True
    )
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event: Mapped["Event"] = relationship(back_populates="selfies")
    participant: Mapped["Participant"] = relationship(back_populates="selfies")
    task: Mapped["Task | None"] = relationship(back_populates="selfies")
    match: Mapped["Match | None"] = relationship(back_populates="selfies")
    reviewer: Mapped["Admin | None"] = relationship(back_populates="reviewed_selfies")
