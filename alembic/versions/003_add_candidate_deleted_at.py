"""add deleted_at to candidates

Revision ID: 003_add_candidate_deleted_at
Revision: ba062b2def4d
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_add_candidate_deleted_at"
down_revision: str | Sequence[str] | None = "ba062b2def4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "candidates",
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_candidates_deleted_at", "candidates", ["deleted_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_candidates_deleted_at", table_name="candidates")
    op.drop_column("candidates", "deleted_at")
