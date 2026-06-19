"""Web push notification subscriptions."""

from alembic import op
import sqlalchemy as sa

revision = "007_push_subscriptions"
down_revision = "006_export_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("participant_id", sa.BigInteger(), nullable=False),
        sa.Column("endpoint", sa.String(512), nullable=False),
        sa.Column("p256dh", sa.String(255), nullable=False),
        sa.Column("auth", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint", name="uq_push_endpoint"),
    )
    op.create_index("ix_push_participant", "push_subscriptions", ["participant_id"])


def downgrade() -> None:
    op.drop_table("push_subscriptions")
