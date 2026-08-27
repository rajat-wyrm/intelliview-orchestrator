"""merge heads

Revision ID: 850f7086ffdd
Revises: 003_add_candidate_deleted_at, 25b9705eb8d5
Create Date: 2026-08-23 08:07:05.596843

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "850f7086ffdd"
down_revision: str | Sequence[str] | None = (
    "003_add_candidate_deleted_at",
    "25b9705eb8d5",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
