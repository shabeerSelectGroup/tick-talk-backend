"""Competition scoring settings and awards table."""

from alembic import op
import sqlalchemy as sa

revision = "005_competition_scoring"
down_revision = "004_selfie_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_settings",
        sa.Column("task_completion_points", sa.Integer(), nullable=False, server_default="100"),
    )
    op.add_column(
        "event_settings",
        sa.Column("speed_bonus_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "event_settings",
        sa.Column("speed_bonus_max_points", sa.Integer(), nullable=False, server_default="25"),
    )
    op.add_column(
        "event_settings",
        sa.Column("speed_bonus_window_seconds", sa.Integer(), nullable=False, server_default="300"),
    )

    op.create_table(
        "awards",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("participant_id", sa.BigInteger(), nullable=False),
        sa.Column("place", sa.Integer(), nullable=False),
        sa.Column("award_type", sa.String(32), nullable=False, server_default="podium"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tasks_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "participant_id", name="uq_award_event_participant"),
    )
    op.create_index("ix_awards_event_id", "awards", ["event_id"])
    op.create_index("ix_awards_event_place", "awards", ["event_id", "place"])


def downgrade() -> None:
    op.drop_table("awards")
    op.drop_column("event_settings", "speed_bonus_window_seconds")
    op.drop_column("event_settings", "speed_bonus_max_points")
    op.drop_column("event_settings", "speed_bonus_enabled")
    op.drop_column("event_settings", "task_completion_points")
