"""Admin roles and refresh token storage

Revision ID: 002
Revises: 001
Create Date: 2026-06-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admins",
        sa.Column(
            "role",
            sa.Enum("super_admin", "event_admin", name="adminrole"),
            nullable=False,
            server_default="super_admin",
        ),
    )
    op.add_column("admins", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_admins_role", "admins", ["role"])

    op.create_table(
        "admin_refresh_tokens",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("jti", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti", name="uq_admin_refresh_jti"),
    )
    op.create_index("ix_admin_refresh_admin_id", "admin_refresh_tokens", ["admin_id"])
    op.create_index("ix_admin_refresh_expires", "admin_refresh_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_table("admin_refresh_tokens")
    op.drop_index("ix_admins_role", table_name="admins")
    op.drop_column("admins", "last_login_at")
    op.drop_column("admins", "role")
