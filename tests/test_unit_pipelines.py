"""Unit tests for the AI pipeline stubs.

These verify the pluggable contracts still hold: each pipeline returns the
shape the RiskScoringEngine consumes, and the seeded deterministic outputs
let end-to-end risk classification thresholds fire.
"""
from unittest.mock import patch
from workers.audio_pipeline import (
    calculate_audio_risk_score,
    detect_background_voices,
    detect_suspicious_conversation,
    run_audio_analysis,
    transcribe_speech,
)
from workers.evaluation_pipeline import (
    evaluate_answer_quality,
    evaluate_answers,
    evaluate_communication,
    evaluate_technical_accuracy,
    generate_feedback,
)
from workers.video_pipeline import (
    calculate_video_risk_score,
    detect_face,
    detect_mobile_phone,
    detect_multiple_persons,
    detect_suspicious_head_movement,
    run_video_analysis,
)


def test_video_pipeline_runs_end_to_end():
    out = run_video_analysis("abc123")
    for key in (
        "session_id",
        "face_detected",
        "head_movement_suspicious",
        "phone_detected",
        "multiple_persons",
        "risk_score",
    ):
        assert key in out
    assert 0.0 <= out["risk_score"] <= 1.0


def test_video_pipeline_is_deterministic_per_session():
    a = run_video_analysis("session-X")
    b = run_video_analysis("session-X")
    assert a == b


def test_audio_pipeline_returns_expected_shape():
    out = run_audio_analysis("s-audio")
    for key in (
        "session_id",
        "transcription",
        "background_voices",
        "suspicious_conversation",
        "risk_score",
    ):
        assert key in out
    assert 0.0 <= out["risk_score"] <= 1.0


def test_audio_pipeline_variation_across_sessions():
    samples = {run_audio_analysis(f"sess-{i}")["risk_score"] for i in range(20)}
    assert len(samples) > 1, "Expected deterministic-but-varied outputs"


def test_evaluation_pipeline_returns_inverse_risk():
    out = evaluate_answers("s-eval")
    assert 0.0 <= out["risk_score"] <= 1.0
    assert "answer_quality_score" in out
    assert "feedback" in out


def test_video_risk_accumulates_signals():
    high_risk_input = {
        "face_detected": {"faces_found": False},
        "head_movement_suspicious": {"suspicious_movement_detected": True},
        "phone_detected": {"phone_detected": True},
        "multiple_persons": {"multiple_persons_detected": True},
    }
    score = calculate_video_risk_score(high_risk_input)
    assert score >= 0.9  # multiple + phone + movement + no_face -> clamped at 1.0


def test_audio_risk_handles_empty_transcription():
    out = {
        "transcription": {"text": ""},
        "background_voices": {"background_voices_detected": False},
        "suspicious_conversation": {"suspicious_pattern_detected": False},
    }
    assert calculate_audio_risk_score(out) >= 0.3


def test_helper_functions_return_dicts():
    for fn, sid in [
        (detect_face, "x"),
        (detect_suspicious_head_movement, "x"),
        (detect_mobile_phone, "x"),
        (detect_multiple_persons, "x"),
        (transcribe_speech, "x"),
        (detect_background_voices, "x"),
        (detect_suspicious_conversation, "x"),
        (evaluate_answer_quality, "x"),
        (evaluate_technical_accuracy, "x"),
        (evaluate_communication, "x"),
        (generate_feedback, "x"),
    ]:
        assert isinstance(fn(sid), dict)

@patch("workers.evaluation_pipeline._llm_evaluate_answer_quality")
def test_answer_quality_contains_llm_usage(mock_quality):
    mock_quality.return_value = {
        "overall_quality_score": 95,
        "relevance": 1.0,
        "completeness": 1.0,
        "clarity": 1.0,
        "feedback": "Excellent",
        "provider": "openai",
        "llm_usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }

    result = evaluate_answer_quality("session-1")

    assert "llm_usage" in result
    assert result["llm_usage"]["total_tokens"] == 30

    
@patch("workers.evaluation_pipeline.evaluate_answer_quality")
@patch("workers.evaluation_pipeline.evaluate_communication")
@patch("workers.evaluation_pipeline.generate_feedback")
def test_evaluate_answers_collects_llm_usage(
    mock_feedback,
    mock_communication,
    mock_quality,
):
    mock_quality.return_value = {
        "overall_quality_score": 90,
        "llm_usage": {
            "total_tokens": 20,
        },
    }

    mock_communication.return_value = {
        "clarity_score": 80,
        "llm_usage": {
            "total_tokens": 15,
        },
    }

    mock_feedback.return_value = {
        "recommendation": "progress",
        "llm_usage": {
            "total_tokens": 25,
        },
    }

    result = evaluate_answers("session-1")

    assert "llm_usage" in result
    assert result["llm_usage"]["quality"]["total_tokens"] == 20
    assert result["llm_usage"]["communication"]["total_tokens"] == 15
    assert result["llm_usage"]["feedback"]["total_tokens"] == 25

        
