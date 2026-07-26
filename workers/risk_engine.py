"""
Risk Scoring Engine
Combines signals from all pipelines to calculate final interview risk score

Responsibilities:
- Normalize signals from different pipelines
- Generate weighted risk score (for reporting)
- Classify interview risk using a decision tree
- Generate final interview risk report

All weights and thresholds are configurable via RISK_CONFIG, a single
source of truth for every numeric constant in the scoring pipeline.
"""

import logging
import os
import time
from threading import Lock
from typing import Any

from database.db import SessionLocal

logger = logging.getLogger(__name__)


FALLBACK_DEFAULTS = {
    "video_weight": 0.4,
    "audio_weight": 0.3,
    "evaluation_weight": 0.3,
    "low_risk_threshold": 0.3,
    "medium_risk_threshold": 0.6,
    "high_risk_threshold": 0.8,
    "video_multiple_persons": 0.35,
    "video_phone_detected": 0.25,
    "video_suspicious_head_movement": 0.20,
    "video_no_face_detected": 0.45,
    "audio_background_voices": 0.35,
    "audio_suspicious_pattern": 0.25,
    "audio_no_transcription": 0.40,
    "eval_low_quality": 0.30,
    "eval_low_accuracy": 0.40,
    "eval_poor_communication": 0.20,
}

ENV_MAPPING = {
    "video_weight": "RISK_VIDEO_WEIGHT",
    "audio_weight": "RISK_AUDIO_WEIGHT",
    "evaluation_weight": "RISK_EVALUATION_WEIGHT",
    "low_risk_threshold": "RISK_LOW_RISK_THRESHOLD",
    "medium_risk_threshold": "RISK_MEDIUM_RISK_THRESHOLD",
    "high_risk_threshold": "RISK_HIGH_RISK_THRESHOLD",
    "video_multiple_persons": "RISK_VIDEO_MULTIPLE_PERSONS",
    "video_phone_detected": "RISK_VIDEO_PHONE_DETECTED",
    "video_suspicious_head_movement": "RISK_VIDEO_SUSPICIOUS_HEAD",
    "video_no_face_detected": "RISK_VIDEO_NO_FACE",
    "audio_background_voices": "RISK_AUDIO_BACKGROUND_VOICES",
    "audio_suspicious_pattern": "RISK_AUDIO_SUSPICIOUS_PATTERN",
    "audio_no_transcription": "RISK_AUDIO_NO_TRANSCRIPTION",
    "eval_low_quality": "RISK_EVAL_LOW_QUALITY",
    "eval_low_accuracy": "RISK_EVAL_LOW_ACCURACY",
    "eval_poor_communication": "RISK_EVAL_POOR_COMMUNICATION",
}


