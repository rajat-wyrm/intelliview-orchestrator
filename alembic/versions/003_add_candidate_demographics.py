"""add demographics to candidates

Revision ID: 003_add_candidate_demographics
Revises: 002_add_llm_usage
Create Date: 2026-08-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "003_add_candidate_demographics"
down_revision = "002_add_llm_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column("demographics", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidates", "demographics")
