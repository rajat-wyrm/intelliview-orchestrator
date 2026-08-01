"""Question ORM model."""

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

from database.models._base import Base, utcnow


class Question(Base):
    """Interview question bank entry"""

    __tablename__ = "questions"

    question_id = Column(String(255), primary_key=True, index=True, nullable=False)
    text = Column(String(1000), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    difficulty = Column(String(20), nullable=False, default="medium")
    tags = Column(JSON, nullable=True, default=list)
    usage_count = Column(Integer, nullable=False, default=0, index=True)
    avg_score = Column(Float, nullable=True, index=True)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return (
            f"<Question(question_id='{self.question_id}', "
            f"category='{self.category}', "
            f"difficulty='{self.difficulty}')>"
        )
