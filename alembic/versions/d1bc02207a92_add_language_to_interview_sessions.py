"""add language to interview sessions

Revision ID: d1bc02207a92
Revises: 002_add_llm_usage
Create Date: 2026-08-12 02:50:43.110538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1bc02207a92'
down_revision: Union[str, Sequence[str], None] = '002_add_llm_usage'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "interview_sessions",
        sa.Column(
            "language",
            sa.String(length=10),
            nullable=False,
            server_default="en",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("interview_sessions", "language")
