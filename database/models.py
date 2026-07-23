"""
SQLAlchemy ORM Models for AI Interview Orchestrator
Defines database models using declarative base
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    Integer,
    String,
)
from sqlalchemy.sql import func  # noqa: F401  (re-exported for ORM consumers)

from database.db import Base


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


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
    candidate_id = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")
    assigned_node = Column(String(255), nullable=True)
    start_time = Column(DateTime, nullable=True, default=utcnow)
    end_time = Column(DateTime, nullable=True)
    risk_score = Column(Float, nullable=True)

    # Analysis results stored as JSON
    video_analysis = Column(JSON, nullable=True)
    audio_analysis = Column(JSON, nullable=True)
    evaluation_analysis = Column(JSON, nullable=True)

    # Interview Q&A tracking
    questions_asked = Column(JSON, nullable=True, default=list)
    answers_provided = Column(JSON, nullable=True, default=list)
    feedback_generated = Column(JSON, nullable=True, default=list)
    overall_score = Column(Float, nullable=True)
    template_id = Column(String(255), nullable=True)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return f"<InterviewSession(session_id='{self.session_id}', candidate_id='{self.candidate_id}', status='{self.status}', risk_score={self.risk_score})>"


class Question(Base):
    """Interview question bank entry"""

    __tablename__ = "questions"

    question_id = Column(String(255), primary_key=True, index=True, nullable=False)
    text = Column(String(1000), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    difficulty = Column(String(20), nullable=False, default="medium")
    tags = Column(JSON, nullable=True, default=list)
    usage_count = Column(Integer, nullable=False, default=0)
    avg_score = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return f"<Question(question_id='{self.question_id}', category='{self.category}', difficulty='{self.difficulty}')>"


class Candidate(Base):
    """Candidate profile"""

    __tablename__ = "candidates"

    candidate_id = Column(String(255), primary_key=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    resume_text = Column(String(10000), nullable=True)
    skills = Column(JSON, nullable=True, default=list)
    interview_history = Column(JSON, nullable=True, default=list)
    # Optional demographic information for fairness auditing.
    # This data is NOT passed to the LLM and is only used for compliance analytics.
    demographics = Column(JSON, nullable=True, default=dict)
    avg_score = Column(Float, nullable=True)
    total_interviews = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return f"<Candidate(candidate_id='{self.candidate_id}', name='{self.name}')>"


class InterviewTemplate(Base):
    """Interview template definition"""

    __tablename__ = "interview_templates"

    template_id = Column(String(255), primary_key=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    interview_type = Column(String(50), nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False, default=60)
    question_count = Column(Integer, nullable=False, default=10)
    category_distribution = Column(JSON, nullable=True, default=dict)
    difficulty_distribution = Column(JSON, nullable=True, default=dict)
    usage_count = Column(Integer, nullable=False, default=0)
    success_rate = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return f"<InterviewTemplate(template_id='{self.template_id}', name='{self.name}', type='{self.interview_type}')>"