class RiskConfigManager:
    """Manages loading configurations from database, env variables, and fallbacks."""

    _cache: dict[str, Any] = {}
    _last_fetched: float = 0.0
    _ttl: float = 10.0  # 10 seconds TTL
    _lock = Lock()

    @classmethod
    def set_ttl(cls, ttl: float) -> None:
        """Helper to adjust TTL during tests or runtime."""
        cls._ttl = ttl

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cache immediately (useful for tests)."""
        with cls._lock:
            cls._cache = {}
            cls._last_fetched = 0.0

    @classmethod
    def get_all_configs(cls) -> dict[str, Any]:
        with cls._lock:
            now = time.monotonic()
            if cls._cache and (now - cls._last_fetched < cls._ttl):
                return cls._cache

            db_configs = {}
            db_success = False
            db = None
            try:
                db = SessionLocal()
                from database.models import RiskConfiguration

                rows = db.query(RiskConfiguration).all()
                for r in rows:
                    db_configs[r.key] = r.value
                db_success = True
            except Exception as exc:
                logger.warning(
                    "Could not load risk configurations from database: %s. Falling back to environment/defaults.",
                    exc,
                )
            finally:
                if db:
                    db.close()

            resolved = {}
            for key, default_val in FALLBACK_DEFAULTS.items():
                if db_success and key in db_configs:
                    resolved[key] = db_configs[key]
                else:
                    env_name = ENV_MAPPING.get(key)
                    env_val = os.getenv(env_name) if env_name else None
                    if env_val is not None:
                        try:
                            resolved[key] = float(env_val)
                        except ValueError:
                            resolved[key] = default_val
                    else:
                        resolved[key] = default_val

            cls._cache = resolved
            cls._last_fetched = now
            return resolved

    @classmethod
    def get_value(cls, key: str, default: Any) -> Any:
        configs = cls.get_all_configs()
        return configs.get(key, default)


class DynamicConfigDict(dict):
    """A dictionary wrapper that dynamically resolves config keys from RiskConfigManager."""

    def __init__(self, key_mapping: dict[str, str], default_values: dict[str, float]):
        self.key_mapping = key_mapping
        self.default_values = default_values
        super().__init__({k: v for k, v in default_values.items()})

    def __getitem__(self, key):
        if key in self.key_mapping:
            db_key = self.key_mapping[key]
            default = self.default_values[key]
            return RiskConfigManager.get_value(db_key, default)
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in self.key_mapping:
            db_key = self.key_mapping[key]
            fallback = self.default_values.get(key, default)
            return RiskConfigManager.get_value(db_key, fallback)
        return super().get(key, default)

    def items(self):
        return [(k, self[k]) for k in self.key_mapping]

    def values(self):
        return [self[k] for k in self.key_mapping]

    def __repr__(self):
        resolved = {k: self[k] for k in self.key_mapping}
        return f"DynamicConfigDict({resolved!r})"


class RiskScoringEngineMeta(type):
    """Metaclass to expose dynamic, database-backed configuration variables as class-level properties."""

    @property
    def VIDEO_WEIGHT(cls) -> float:
        return RiskConfigManager.get_value("video_weight", 0.4)

    @property
    def AUDIO_WEIGHT(cls) -> float:
        return RiskConfigManager.get_value("audio_weight", 0.3)

    @property
    def EVALUATION_WEIGHT(cls) -> float:
        return RiskConfigManager.get_value("evaluation_weight", 0.3)

    @property
    def LOW_RISK_THRESHOLD(cls) -> float:
        return RiskConfigManager.get_value("low_risk_threshold", 0.3)

    @property
    def MEDIUM_RISK_THRESHOLD(cls) -> float:
        return RiskConfigManager.get_value("medium_risk_threshold", 0.6)

    @property
    def HIGH_RISK_THRESHOLD(cls) -> float:
        return RiskConfigManager.get_value("high_risk_threshold", 0.8)

    @property
    def VIDEO_FACTORS(cls) -> dict[str, float]:
        return DynamicConfigDict(
            {
                "multiple_persons": "video_multiple_persons",
                "phone_detected": "video_phone_detected",
                "suspicious_head_movement": "video_suspicious_head_movement",
                "no_face_detected": "video_no_face_detected",
            },
            {
                "multiple_persons": 0.35,
                "phone_detected": 0.25,
                "suspicious_head_movement": 0.20,
                "no_face_detected": 0.45,
            },
        )

    @property
    def AUDIO_FACTORS(cls) -> dict[str, float]:
        return DynamicConfigDict(
            {
                "background_voices": "audio_background_voices",
                "suspicious_pattern": "audio_suspicious_pattern",
                "no_transcription": "audio_no_transcription",
            },
            {
                "background_voices": 0.35,
                "suspicious_pattern": 0.25,
                "no_transcription": 0.40,
            },
        )

    @property
    def EVALUATION_FACTORS(cls) -> dict[str, float]:
        return DynamicConfigDict(
            {
                "low_quality_answers": "eval_low_quality",
                "low_accuracy": "eval_low_accuracy",
                "poor_communication": "eval_poor_communication",
            },
            {
                "low_quality_answers": 0.30,
                "low_accuracy": 0.40,
                "poor_communication": 0.20,
            },
        )


# For backwards compatibility, expose a dynamic RISK_CONFIG dictionary at the module level.
RISK_CONFIG = DynamicConfigDict({k: k for k in FALLBACK_DEFAULTS}, FALLBACK_DEFAULTS)


class RiskScoringEngine(metaclass=RiskScoringEngineMeta):
    """
    Calculates comprehensive risk scores from interview analysis results.
    All numeric constants read dynamically from database or fallback configuration.
    """

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
        final_risk = RiskScoringEngine.calculate_final_risk(
            video_risk,
            audio_risk,
            evaluation_risk,
        )
        risk_classification = RiskDecisionTree.classify(
            video_result,
            audio_result,
            evaluation_result,
        )
        weighted_classification = RiskScoringEngine.classify_risk(final_risk)
        logger.info(
            "Weighted=%s (%.2f), DecisionTree=%s",
            weighted_classification,
            final_risk,
            risk_classification,
        )
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


def seed_default_configs(db) -> None:
    """Seed default risk configurations if the table is empty."""
    import os

    from database.models import RiskConfiguration

    try:
        if db.query(RiskConfiguration).count() == 0:
            logger.info("Risk configurations table is empty. Seeding default values...")
            for key, default_val in FALLBACK_DEFAULTS.items():
                env_name = ENV_MAPPING.get(key)
                env_val = os.getenv(env_name) if env_name else None
                initial_val = default_val
                if env_val is not None:
                    try:
                        initial_val = float(env_val)
                    except ValueError:
                        pass

                db.add(
                    RiskConfiguration(
                        key=key,
                        value=initial_val,
                        description=f"Initial risk parameter for {key}",
                    )
                )
            db.commit()
            logger.info("Successfully seeded default risk configurations.")
    except Exception as exc:
        db.rollback()
        logger.error("Failed to seed default risk configurations: %s", exc)


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
