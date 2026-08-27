"""
A/B Testing Framework for Risk Scoring

Executes multiple risk scoring models on the same interview data
and exposes their results for comparison without affecting the
existing production workflow.
"""

from __future__ import annotations

import logging
from typing import Any

from workers.scoring_models import (
    BaseRiskScoringModel,
    ExperimentalRiskModel,
    WeightedRiskModel,
)

logger = logging.getLogger(__name__)


class ABTestingFramework:
    """
    Executes multiple risk scoring models independently
    and compares their outputs.
    """

    def __init__(
        self,
        experiment_id: str = "risk-scoring-v1",
        production_model: BaseRiskScoringModel | None = None,
        experimental_model: BaseRiskScoringModel | None = None,
    ) -> None:

        self.experiment_id = experiment_id
        self.production_model = production_model or WeightedRiskModel()
        self.experimental_model = experimental_model or ExperimentalRiskModel()

        # Stores one result per experiment/variant/session.
        self._results: list[dict[str, Any]] = []

    def run(
        self,
        session_id: str,
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute both models independently using the same input.
        """

        logger.info("Running A/B risk scoring for session %s", session_id)

        production_report = self.production_model.generate_report(
            session_id=session_id,
            video_result=video_result,
            audio_result=audio_result,
            evaluation_result=evaluation_result,
        )

        experimental_report = self.experimental_model.generate_report(
            session_id=session_id,
            video_result=video_result,
            audio_result=audio_result,
            evaluation_result=evaluation_result,
        )

        # Record the results for dashboard aggregation.
        self._record_result(
            variant=self.production_model.name,
            session_id=session_id,
            score=production_report["final_risk_score"],
        )

        self._record_result(
            variant=self.experimental_model.name,
            session_id=session_id,
            score=experimental_report["final_risk_score"],
        )

        comparison = self.compare_reports(
            production_report,
            experimental_report,
        )

        return {
            "production_model": production_report,
            "experimental_model": experimental_report,
            "comparison": comparison,
        }

    def _record_result(
        self,
        variant: str,
        session_id: str,
        score: float,
    ) -> None:
        """
        Record one scoring result for dashboard aggregation.
        """

        self._results.append(
            {
                "experiment_id": self.experiment_id,
                "variant": variant,
                "session_id": session_id,
                "score": float(score),
            }
        )

    def get_experiment_data(self) -> list[dict[str, Any]]:
        """
        Return aggregated A/B testing data.

        Results are grouped by experiment and variant.
        Each session is counted once per variant.
        """

        grouped: dict[tuple[str, str], dict[str, Any]] = {}

        for result in self._results:
            key = (
                result["experiment_id"],
                result["variant"],
            )

            if key not in grouped:
                grouped[key] = {
                    "experiment_id": result["experiment_id"],
                    "variant": result["variant"],
                    "sessions": set(),
                    "scores": [],
                }

            grouped[key]["sessions"].add(result["session_id"])
            grouped[key]["scores"].append(result["score"])

        response: list[dict[str, Any]] = []

        for data in grouped.values():
            scores = data["scores"]

            response.append(
                {
                    "experiment_id": data["experiment_id"],
                    "variant": data["variant"],
                    "sessions": len(data["sessions"]),
                    "avg_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
                }
            )

        return response

    @staticmethod
    def compare_reports(
        production: dict[str, Any],
        experimental: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Compare two model outputs.
        """

        score_difference = round(
            experimental["final_risk_score"] - production["final_risk_score"],
            3,
        )

        classification_changed = (
            production["risk_classification"] != experimental["risk_classification"]
        )

        return {
            "production_score": production["final_risk_score"],
            "experimental_score": experimental["final_risk_score"],
            "score_difference": score_difference,
            "production_classification": production["risk_classification"],
            "experimental_classification": experimental["risk_classification"],
            "classification_changed": classification_changed,
        }
