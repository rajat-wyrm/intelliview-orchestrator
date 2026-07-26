import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import select

from database.models import Candidate

logger = logging.getLogger(__name__)

# Thresholds used to flag fairness concerns when score averages differ across
# demographic groups. These are intentionally simple heuristics for auditing
# review purposes rather than a comprehensive fairness assessment.
REVIEW_THRESHOLD = 0.1
ALERT_THRESHOLD = 0.2


class BiasAuditor:
    """Perform a lightweight fairness audit over interview evaluation scores.

    The current implementation uses the average score difference between
    demographic groups as a simple heuristic for detecting potential scoring
    disparities. It is not a comprehensive fairness evaluation and should not
    be treated as a legal compliance metric. More advanced metrics such as
    demographic parity, equalized odds, calibration, and subgroup-specific
    analysis could be implemented later if deeper compliance auditing is
    required.
    """

    REVIEW_THRESHOLD = REVIEW_THRESHOLD
    ALERT_THRESHOLD = ALERT_THRESHOLD

    def __init__(self, db_session: Any):
        self.db_session = db_session

    def analyze_scoring_consistency(
        self,
        evaluations: list[dict[str, Any]],
        demographic_attribute: str,
    ) -> dict[str, Any]:
        """Assess whether scoring differs meaningfully across demographic groups."""
        normalized_groups: dict[str, list[float]] = defaultdict(list)
        group_details: dict[str, dict[str, Any]] = {}

        for evaluation in evaluations or []:
            if not isinstance(evaluation, dict):
                continue

            score = evaluation.get("score")
            if score is None:
                continue

            try:
                numeric_score = float(score)
            except (TypeError, ValueError):
                continue

            group_value = self._resolve_group_value(evaluation, demographic_attribute)
            if group_value is None:
                continue

            normalized_group = self._normalize_group_value(group_value)
            normalized_groups[normalized_group].append(numeric_score)

        if not normalized_groups:
            return {
                "demographic_attribute": demographic_attribute,
                "groups": {},
                "fairness_gap": 0.0,
                "status": "PASS",
                "recommendations": [],
                "sample_size": 0,
            }

        for group_name, scores in sorted(normalized_groups.items()):
            group_details[group_name] = {
                "average_score": round(sum(scores) / len(scores), 3),
                "count": len(scores),
            }

        average_scores = [summary["average_score"] for summary in group_details.values()]
        fairness_gap = round(max(average_scores) - min(average_scores), 3) if len(average_scores) > 1 else 0.0

        recommendations: list[str] = []
        if len(group_details) >= 2 and fairness_gap > self.ALERT_THRESHOLD:
            recommendations.append(
                f"Investigate score differences for {demographic_attribute} before finalizing outcomes."
            )
            status = "ALERT"
        elif len(group_details) >= 2 and fairness_gap > self.REVIEW_THRESHOLD:
            recommendations.append("Review scoring dispersion across demographic groups for potential bias.")
            status = "REVIEW"
        else:
            status = "PASS"

        if len(group_details) < 2:
            recommendations = []
            status = "PASS"

        logger.info(
            "Bias audit completed for %s with gap %.3f and status %s",
            demographic_attribute,
            fairness_gap,
            status,
        )

        return {
            "demographic_attribute": demographic_attribute,
            "groups": group_details,
            "fairness_gap": fairness_gap,
            "status": status,
            "recommendations": recommendations,
            "sample_size": sum(summary["count"] for summary in group_details.values()),
        }

    def _resolve_group_value(self, evaluation: dict[str, Any], demographic_attribute: str) -> Any:
        direct_value = evaluation.get(demographic_attribute)
        if direct_value is not None:
            return direct_value

        candidate_id = evaluation.get("candidate_id")
        if not candidate_id or self.db_session is None:
            return None

        try:
            candidate = self.db_session.execute(
                select(Candidate).where(Candidate.candidate_id == str(candidate_id))
            ).scalar_one_or_none()
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.debug("Unable to resolve demographic attribute for candidate %s: %s", candidate_id, exc)
            return None

        if candidate is None:
            return None

        demographics = candidate.demographics or {}
        if isinstance(demographics, dict):
            return demographics.get(demographic_attribute)

        return None

    @staticmethod
    def _normalize_group_value(value: Any) -> str:
        if value is None:
            return "unknown"
        if isinstance(value, str):
            return value.strip().lower()
        return str(value).strip().lower()
