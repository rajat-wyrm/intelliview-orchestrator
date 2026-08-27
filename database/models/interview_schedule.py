"""InterviewSchedule ORM model."""

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database.models._base import Base, utcnow


def generate_schedule_id() -> str:
    """Generate unique schedule identifier."""
    return f"sched_{uuid.uuid4().hex[:12]}"


class InterviewSchedule(Base):
    """InterviewSchedule model for managing scheduled interview events."""

    __tablename__ = "interview_schedules"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id", "scheduled_at", name="uq_schedule_candidate_slot"
        ),
        Index("ix_schedule_interviewer_time", "interviewer_id", "scheduled_at"),
        Index("ix_schedule_status_time", "status", "scheduled_at"),
    )

    id = Column(
        String(255),
        primary_key=True,
        default=generate_schedule_id,
        index=True,
        nullable=False,
    )
    candidate_id = Column(
        String(255),
        ForeignKey("candidates.candidate_id"),
        nullable=False,
        index=True,
    )
    interviewer_id = Column(
        String(255),
        nullable=False,
        index=True,
    )
    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    status = Column(
        String(50),
        nullable=False,
        default="scheduled",
        index=True,
    )
    notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    candidate = relationship("Candidate", backref="schedules")

    def __repr__(self):
        return (
            f"<InterviewSchedule(id='{self.id}', "
            f"candidate_id='{self.candidate_id}', "
            f"interviewer_id='{self.interviewer_id}', "
            f"scheduled_at='{self.scheduled_at}', "
            f"status='{self.status}')>"
        )
