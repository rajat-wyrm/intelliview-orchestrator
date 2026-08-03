"""InterviewTemplate ORM model."""

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship

from database.models._base import Base, utcnow


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
    usage_count = Column(Integer, nullable=False, default=0, index=True)
    success_rate = Column(Float, nullable=True, index=True)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    interview_sessions = relationship("InterviewSession", back_populates="template")

    def __repr__(self):
        return (
            f"<InterviewTemplate(template_id='{self.template_id}', "
            f"name='{self.name}', "
            f"type='{self.interview_type}')>"
        )
