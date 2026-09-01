"""add email verification to candidates

Revision ID: 55b99d3322a5
Revises: ba062b2def4d
Create Date: 2026-08-26 18:12:14.486878

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "55b99d3322a5"
down_revision: str | Sequence[str] | None = "ba062b2def4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add email verification fields to candidates."""

    op.add_column(
        "candidates",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "candidates",
        sa.Column(
            "verification_token",
            sa.String(255),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_candidates_verification_token",
        "candidates",
        ["verification_token"],
        unique=True,
    )

    op.add_column(
        "candidates",
        sa.Column(
            "verification_token_expires_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove email verification fields from candidates."""
    op.drop_index("ix_candidates_verification_token", table_name="candidates")
    op.drop_column("candidates", "verification_token_expires_at")
    op.drop_column("candidates", "verification_token")
    op.drop_column("candidates", "email_verified")
