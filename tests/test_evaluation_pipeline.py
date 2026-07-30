"""
Tests for the evaluation pipeline's handling of malformed LLM JSON output.

Covers issue #114: LLM JSON parsing crashes Celery worker tasks due to
missing exception handling.
"""

from unittest.mock import patch

from workers import evaluation_pipeline


def test_evaluate_answer_quality_falls_back_on_invalid_json():
    """If the LLM returns invalid JSON, evaluate_answer_quality should not
    raise, and should fall back to the seeded stub instead of crashing
    the Celery task."""
    with (
        patch("workers.ai_client.HAS_OPENAI", True),
        patch("workers.ai_client.chat_completion", return_value="not valid json {"),
    ):
        result = evaluation_pipeline.evaluate_answer_quality("session-123")

    assert result is not None
    assert "overall_quality_score" in result


def test_evaluate_technical_accuracy_falls_back_on_invalid_json():
    with (
        patch("workers.ai_client.HAS_OPENAI", True),
        patch("workers.ai_client.chat_completion", return_value="{bad json"),
    ):
        result = evaluation_pipeline.evaluate_technical_accuracy("session-123")

    assert result is not None
    assert "accuracy_score" in result


def test_evaluate_communication_falls_back_on_invalid_json():
    with patch("workers.ai_client.chat_completion", return_value="not json at all"):
        result = evaluation_pipeline.evaluate_communication("session-123")

    assert result is not None
    assert "clarity_score" in result


def test_generate_feedback_falls_back_on_invalid_json():
    with patch("workers.ai_client.chat_completion", return_value="<<<invalid>>>"):
        result = evaluation_pipeline.generate_feedback("session-123")

    assert result is not None
    assert "recommendation" in result


def test_full_pipeline_does_not_crash_on_invalid_json():
    """End-to-end: the whole evaluate_answers() pipeline should complete
    and return a well-formed result even when every LLM call returns
    malformed JSON."""
    with (
        patch("workers.ai_client.HAS_OPENAI", True),
        patch("workers.ai_client.chat_completion", return_value="{not valid json"),
    ):
        result = evaluation_pipeline.evaluate_answers("session-123")

    assert result["session_id"] == "session-123"
    assert 0.0 <= result["risk_score"] <= 1.0
