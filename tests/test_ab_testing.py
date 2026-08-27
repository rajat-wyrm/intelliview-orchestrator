"""
Unit tests for A/B Risk Scoring Framework
"""

from workers.ab_testing_framework import ABTestingFramework
from workers.scoring_models import (
    ExperimentalRiskModel,
    WeightedRiskModel,
)


def sample_video():
    return {
        "multiple_persons": {
            "multiple_persons_detected": False,
        },
        "phone_detected": {
            "phone_detected": False,
        },
        "head_movement_suspicious": {
            "suspicious_movement_detected": False,
        },
        "face_detected": {
            "faces_found": True,
        },
    }


def sample_audio():
    return {
        "background_voices": {
            "background_voices_detected": False,
        },
        "suspicious_conversation": {
            "suspicious_pattern_detected": False,
        },
        "transcription": {
            "text": "Hello",
        },
    }


def sample_evaluation():
    return {
        "answer_quality_score": {
            "overall_quality_score": 85,
        },
        "technical_accuracy": {
            "accuracy_score": 90,
        },
        "communication_clarity": {
            "clarity_score": 88,
        },
    }


def test_weighted_model_runs():

    model = WeightedRiskModel()

    report = model.generate_report(
        "session-1",
        sample_video(),
        sample_audio(),
        sample_evaluation(),
    )

    assert report["model"] == "weighted_model"
    assert "final_risk_score" in report
    assert "risk_classification" in report


def test_experimental_model_runs():

    model = ExperimentalRiskModel()

    report = model.generate_report(
        "session-1",
        sample_video(),
        sample_audio(),
        sample_evaluation(),
    )

    assert report["model"] == "experimental_model"
    assert "final_risk_score" in report
    assert "risk_classification" in report


def test_ab_framework_runs_both_models():

    framework = ABTestingFramework()

    results = framework.run(
        "session-1",
        sample_video(),
        sample_audio(),
        sample_evaluation(),
    )

    assert "production_model" in results
    assert "experimental_model" in results
    assert "comparison" in results


def test_same_session_used():

    framework = ABTestingFramework()

    results = framework.run(
        "session-abc",
        sample_video(),
        sample_audio(),
        sample_evaluation(),
    )

    assert (
        results["production_model"]["session_id"]
        == results["experimental_model"]["session_id"]
    )


def test_comparison_contains_difference():

    framework = ABTestingFramework()

    comparison = framework.run(
        "session-x",
        sample_video(),
        sample_audio(),
        sample_evaluation(),
    )["comparison"]

    assert "score_difference" in comparison
    assert "classification_changed" in comparison


def test_production_model_not_modified():

    framework = ABTestingFramework()

    production = framework.run(
        "session-y",
        sample_video(),
        sample_audio(),
        sample_evaluation(),
    )["production_model"]

    assert production["model"] == "weighted_model"


def test_framework_is_modular():

    framework = ABTestingFramework()

    assert framework.production_model is not None
    assert framework.experimental_model is not None


def test_get_experiment_data_with_no_results():

    framework = ABTestingFramework(
        experiment_id="test-experiment",
    )

    result = framework.get_experiment_data()

    assert result == []


def test_get_experiment_data_with_multiple_variants():

    framework = ABTestingFramework(
        experiment_id="test-experiment",
    )

    framework._record_result(
        variant="weighted_model",
        session_id="session-1",
        score=0.4,
    )

    framework._record_result(
        variant="weighted_model",
        session_id="session-2",
        score=0.6,
    )

    framework._record_result(
        variant="experimental_model",
        session_id="session-1",
        score=0.3,
    )

    framework._record_result(
        variant="experimental_model",
        session_id="session-2",
        score=0.5,
    )

    result = framework.get_experiment_data()

    assert len(result) == 2

    weighted = next(item for item in result if item["variant"] == "weighted_model")

    experimental = next(
        item for item in result if item["variant"] == "experimental_model"
    )

    assert weighted == {
        "experiment_id": "test-experiment",
        "variant": "weighted_model",
        "sessions": 2,
        "avg_score": 0.5,
    }

    assert experimental == {
        "experiment_id": "test-experiment",
        "variant": "experimental_model",
        "sessions": 2,
        "avg_score": 0.4,
    }


def test_session_is_counted_once_per_variant():

    framework = ABTestingFramework(
        experiment_id="test-experiment",
    )

    framework._record_result(
        variant="weighted_model",
        session_id="session-1",
        score=0.4,
    )

    framework._record_result(
        variant="weighted_model",
        session_id="session-1",
        score=0.6,
    )

    result = framework.get_experiment_data()

    assert result == [
        {
            "experiment_id": "test-experiment",
            "variant": "weighted_model",
            "sessions": 1,
            "avg_score": 0.5,
        }
    ]
