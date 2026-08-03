"""
Risk Scoring Engine
Combines signals from all pipelines to calculate final interview risk score

Responsibilities:
- Normalize signals from different pipelines
- Apply weighted scoring
- Generate final risk score (0-1 scale)
- Provide risk classification (static or adaptive thresholds & decision tree)
- Generate final interview risk report

All weights and thresholds are configurable via RISK_CONFIG, a single
source of truth for every numeric constant in the scoring pipeline.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from workers.adaptive_thresholds import (
    AdaptiveThresholdManager,
    RiskThresholds,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Single-source risk configuration — all weights & thresholds here.
# Override via environment variables (prefix RISK_), e.g.
#   RISK_VIDEO_WEIGHT=0.5 RISK_LOW_RISK_THRESHOLD=0.25
# ---------------------------------------------------------------------------

RISK_CONFIG: dict[str, Any] = {
    # Pipeline weights (must sum to 1.0)
    "video_weight": float(os.getenv("RISK_VIDEO_WEIGHT", "0.4")),
    "audio_weight": float(os.getenv("RISK_AUDIO_WEIGHT", "0.3")),
    "evaluation_weight": float(os.getenv("RISK_EVALUATION_WEIGHT", "0.3")),
    # Static Thresholds (Fallback)
    "low_risk_threshold": float(os.getenv("RISK_LOW_RISK_THRESHOLD", "0.3")),
    "medium_risk_threshold": float(os.getenv("RISK_MEDIUM_RISK_THRESHOLD", "0.6")),
    "high_risk_threshold": float(os.getenv("RISK_HIGH_RISK_THRESHOLD", "0.8")),
    # Adaptive Threshold Config
    "adaptive_thresholds_enabled": os.getenv("RISK_ADAPTIVE_THRESHOLDS_ENABLED", "true").lower()
    in ("true", "1", "yes"),
    "threshold_strategy": os.getenv("RISK_THRESHOLD_STRATEGY", "percentile"),
    "min_historical_samples": int(os.getenv("RISK_MIN_HISTORICAL_SAMPLES", "10")),
    "low_percentile": float(os.getenv("RISK_LOW_PERCENTILE", "0.60")),
    "medium_percentile": float(os.getenv("RISK_MEDIUM_PERCENTILE", "0.85")),
    "high_percentile": float(os.getenv("RISK_HIGH_PERCENTILE", "0.95")),
    "rolling_window_size": int(os.getenv("RISK_ROLLING_WINDOW_SIZE", "100")),
    "recalc_interval": int(os.getenv("RISK_RECALC_INTERVAL", "1")),
    # Video factors
    "video_multiple_persons": float(os.getenv("RISK_VIDEO_MULTIPLE_PERSONS", "0.35")),
    "video_phone_detected": float(os.getenv("RISK_VIDEO_PHONE_DETECTED", "0.25")),
    "video_suspicious_head_movement": float(os.getenv("RISK_VIDEO_SUSPICIOUS_HEAD", "0.20")),
    "video_no_face_detected": float(os.getenv("RISK_VIDEO_NO_FACE", "0.45")),
    # Audio factors
    "audio_background_voices": float(os.getenv("RISK_AUDIO_BACKGROUND_VOICES", "0.35")),
    "audio_suspicious_pattern": float(os.getenv("RISK_AUDIO_SUSPICIOUS_PATTERN", "0.25")),
    "audio_no_transcription": float(os.getenv("RISK_AUDIO_NO_TRANSCRIPTION", "0.40")),
    # Evaluation factors
    "eval_low_quality": float(os.getenv("RISK_EVAL_LOW_QUALITY", "0.30")),
    "eval_low_accuracy": float(os.getenv("RISK_EVAL_LOW_ACCURACY", "0.40")),
    "eval_poor_communication": float(os.getenv("RISK_EVAL_POOR_COMMUNICATION", "0.20")),
}

# Global adaptive threshold manager singleton
adaptive_threshold_manager = AdaptiveThresholdManager(
    strategy_name=str(RISK_CONFIG["threshold_strategy"]),
    min_samples=int(RISK_CONFIG["min_historical_samples"]),
    fixed_low=float(RISK_CONFIG["low_risk_threshold"]),
    fixed_medium=float(RISK_CONFIG["medium_risk_threshold"]),
    fixed_high=float(RISK_CONFIG["high_risk_threshold"]),
    low_percentile=float(RISK_CONFIG["low_percentile"]),
    medium_percentile=float(RISK_CONFIG["medium_percentile"]),
    high_percentile=float(RISK_CONFIG["high_percentile"]),
    rolling_window_size=int(RISK_CONFIG["rolling_window_size"]),
    recalc_interval=int(RISK_CONFIG["recalc_interval"]),
)


class RiskScoringEngine:
    """
    Calculates comprehensive risk scores from interview analysis results.
    All numeric constants read from RISK_CONFIG.
    """

    # Pipeline weights
    VIDEO_WEIGHT = float(RISK_CONFIG["video_weight"])
    AUDIO_WEIGHT = float(RISK_CONFIG["audio_weight"])
    EVALUATION_WEIGHT = float(RISK_CONFIG["evaluation_weight"])

    # Risk thresholds (static fallback values)
    LOW_RISK_THRESHOLD = float(RISK_CONFIG["low_risk_threshold"])
    MEDIUM_RISK_THRESHOLD = float(RISK_CONFIG["medium_risk_threshold"])
    HIGH_RISK_THRESHOLD = float(RISK_CONFIG["high_risk_threshold"])

    # Factor weights
    VIDEO_FACTORS = {
        "multiple_persons": float(RISK_CONFIG["video_multiple_persons"]),
        "phone_detected": float(RISK_CONFIG["video_phone_detected"]),
        "suspicious_head_movement": float(RISK_CONFIG["video_suspicious_head_movement"]),
        "no_face_detected": float(RISK_CONFIG["video_no_face_detected"]),
    }

    AUDIO_FACTORS = {
        "background_voices": float(RISK_CONFIG["audio_background_voices"]),
        "suspicious_pattern": float(RISK_CONFIG["audio_suspicious_pattern"]),
        "no_transcription": float(RISK_CONFIG["audio_no_transcription"]),
    }

    EVALUATION_FACTORS = {
        "low_quality_answers": float(RISK_CONFIG["eval_low_quality"]),
        "low_accuracy": float(RISK_CONFIG["eval_low_accuracy"]),
        "poor_communication": float(RISK_CONFIG["eval_poor_communication"]),
    }

    @staticmethod
    def calculate_video_risk(video_result: dict[str, Any]) -> float:
        """Calculate risk score from video analysis."""
        risk_score = 0.0

        if video_result.get("multiple_persons", {}).get("multiple_persons_detected"):
            risk_score += RiskScoringEngine.VIDEO_FACTORS["multiple_persons"]

        if video_result.get("phone_detected", {}).get("phone_detected"):
            risk_score += RiskScoringEngine.VIDEO_FACTORS["phone_detected"]

        if video_result.get("head_movement_suspicious", {}).get("suspicious_movement_detected"):
            risk_score += RiskScoringEngine.VIDEO_FACTORS["suspicious_head_movement"]

        if not video_result.get("face_detected", {}).get("faces_found"):
            risk_score += RiskScoringEngine.VIDEO_FACTORS["no_face_detected"]

        return min(risk_score, 1.0)

    @staticmethod
    def calculate_audio_risk(audio_result: dict[str, Any]) -> float:
        """Calculate risk score from audio analysis."""
        risk_score = 0.0

        if audio_result.get("background_voices", {}).get("background_voices_detected"):
            risk_score += RiskScoringEngine.AUDIO_FACTORS["background_voices"]

        if audio_result.get("suspicious_conversation", {}).get("suspicious_pattern_detected"):
            risk_score += RiskScoringEngine.AUDIO_FACTORS["suspicious_pattern"]

        if not audio_result.get("transcription", {}).get("text"):
            risk_score += RiskScoringEngine.AUDIO_FACTORS["no_transcription"]

        return min(risk_score, 1.0)

    @staticmethod
    def calculate_evaluation_risk(evaluation_result: dict[str, Any]) -> float:
        """Calculate risk score from answer evaluation."""
        risk_score = 0.0

        quality_score = evaluation_result.get("answer_quality_score", {}).get("overall_quality_score", 50)
        accuracy_score = evaluation_result.get("technical_accuracy", {}).get("accuracy_score", 50)
        clarity_score = evaluation_result.get("communication_clarity", {}).get("clarity_score", 50)

        if quality_score < 40:
            risk_score += RiskScoringEngine.EVALUATION_FACTORS["low_quality_answers"]
        if accuracy_score < 40:
            risk_score += RiskScoringEngine.EVALUATION_FACTORS["low_accuracy"]
        if clarity_score < 40:
            risk_score += RiskScoringEngine.EVALUATION_FACTORS["poor_communication"]

        return min(risk_score, 1.0)

    @staticmethod
    def calculate_final_risk(video_risk: float, audio_risk: float, evaluation_risk: float) -> float:
        """Calculate final combined risk score using weighted average."""
        final_risk = (
            RiskScoringEngine.VIDEO_WEIGHT * video_risk
            + RiskScoringEngine.AUDIO_WEIGHT * audio_risk
            + RiskScoringEngine.EVALUATION_WEIGHT * evaluation_risk
        )
        return round(min(max(final_risk, 0.0), 1.0), 3)

    @staticmethod
    def _apply_critical_rule_overrides(final_risk: float, risk_classification: str) -> float:
        """Apply rule-based overrides to the linear combined risk score."""
        if risk_classification == "CRITICAL":
            return max(final_risk, 0.95)
        if risk_classification == "HIGH":
            return max(final_risk, 0.8)
        if risk_classification == "MEDIUM":
            return max(final_risk, 0.6)
        return final_risk

    @staticmethod
    def calculate_confidence(
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
    ) -> float:
        """
        Calculate confidence based on completeness of available signals.
        Returns a value between 0.0 and 1.0.
        """
        total_signals = 3
        available_signals = 0

        if video_result:
            available_signals += 1
        if audio_result:
            available_signals += 1
        if evaluation_result:
            available_signals += 1

        confidence = available_signals / total_signals
        return round(confidence, 2)

    @staticmethod
    def classify_risk(
        risk_score: float,
        thresholds: RiskThresholds | dict[str, float] | None = None,
    ) -> str:
        """Classify risk level based on score using dynamic or static thresholds."""
        if thresholds is not None:
            if isinstance(thresholds, RiskThresholds):
                low, medium, high = thresholds.low, thresholds.medium, thresholds.high
            else:
                low = thresholds.get("low", RiskScoringEngine.LOW_RISK_THRESHOLD)
                medium = thresholds.get("medium", RiskScoringEngine.MEDIUM_RISK_THRESHOLD)
                high = thresholds.get("high", RiskScoringEngine.HIGH_RISK_THRESHOLD)
        elif RISK_CONFIG.get("adaptive_thresholds_enabled", True):
            active_t = adaptive_threshold_manager.get_current_thresholds()
            low, medium, high = active_t.low, active_t.medium, active_t.high
        else:
            low = RiskScoringEngine.LOW_RISK_THRESHOLD
            medium = RiskScoringEngine.MEDIUM_RISK_THRESHOLD
            high = RiskScoringEngine.HIGH_RISK_THRESHOLD

        if risk_score < low:
            return "LOW"
        if risk_score < medium:
            return "MEDIUM"
        if risk_score < high:
            return "HIGH"
        return "CRITICAL"

    @staticmethod
    def generate_risk_report(
        session_id: str,
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
        db_session: Any = None,
    ) -> dict[str, Any]:
        """Generate comprehensive risk report from all analysis results."""
        logger.info(f"Generating risk report for session {session_id}")

        video_risk = RiskScoringEngine.calculate_video_risk(video_result)
        audio_risk = RiskScoringEngine.calculate_audio_risk(audio_result)
        evaluation_risk = RiskScoringEngine.calculate_evaluation_risk(evaluation_result)
        final_risk = RiskScoringEngine.calculate_final_risk(
            video_risk,
            audio_risk,
            evaluation_risk,
        )
        dt_classification = RiskDecisionTree.classify(
            video_result,
            audio_result,
            evaluation_result,
        )
        final_risk = RiskScoringEngine._apply_critical_rule_overrides(final_risk, dt_classification)

        # Record score into historical store and update adaptive thresholds if enabled
        if RISK_CONFIG.get("adaptive_thresholds_enabled", True):
            current_thresholds = adaptive_threshold_manager.record_and_update(
                session_id=session_id,
                risk_score=final_risk,
                db_session=db_session,
            )
        else:
            current_thresholds = RiskThresholds(
                low=RiskScoringEngine.LOW_RISK_THRESHOLD,
                medium=RiskScoringEngine.MEDIUM_RISK_THRESHOLD,
                high=RiskScoringEngine.HIGH_RISK_THRESHOLD,
            )

        risk_classification = RiskScoringEngine.classify_risk(final_risk, thresholds=current_thresholds)
        confidence = RiskScoringEngine.calculate_confidence(
            video_result,
            audio_result,
            evaluation_result,
        )

        risk_factors = RiskScoringEngine._identify_risk_factors(
            video_result,
            audio_result,
            evaluation_result,
        )
        report = {
            "session_id": session_id,
            "final_risk_score": final_risk,
            "risk_classification": risk_classification,
            "confidence": confidence,
            "component_risks": {
                "video_risk": video_risk,
                "audio_risk": audio_risk,
                "evaluation_risk": evaluation_risk,
            },
            "risk_factors": risk_factors,
            "recommendation": RiskScoringEngine._generate_recommendation(risk_classification),
            "thresholds_used": current_thresholds.as_dict(),
        }

        logger.info(f"Risk report generated: {risk_classification} (score: {final_risk})")
        return report

    @staticmethod
    def _identify_risk_factors(
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
    ) -> list:
        """Identify specific risk factors from analysis results."""
        risk_factors = []

        if not video_result.get("face_detected", {}).get("faces_found"):
            risk_factors.append("Candidate face not detected")
        if video_result.get("multiple_persons", {}).get("multiple_persons_detected"):
            risk_factors.append("Multiple persons detected in frame")
        if video_result.get("phone_detected", {}).get("phone_detected"):
            risk_factors.append("Mobile phone detected")
        if video_result.get("head_movement_suspicious", {}).get("suspicious_movement_detected"):
            risk_factors.append("Suspicious head movement detected")

        if audio_result.get("background_voices", {}).get("background_voices_detected"):
            risk_factors.append("Background voices detected - possible external help")
        if audio_result.get("suspicious_conversation", {}).get("suspicious_pattern_detected"):
            risk_factors.append("Suspicious conversation pattern detected")
        if not audio_result.get("transcription", {}).get("text"):
            risk_factors.append("No speech detected during interview")

        quality_score = evaluation_result.get("answer_quality_score", {}).get("overall_quality_score", 50)
        accuracy_score = evaluation_result.get("technical_accuracy", {}).get("accuracy_score", 50)

        if quality_score < 40:
            risk_factors.append("Low answer quality detected")
        if accuracy_score < 40:
            risk_factors.append("Low technical accuracy detected")

        return risk_factors

    @staticmethod
    def _generate_recommendation(risk_classification: str) -> str:
        """Generate recommendation based on risk classification."""
        recommendations = {
            "LOW": "Candidate appears genuine. Proceed with hiring consideration.",
            "MEDIUM": "Monitor candidate responses. Further verification may be needed.",
            "HIGH": "Multiple concerning factors detected. Recommend interview review.",
            "CRITICAL": "Significant fraud indicators detected. Recommend rejection or investigation.",
        }
        return recommendations.get(risk_classification, "Review interview manually.")


class RiskDecisionTree:
    """
    Decision tree for interview risk classification.
    Determines the final interview risk using decision rules
    instead of weighted scoring.
    """

    @staticmethod
    def classify(
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
    ) -> str:

        # Multiple people detected
        if video_result.get("multiple_persons", {}).get("multiple_persons_detected"):
            return "CRITICAL"

        # Face not detected
        if not video_result.get("face_detected", {}).get("faces_found"):
            return "HIGH"

        # Phone detected
        if video_result.get("phone_detected", {}).get("phone_detected"):
            return "HIGH"

        # Suspicious head movement
        if video_result.get("head_movement_suspicious", {}).get("suspicious_movement_detected"):
            return "HIGH"

        # Background voices + suspicious conversation together
        if audio_result.get("background_voices", {}).get("background_voices_detected") and audio_result.get(
            "suspicious_conversation", {}
        ).get("suspicious_pattern_detected"):
            return "HIGH"

        # Background voices only
        if audio_result.get("background_voices", {}).get("background_voices_detected"):
            return "MEDIUM"

        # Suspicious conversation only
        if audio_result.get("suspicious_conversation", {}).get("suspicious_pattern_detected"):
            return "MEDIUM"

        # Poor answer quality
        quality = evaluation_result.get("answer_quality_score", {}).get("overall_quality_score", 50)

        if quality < 40:
            return "MEDIUM"

        # Poor technical accuracy
        accuracy = evaluation_result.get("technical_accuracy", {}).get("accuracy_score", 50)

        if accuracy < 40:
            return "MEDIUM"

        # Poor communication
        clarity = evaluation_result.get("communication_clarity", {}).get("clarity_score", 50)

        if clarity < 40:
            return "MEDIUM"

        return "LOW"
