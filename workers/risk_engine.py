"""
Risk Scoring Engine
Combines signals from all pipelines to calculate final interview risk score

Responsibilities:
- Normalize signals from different pipelines
- Apply weighted scoring
- Generate final risk score (0-1 scale)
- Provide risk classification

All weights and thresholds are configurable via RISK_CONFIG, a single
source of truth for every numeric constant in the scoring pipeline.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Single-source risk configuration — all weights & thresholds here.
# Override via environment variables (prefix RISK_), e.g.
#   RISK_VIDEO_WEIGHT=0.5 RISK_LOW_RISK_THRESHOLD=0.25
# ---------------------------------------------------------------------------

RISK_CONFIG: dict[str, float] = {
    # Pipeline weights (must sum to 1.0)
    "video_weight": float(os.getenv("RISK_VIDEO_WEIGHT", "0.4")),
    "audio_weight": float(os.getenv("RISK_AUDIO_WEIGHT", "0.3")),
    "evaluation_weight": float(os.getenv("RISK_EVALUATION_WEIGHT", "0.3")),
    # Thresholds
    "low_risk_threshold": float(os.getenv("RISK_LOW_RISK_THRESHOLD", "0.3")),
    "medium_risk_threshold": float(os.getenv("RISK_MEDIUM_RISK_THRESHOLD", "0.6")),
    "high_risk_threshold": float(os.getenv("RISK_HIGH_RISK_THRESHOLD", "0.8")),
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


class RiskScoringEngine:
    """
    Calculates comprehensive risk scores from interview analysis results.
    All numeric constants read from RISK_CONFIG.
    """

    # Pipeline weights
    VIDEO_WEIGHT = RISK_CONFIG["video_weight"]
    AUDIO_WEIGHT = RISK_CONFIG["audio_weight"]
    EVALUATION_WEIGHT = RISK_CONFIG["evaluation_weight"]

    # Risk thresholds
    LOW_RISK_THRESHOLD = RISK_CONFIG["low_risk_threshold"]
    MEDIUM_RISK_THRESHOLD = RISK_CONFIG["medium_risk_threshold"]
    HIGH_RISK_THRESHOLD = RISK_CONFIG["high_risk_threshold"]

    # Factor weights
    VIDEO_FACTORS = {
        "multiple_persons": RISK_CONFIG["video_multiple_persons"],
        "phone_detected": RISK_CONFIG["video_phone_detected"],
        "suspicious_head_movement": RISK_CONFIG["video_suspicious_head_movement"],
        "no_face_detected": RISK_CONFIG["video_no_face_detected"],
    }

    AUDIO_FACTORS = {
        "background_voices": RISK_CONFIG["audio_background_voices"],
        "suspicious_pattern": RISK_CONFIG["audio_suspicious_pattern"],
        "no_transcription": RISK_CONFIG["audio_no_transcription"],
    }

    EVALUATION_FACTORS = {
        "low_quality_answers": RISK_CONFIG["eval_low_quality"],
        "low_accuracy": RISK_CONFIG["eval_low_accuracy"],
        "poor_communication": RISK_CONFIG["eval_poor_communication"],
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
    def classify_risk(risk_score: float) -> str:
        """Classify risk level based on score."""
        if risk_score < RiskScoringEngine.LOW_RISK_THRESHOLD:
            return "LOW"
        if risk_score < RiskScoringEngine.MEDIUM_RISK_THRESHOLD:
            return "MEDIUM"
        if risk_score < RiskScoringEngine.HIGH_RISK_THRESHOLD:
            return "HIGH"
        return "CRITICAL"

    @staticmethod
    def generate_risk_report(
        session_id: str,
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate comprehensive risk report from all analysis results."""
        logger.info(f"Generating risk report for session {session_id}")

        video_risk = RiskScoringEngine.calculate_video_risk(video_result)
        audio_risk = RiskScoringEngine.calculate_audio_risk(audio_result)
        evaluation_risk = RiskScoringEngine.calculate_evaluation_risk(evaluation_result)
        final_risk = RiskScoringEngine.calculate_final_risk(video_risk, audio_risk, evaluation_risk)
        risk_classification = RiskScoringEngine.classify_risk(final_risk)
        risk_factors = RiskScoringEngine._identify_risk_factors(video_result, audio_result, evaluation_result)

        report = {
            "session_id": session_id,
            "final_risk_score": final_risk,
            "risk_classification": risk_classification,
            "component_risks": {
                "video_risk": video_risk,
                "audio_risk": audio_risk,
                "evaluation_risk": evaluation_risk,
            },
            "risk_factors": risk_factors,
            "recommendation": RiskScoringEngine._generate_recommendation(risk_classification),
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
