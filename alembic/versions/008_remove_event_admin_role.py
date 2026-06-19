"""Promote event_admin accounts to super_admin and remove event-admin seed user."""

from alembic import op

revision = "008_remove_event_admin_role"
down_revision = "007_push_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE admins SET role = 'super_admin' WHERE role = 'event_admin'")
    op.execute("DELETE FROM admins WHERE email = 'events@ticktalk.app'")


def downgrade() -> None:
    pass
