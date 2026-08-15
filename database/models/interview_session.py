"""InterviewSession ORM model."""

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
)
from sqlalchemy.orm import relationship

from database.models._base import Base, utcnow


class InterviewSession(Base):
    """
    InterviewSession ORM Model
    Represents an interview session with candidate and processing details
    """

    __tablename__ = "interview_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'pending',"
            "'CREATED',"
            "'QUEUED',"
            "'VIDEO_PROCESSING',"
            "'AUDIO_PROCESSING',"
            "'EVALUATING',"
            "'PROCESSING',"
            "'COMPLETED',"
            "'FAILED',"
            "'TIMEOUT',"
            "'CANCELLED'"
            ")",
            name="ck_interview_status",
        ),
        CheckConstraint(
            "risk_score IS NULL OR risk_score >= 0",
            name="ck_risk_score_non_negative",
        ),
        CheckConstraint(
            "overall_score IS NULL OR overall_score >= 0",
            name="ck_overall_score_non_negative",
        ),
    )

    session_id = Column(String(255), primary_key=True, index=True, nullable=False)
    candidate_id = Column(
        String(255), ForeignKey("candidates.candidate_id"), nullable=False, index=True
    )
    language = Column(
    String(10),
    nullable=False,
    default="en",
    )
    status = Column(String(50), nullable=False, default="pending", index=True)
    assigned_node = Column(String(255), nullable=True)
    start_time = Column(DateTime, nullable=True, default=utcnow)
    end_time = Column(DateTime, nullable=True)
    risk_score = Column(Float, nullable=True)
    video_analysis = Column(JSON, nullable=True)
    audio_analysis = Column(JSON, nullable=True)
    evaluation_analysis = Column(JSON, nullable=True)
    questions_asked = Column(JSON, nullable=True, default=list)
    answers_provided = Column(JSON, nullable=True, default=list)
    feedback_generated = Column(JSON, nullable=True, default=list)
    overall_score = Column(Float, nullable=True, index=True)
    template_id = Column(
        String(255),
        ForeignKey("interview_templates.template_id"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    candidate = relationship("Candidate", back_populates="interview_sessions")
    template = relationship("InterviewTemplate", back_populates="interview_sessions")

    def __repr__(self):
        return (
            f"<InterviewSession(session_id='{self.session_id}', "
            f"candidate_id='{self.candidate_id}', "
            f"status='{self.status}', "
            f"risk_score={self.risk_score})>"
        )
