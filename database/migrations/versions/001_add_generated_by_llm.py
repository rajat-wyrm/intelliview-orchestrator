"""add generated_by_llm to questions

Revision ID: 001_add_generated_by_llm
Revises: 
Create Date: 2026-07-21

"""
from alembic import op
import sqlalchemy as sa


revision = '001_add_generated_by_llm'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('generated_by_llm', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('questions', 'generated_by_llm')