"""
Unit tests that don't require a running stack.

These exercise pure-logic modules that are easy to test in isolation.
"""

import math

from workers.risk_engine import RiskScoringEngine


def test_classify_risk_boundaries():
    assert RiskScoringEngine.classify_risk(0.0) == "LOW"
    assert RiskScoringEngine.classify_risk(0.29) == "LOW"
    assert RiskScoringEngine.classify_risk(0.3) == "MEDIUM"
    assert RiskScoringEngine.classify_risk(0.59) == "MEDIUM"
    assert RiskScoringEngine.classify_risk(0.6) == "HIGH"
    assert RiskScoringEngine.classify_risk(0.79) == "HIGH"
    assert RiskScoringEngine.classify_risk(0.8) == "CRITICAL"
    assert RiskScoringEngine.classify_risk(1.0) == "CRITICAL"


def test_calculate_final_risk_weighted_and_clamped():
    # 0.4*1.0 + 0.3*1.0 + 0.3*1.0 = 1.0
    assert RiskScoringEngine.calculate_final_risk(1.0, 1.0, 1.0) == 1.0
    # 0.4*0 + 0.3*0 + 0.3*0 = 0
    assert RiskScoringEngine.calculate_final_risk(0.0, 0.0, 0.0) == 0.0
    # Mid-point
    score = RiskScoringEngine.calculate_final_risk(0.5, 0.5, 0.5)
    assert math.isclose(score, 0.5, rel_tol=1e-9)


def test_video_risk_no_face_is_high():
    risk = RiskScoringEngine.calculate_video_risk({"face_detected": {"faces_found": False}})
    assert risk >= 0.4


def test_video_risk_clean_signals_is_zero():
    risk = RiskScoringEngine.calculate_video_risk(
        {
            "face_detected": {"faces_found": True},
            "multiple_persons": {"multiple_persons_detected": False},
            "phone_detected": {"phone_detected": False},
            "head_movement_suspicious": {"suspicious_movement_detected": False},
        }
    )
    assert risk == 0.0


def test_audio_risk_background_voices_increases_risk():
    base = RiskScoringEngine.calculate_audio_risk({"transcription": {"text": "ok"}})
    with_bg = RiskScoringEngine.calculate_audio_risk(
        {
            "transcription": {"text": "ok"},
            "background_voices": {"background_voices_detected": True},
        }
    )
    assert with_bg > base


def test_evaluation_risk_low_quality_increases_risk():
    base = RiskScoringEngine.calculate_evaluation_risk(
        {
            "answer_quality_score": {"overall_quality_score": 80},
            "technical_accuracy": {"accuracy_score": 80},
            "communication_clarity": {"clarity_score": 80},
        }
    )
    low = RiskScoringEngine.calculate_evaluation_risk(
        {
            "answer_quality_score": {"overall_quality_score": 20},
            "technical_accuracy": {"accuracy_score": 80},
            "communication_clarity": {"clarity_score": 80},
        }
    )
    assert low > base


def test_generate_risk_report_shape():
    report = RiskScoringEngine.generate_risk_report(
        "s1",
        {"face_detected": {"faces_found": True}},
        {"transcription": {"text": "hello"}},
        {
            "answer_quality_score": {"overall_quality_score": 70},
            "technical_accuracy": {"accuracy_score": 70},
            "communication_clarity": {"clarity_score": 70},
        },
    )
    assert report["session_id"] == "s1"
    assert "final_risk_score" in report
    assert report["risk_classification"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert "component_risks" in report
    assert "risk_factors" in report
    assert "explanation" in report
    assert "recommendation" in report


def test_generate_explanation_low():
    explanation = RiskScoringEngine._generate_explanation(
        "LOW",
        [],
    )
    assert "Low risk" in explanation


def test_generate_explanation_medium():
    explanation = RiskScoringEngine._generate_explanation(
        "MEDIUM",
        ["Background voices detected"],
    )
    assert "Medium risk" in explanation
    assert "Background voices detected" in explanation


def test_generate_explanation_high():
    explanation = RiskScoringEngine._generate_explanation(
        "HIGH",
        ["Phone detected"],
    )
    assert "High risk" in explanation
    assert "Phone detected" in explanation


def test_generate_explanation_critical():
    explanation = RiskScoringEngine._generate_explanation(
        "CRITICAL",
        ["Multiple persons detected"],
    )
    assert "Critical risk" in explanation
    assert "Multiple persons detected" in explanation
