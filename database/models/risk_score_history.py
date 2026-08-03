"""RiskScoreHistory ORM model."""

from sqlalchemy import Column, DateTime, Float, Integer, String

from database.models._base import Base, utcnow


class RiskScoreHistory(Base):
    """Historical risk scores recorded from completed interviews for dynamic threshold tuning."""

    __tablename__ = "risk_score_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    risk_score = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)

    def __repr__(self):
        return (
            f"<RiskScoreHistory(id={self.id}, session_id='{self.session_id}', risk_score={self.risk_score})>"
        )
