"""merge email verification migration head

Revision ID: 2b9d49b93827
Revises: 55b99d3322a5, 850f7086ffdd
Create Date: 2026-08-28 05:16:36.062145

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b9d49b93827"
down_revision: Union[str, Sequence[str], None] = ("55b99d3322a5", "850f7086ffdd")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
