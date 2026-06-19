from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.event import Event


class EventSettings(Base):
    """Per-event configuration: duration, leaderboard, wall, selfies, awards."""

    __tablename__ = "event_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Leaderboard & competition display
    leaderboard_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_awards: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_live_ranking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_ranking_only_at_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    leaderboard_size: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    show_scores_on_wall: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Features
    enable_selfie_verification: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_public_wall: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Competition scoring
    task_completion_points: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    speed_bonus_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    speed_bonus_max_points: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    speed_bonus_window_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)

    # Scoring & networking
    scan_match_points: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    allow_self_scan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_duplicate_matches: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    selfie_requires_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_selfies_per_participant: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    min_matches_for_completion: Mapped[int | None] = mapped_column(Integer, nullable=True)

    extra_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    event: Mapped["Event"] = relationship(back_populates="settings")
