"""add llm_usage to interview_sessions

Revision ID: 002_add_llm_usage
Revises: d7d869570be9
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa


revision = '002_add_llm_usage'
down_revision = 'd7d869570be9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'interview_sessions',
        sa.Column('llm_usage', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('interview_sessions', 'llm_usage')