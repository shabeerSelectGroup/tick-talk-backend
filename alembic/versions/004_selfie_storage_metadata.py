"""Selfie storage: match association and metadata."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_selfie_storage"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("selfies", sa.Column("match_id", sa.BigInteger(), nullable=True))
    op.add_column("selfies", sa.Column("thumbnail_storage_key", sa.String(512), nullable=True))
    op.add_column("selfies", sa.Column("metadata_json", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_selfies_match_id",
        "selfies",
        "matches",
        ["match_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_selfies_match_id", "selfies", ["match_id"])


def downgrade() -> None:
    op.drop_index("ix_selfies_match_id", table_name="selfies")
    op.drop_constraint("fk_selfies_match_id", "selfies", type_="foreignkey")
    op.drop_column("selfies", "metadata_json")
    op.drop_column("selfies", "thumbnail_storage_key")
    op.drop_column("selfies", "match_id")
