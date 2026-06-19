"""Event management fields and settings

Revision ID: 003
Revises: 002
Create Date: 2026-06-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("task_count", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "event_settings",
        sa.Column("enable_awards", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "event_settings",
        sa.Column("show_live_ranking", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "event_settings",
        sa.Column("show_ranking_only_at_end", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "event_settings",
        sa.Column("enable_selfie_verification", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "event_settings",
        sa.Column("enable_public_wall", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )


def downgrade() -> None:
    op.drop_column("event_settings", "enable_public_wall")
    op.drop_column("event_settings", "enable_selfie_verification")
    op.drop_column("event_settings", "show_ranking_only_at_end")
    op.drop_column("event_settings", "show_live_ranking")
    op.drop_column("event_settings", "enable_awards")
    op.drop_column("events", "task_count")
