"""Complete Tick Talk schema

Revision ID: 001
Revises:
Create Date: 2026-06-02

Tables: admins, events, event_settings, tasks, participants, participant_tasks,
        matches, selfies, activity_logs, leaderboards
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- admins ---
    op.create_table(
        "admins",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_admins_email"),
    )

    # --- events ---
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(12), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mode", sa.Enum("networking", "competition", name="eventmode"), nullable=False),
        sa.Column("status", sa.Enum("draft", "scheduled", "live", "ended", name="eventstatus"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("max_participants", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["admins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_events_code"),
    )
    op.create_index("ix_events_mode", "events", ["mode"])
    op.create_index("ix_events_status", "events", ["status"])
    op.create_index("ix_events_starts_at", "events", ["starts_at"])

    # --- event_settings (1:1) ---
    op.create_table(
        "event_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("leaderboard_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("leaderboard_size", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("show_scores_on_wall", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("scan_match_points", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("allow_self_scan", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("allow_duplicate_matches", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("selfie_requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("max_selfies_per_participant", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("min_matches_for_completion", sa.Integer(), nullable=True),
        sa.Column("extra_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_event_settings_event_id"),
    )
    op.create_index("ix_event_settings_event_id", "event_settings", ["event_id"])

    # --- tasks (event-scoped) ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.Enum("scan", "selfie", "manual", "quiz", name="tasktype"), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("available_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "slug", name="uq_tasks_event_slug"),
    )
    op.create_index("ix_tasks_event_id", "tasks", ["event_id"])
    op.create_index("ix_tasks_event_sort", "tasks", ["event_id", "sort_order"])

    # --- participants ---
    op.create_table(
        "participants",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("session_token", sa.String(64), nullable=False),
        sa.Column("qr_code", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("company", sa.String(120), nullable=True),
        sa.Column("title", sa.String(120), nullable=True),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("tasks_completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_percent", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_token", name="uq_participants_session_token"),
        sa.UniqueConstraint("qr_code", name="uq_participants_qr_code"),
    )
    op.create_index("ix_participants_event_id", "participants", ["event_id"])
    op.create_index("ix_participants_event_active", "participants", ["event_id", "is_active"])

    # --- participant_tasks ---
    op.create_table(
        "participant_tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("participant_id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "in_progress",
                "completed",
                "failed",
                "skipped",
                name="participanttaskstatus",
            ),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participant_id", "task_id", name="uq_participant_task"),
    )
    op.create_index("ix_participant_tasks_participant", "participant_tasks", ["participant_id"])
    op.create_index("ix_participant_tasks_status", "participant_tasks", ["status"])

    # --- matches ---
    op.create_table(
        "matches",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("initiator_id", sa.BigInteger(), nullable=False),
        sa.Column("partner_id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "match_type",
            sa.Enum("qr_scan", "manual", "task", "selfie", name="matchtype"),
            nullable=False,
        ),
        sa.Column("points_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relationship_note", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiator_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "initiator_id", "partner_id", name="uq_match_event_pair"),
        sa.CheckConstraint("initiator_id != partner_id", name="ck_match_not_self"),
    )
    op.create_index("ix_matches_event_id", "matches", ["event_id"])
    op.create_index("ix_matches_initiator", "matches", ["initiator_id"])
    op.create_index("ix_matches_partner", "matches", ["partner_id"])
    op.create_index("ix_matches_created_at", "matches", ["created_at"])

    # --- selfies ---
    op.create_table(
        "selfies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("participant_id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=True),
        sa.Column("image_url", sa.String(1024), nullable=False),
        sa.Column("thumbnail_url", sa.String(1024), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "rejected", name="selfiestatus"),
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["admins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_selfies_event_id", "selfies", ["event_id"])
    op.create_index("ix_selfies_participant_id", "selfies", ["participant_id"])
    op.create_index("ix_selfies_status", "selfies", ["status"])

    # --- activity_logs ---
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("participant_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "activity_type",
            sa.Enum(
                "participant_joined",
                "task_completed",
                "match_created",
                "selfie_uploaded",
                "selfie_approved",
                "score_updated",
                "event_started",
                "event_ended",
                "winner_announced",
                name="activitytype",
            ),
            nullable=False,
        ),
        sa.Column("summary", sa.String(512), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_logs_event_created", "activity_logs", ["event_id", "created_at"])
    op.create_index("ix_activity_logs_type", "activity_logs", ["activity_type"])

    # --- leaderboards ---
    op.create_table(
        "leaderboards",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("participant_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("tasks_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "participant_id", name="uq_leaderboard_event_participant"),
    )
    op.create_index("ix_leaderboards_event_id", "leaderboards", ["event_id"])
    op.create_index("ix_leaderboards_rank", "leaderboards", ["event_id", "rank"])
    op.create_index(
        "ix_leaderboards_event_score",
        "leaderboards",
        ["event_id", "score", "finished_at"],
    )


def downgrade() -> None:
    for table in (
        "leaderboards",
        "activity_logs",
        "selfies",
        "matches",
        "participant_tasks",
        "participants",
        "tasks",
        "event_settings",
        "events",
        "admins",
    ):
        op.drop_table(table)
