"""merge email verification migration head

Revision ID: 2b9d49b93827
Revises: 55b99d3322a5, 850f7086ffdd
Create Date: 2026-08-28 05:16:36.062145

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "2b9d49b93827"
down_revision: str | Sequence[str] | None = ("55b99d3322a5", "850f7086ffdd")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
