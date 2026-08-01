"""Candidate ORM model."""

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship

from database.models._base import Base, utcnow


class Candidate(Base):
    """Candidate profile"""

    __tablename__ = "candidates"

    candidate_id = Column(String(255), primary_key=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    resume_text = Column(String(10000), nullable=True)
    skills = Column(JSON, nullable=True, default=list)
    interview_history = Column(JSON, nullable=True, default=list)
    demographics = Column(JSON, nullable=True, default=dict)
    avg_score = Column(Float, nullable=True, index=True)
    total_interviews = Column(Integer, nullable=False, default=0, index=True)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    interview_sessions = relationship("InterviewSession", back_populates="candidate")

    def __repr__(self):
        return f"<Candidate(candidate_id='{self.candidate_id}', name='{self.name}')>"
