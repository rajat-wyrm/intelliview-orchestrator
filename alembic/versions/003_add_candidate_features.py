"""add candidate features

Revision ID: 003_add_candidate_features
Revises: ba062b2def4d
Create Date: 2026-08-27

"""

import sqlalchemy as sa

from alembic import op

revision = "003_add_candidate_features"
down_revision = "ba062b2def4d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "candidates",
        sa.Column(
            "practice_streak", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.add_column(
        "candidates",
        sa.Column("last_practice_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("candidates", sa.Column("badges", sa.JSON(), nullable=True))
    op.add_column(
        "candidates",
        sa.Column(
            "status", sa.String(length=50), nullable=True, server_default="unverified"
        ),
    )
    op.add_column("candidates", sa.Column("role", sa.String(length=100), nullable=True))
    op.add_column(
        "candidates",
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_candidates_deleted_at"), "candidates", ["deleted_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_candidates_deleted_at"), table_name="candidates")
    op.drop_column("candidates", "deleted_at")
    op.drop_column("candidates", "role")
    op.drop_column("candidates", "status")
    op.drop_column("candidates", "badges")
    op.drop_column("candidates", "last_practice_date")
    op.drop_column("candidates", "practice_streak")
    op.drop_column("candidates", "is_verified")
