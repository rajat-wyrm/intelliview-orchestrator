"""
Risk History Manager

Handles storage and retrieval of historical interview
risk scores from the InterviewSession table.
"""

from sqlalchemy import select

from database.db import SessionLocal
from database.models import InterviewSession


class RiskHistoryManager:
    """
    Handles historical interview risk scores.
    """

    @staticmethod
    def get_all_scores() -> list[float]:
        """
        Fetch all historical risk scores.
        """

        with SessionLocal() as db:

            scores = db.execute(
                select(InterviewSession.risk_score)
                .where(InterviewSession.risk_score.is_not(None))
            ).all()

            return [score[0] for score in scores]

    @staticmethod
    def save_score(
        session_id: str,
        risk_score: float,
    ) -> None:
        """
        Save the final risk score for an interview.
        """

        with SessionLocal() as db:

            session = db.get(
                InterviewSession,
                session_id,
            )

            if session is None:
                return

            session.risk_score = risk_score

            db.commit()

    @staticmethod
    def history_size() -> int:
        """
        Number of historical interview scores.
        """

        with SessionLocal() as db:

            return (
                db.query(InterviewSession)
                .filter(
                    InterviewSession.risk_score.isnot(None)
                )
                .count()
            )