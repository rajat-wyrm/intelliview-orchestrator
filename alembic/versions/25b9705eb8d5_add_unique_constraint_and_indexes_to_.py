"""add unique constraint and indexes to interview_schedules

Revision ID: 25b9705eb8d5
Revises: ba062b2def4d
Create Date: 2026-08-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "25b9705eb8d5"
down_revision: str | Sequence[str] | None = "ba062b2def4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: ensure interview_schedules exists with unique constraint and indexes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "interview_schedules" not in tables:
        op.create_table(
            "interview_schedules",
            sa.Column("id", sa.String(length=255), primary_key=True, nullable=False),
            sa.Column(
                "candidate_id",
                sa.String(length=255),
                sa.ForeignKey("candidates.candidate_id"),
                nullable=False,
            ),
            sa.Column("interviewer_id", sa.String(length=255), nullable=False),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "status",
                sa.String(length=50),
                nullable=False,
                server_default="scheduled",
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "candidate_id", "scheduled_at", name="uq_schedule_candidate_slot"
            ),
        )
        op.create_index(
            op.f("ix_interview_schedules_id"),
            "interview_schedules",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_interview_schedules_candidate_id"),
            "interview_schedules",
            ["candidate_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_interview_schedules_interviewer_id"),
            "interview_schedules",
            ["interviewer_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_interview_schedules_scheduled_at"),
            "interview_schedules",
            ["scheduled_at"],
            unique=False,
        )
        op.create_index(
            op.f("ix_interview_schedules_status"),
            "interview_schedules",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_schedule_interviewer_time",
            "interview_schedules",
            ["interviewer_id", "scheduled_at"],
            unique=False,
        )
        op.create_index(
            "ix_schedule_status_time",
            "interview_schedules",
            ["status", "scheduled_at"],
            unique=False,
        )
    else:
        existing_uqs = {
            uq["name"]
            for uq in inspector.get_unique_constraints("interview_schedules")
            if uq.get("name")
        }
        existing_ixs = {
            ix["name"]
            for ix in inspector.get_indexes("interview_schedules")
            if ix.get("name")
        }

        with op.batch_alter_table("interview_schedules") as batch_op:
            if "uq_schedule_candidate_slot" not in existing_uqs:
                batch_op.create_unique_constraint(
                    "uq_schedule_candidate_slot",
                    ["candidate_id", "scheduled_at"],
                )
            if "ix_schedule_interviewer_time" not in existing_ixs:
                batch_op.create_index(
                    "ix_schedule_interviewer_time",
                    ["interviewer_id", "scheduled_at"],
                )
            if "ix_schedule_status_time" not in existing_ixs:
                batch_op.create_index(
                    "ix_schedule_status_time",
                    ["status", "scheduled_at"],
                )


def downgrade() -> None:
    """Downgrade schema: remove unique constraint and composite indexes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "interview_schedules" in tables:
        existing_uqs = {
            uq["name"]
            for uq in inspector.get_unique_constraints("interview_schedules")
            if uq.get("name")
        }
        existing_ixs = {
            ix["name"]
            for ix in inspector.get_indexes("interview_schedules")
            if ix.get("name")
        }

        with op.batch_alter_table("interview_schedules") as batch_op:
            if "ix_schedule_status_time" in existing_ixs:
                batch_op.drop_index("ix_schedule_status_time")
            if "ix_schedule_interviewer_time" in existing_ixs:
                batch_op.drop_index("ix_schedule_interviewer_time")
            if "uq_schedule_candidate_slot" in existing_uqs:
                batch_op.drop_constraint("uq_schedule_candidate_slot", type_="unique")
