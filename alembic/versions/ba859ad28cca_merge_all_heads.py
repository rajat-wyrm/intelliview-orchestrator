"""merge all heads

Revision ID: ba859ad28cca
Revises: 55b99d3322a5, a9c4c63a79be
Create Date: 2026-09-01 18:58:40.512117

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "ba859ad28cca"
down_revision: str | Sequence[str] | None = ("55b99d3322a5", "a9c4c63a79be")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
