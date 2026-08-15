"""
Unit tests for AI Interview Coaching Generation
"""

from unittest.mock import patch

from workers.coaching_ai import generate_interview_coaching


def test_valid_coaching_input():
    """Test coaching generation with valid interview performance input."""
    mock_interview_data = {
        "session_id": "sess_123",
        "questions_answered": 3,
        "details": [{"question": "What is dependency injection?", "score": 85, "feedback": "Good clarity"}],
    }

    mock_gemini_json = (
        '{"strengths": ["Clear technical articulation"], '
        '"weaknesses": ["Needs more system design examples"], '
        '"communication_feedback": "Good pace and tone", '
        '"topics_requiring_improvement": ["Distributed Systems"], '
        '"recommendations": ["Practice trade-off analysis"], '
        '"suggestions_for_future_answers": ["Structure answers using STAR method"], '
        '"sample_improved_answers": ["Focus on scalability patterns"]}'
    )

    with (
        patch("workers.ai_client.HAS_GEMINI", True),
        patch("workers.ai_client.gemini_generate", return_value=(mock_gemini_json, {"total_tokens": 100})),
    ):
        result = generate_interview_coaching(mock_interview_data)

        assert result["status"] == "success"
        assert len(result["strengths"]) > 0
        assert "Clear technical articulation" in result["strengths"]
        assert len(result["recommendations"]) > 0


def test_missing_evaluation_data():
    """Test handling of missing or empty interview evaluation data."""
    result = generate_interview_coaching(None)
    assert result["status"] == "fallback"
    assert "Missing" in result["error_reason"]


def test_llm_api_failure():
    """Test graceful handling when the LLM API fails or is unavailable."""
    mock_interview_data = {"session_id": "sess_456"}

    with patch("workers.ai_client.HAS_GEMINI", False):
        result = generate_interview_coaching(mock_interview_data)
        assert result["status"] == "fallback"


def test_unexpected_ai_output():
    """Test handling when Gemini returns invalid non-JSON text."""
    mock_interview_data = {"session_id": "sess_789"}
    malformed_text = "This is not valid JSON output from the model."

    with (
        patch("workers.ai_client.HAS_GEMINI", True),
        patch("workers.ai_client.gemini_generate", return_value=(malformed_text, {"total_tokens": 50})),
    ):
        result = generate_interview_coaching(mock_interview_data)
        assert result["status"] == "partial_success_invalid_json"
        assert result["raw_ai_output"] == malformed_text
