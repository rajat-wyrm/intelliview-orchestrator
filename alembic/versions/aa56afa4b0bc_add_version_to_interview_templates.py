"""add version to interview templates

Revision ID: aa56afa4b0bc
Revises: 002_add_llm_usage
Create Date: 2026-08-28 19:30:43.341760

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa56afa4b0bc"
down_revision: str | Sequence[str] | None = "b08fe3635da3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "interview_templates",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("interview_templates", "version")
