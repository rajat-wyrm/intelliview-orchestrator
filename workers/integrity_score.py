"""
Integrity Scorer
Combines signals from ScreenLock, CV service, and risk engine to output a single score.
"""

from typing import Optional


class IntegrityScorer:
    """
    Calculates a single integrity score for an interview session.
    Combines:
    - ScreenLock tab-switch events
    - CV-service face/gaze results
    - Risk engine final score
    """

    @classmethod
    def calculate_integrity_score(
        cls,
        tab_switches: Optional[int] = None,
        cv_flags: Optional[int] = None,
        risk_score: Optional[float] = None,
    ) -> int:
        """
        Calculate a single 0-100 integrity score from given signals.
        Returns 100 minus calculated penalties.
        """
        base_score = 100
        total_penalty = 0

        # Tab switch penalty: 5 per switch, max 20
        if tab_switches is not None and tab_switches > 0:
            total_penalty += min(tab_switches * 5, 20)

        # CV flags penalty: 10 per flag, max 30
        if cv_flags is not None and cv_flags > 0:
            total_penalty += min(cv_flags * 10, 30)

        # Risk score penalty: max 50 points based on risk_score (0.0 - 1.0)
        if risk_score is not None and risk_score > 0.0:
            # Clamp risk score between 0.0 and 1.0 just in case
            safe_risk_score = min(max(risk_score, 0.0), 1.0)
            total_penalty += int(safe_risk_score * 50)

        final_score = base_score - total_penalty
        return max(0, min(final_score, 100))
