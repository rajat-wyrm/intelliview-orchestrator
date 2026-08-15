"""
AI Interview Coaching Generation Module
Uses Gemini to generate personalized candidate coaching based on interview evaluation data.
"""

import json
import logging
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    from workers.prompts import COACHING_GENERATION_PROMPT
except ImportError:
    COACHING_GENERATION_PROMPT = (
        "You are an expert AI interview coach. Analyze candidate performance data "
        "and return a JSON object with keys: strengths, weaknesses, communication_feedback, "
        "topics_requiring_improvement, recommendations, suggestions_for_future_answers, sample_improved_answers."
    )


def generate_interview_coaching(interview_data: Any | None) -> dict[str, Any]:
    """
    Generate personalized interview coaching using Gemini.
    Handles missing or flexible incoming formats defensively using .get().
    """
    # Defensive handling if interview_data is missing, empty, or not a dict
    if not interview_data:
        logger.warning("Coaching generation received empty interview data.")
        return _get_fallback_coaching("Missing or incomplete interview evaluation data.")

    # Normalize incoming data if passed as a string or list unexpectedly
    if isinstance(interview_data, str):
        try:
            interview_data = json.loads(interview_data)
        except Exception:
            interview_data = {"raw_text": interview_data}

    if not isinstance(interview_data, dict):
        interview_data = {"data": interview_data}

    try:
        from workers.ai_client import HAS_GEMINI, gemini_generate

        if not HAS_GEMINI:
            logger.warning("Gemini client is unavailable (Check GEMINI_API_KEY in .env).")
            return _get_fallback_coaching("AI service unavailable or API key missing.")

        # Safely extract fields using .get() so it never throws a KeyError
        session_id = interview_data.get("session_id", "unknown_session")
        score = interview_data.get("total_score", interview_data.get("score", "N/A"))
        details = interview_data.get("details", interview_data.get("evaluations", interview_data))

        # Construct payload message securely for Gemini
        payload_summary = {"session_id": session_id, "overall_score": score, "performance_details": details}

        user_payload = json.dumps(payload_summary, indent=2, default=str)
        full_prompt = f"{COACHING_GENERATION_PROMPT}\n\nCandidate Performance Data:\n{user_payload}"

        # Call Gemini generation API
        response_text, usage = gemini_generate(full_prompt, temperature=0.4, max_output_tokens=1024)

        if not response_text:
            logger.warning("Gemini returned empty response for coaching generation.")
            return _get_fallback_coaching("AI generation failed to return text.")

        # 2. Handle unexpected AI output or invalid JSON parsing safely
        try:
            parsed_output = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse Gemini coaching response as JSON: %s", response_text)
            return {
                "strengths": ["Completed interview session."],
                "weaknesses": ["Review detailed report feedback."],
                "communication_feedback": "Check speech and clarity metrics in your report.",
                "topics_requiring_improvement": [],
                "recommendations": ["Practice structuring responses clearly."],
                "suggestions_for_future_answers": [],
                "sample_improved_answers": [],
                "raw_ai_output": response_text,
                "status": "partial_success_invalid_json",
            }

        # Structure final successful response matching Manohar's expected schema
        return {
            "strengths": parsed_output.get("strengths", ["Good participation"]),
            "weaknesses": parsed_output.get("weaknesses", ["Area for refinement identified"]),
            "communication_feedback": parsed_output.get(
                "communication_feedback", "Clear communication observed"
            ),
            "topics_requiring_improvement": parsed_output.get("topics_requiring_improvement", []),
            "recommendations": parsed_output.get("recommendations", ["Continue practicing technical depth"]),
            "suggestions_for_future_answers": parsed_output.get("suggestions_for_future_answers", []),
            "sample_improved_answers": parsed_output.get("sample_improved_answers", []),
            "usage": usage,
            "status": "success",
        }

    except Exception as exc:
        logger.error("Unexpected error during AI coaching generation: %s", exc)
        return _get_fallback_coaching(f"Error occurred: {exc!s}")


def _get_fallback_coaching(reason: str) -> dict[str, Any]:
    """Provide a deterministic fallback structure so the system never crashes."""
    return {
        "strengths": ["Interview submitted successfully."],
        "weaknesses": ["Coaching data currently unavailable."],
        "communication_feedback": "Please refer to your individual question feedback scores.",
        "topics_requiring_improvement": [],
        "recommendations": ["Review evaluation reports manually."],
        "suggestions_for_future_answers": [],
        "sample_improved_answers": [],
        "error_reason": reason,
        "status": "fallback",
    }
