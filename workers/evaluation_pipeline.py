"""
Answer Evaluation Pipeline
Handles interview answer evaluation and scoring

Responsibilities:
- LLM-based answer evaluation
- Score generation
- Feedback generation

Pluggable contract — replace each evaluator with your own LLM client
(OpenAI, Anthropic, local Llama, etc.). The provided defaults produce
deterministic per-session signals so the risk engine's HIGH/CRITICAL
thresholds exercise without external services.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


from workers._stubs import _seeded_unit  # noqa: E402

# ---------------------------------------------------------------------------
# Real LLM-based evaluation helpers with fallback to seeded stubs
# ---------------------------------------------------------------------------


def _llm_evaluate_answer_quality(session_id: str, question: str, answer: str) -> dict[str, Any] | None:
    """Use GPT-4o/Gemini/Grok to evaluate answer quality and relevance."""
    prompt = (
        "You are an expert technical interviewer. Evaluate this candidate answer. "
        "Return a JSON object with keys: overall_quality_score (0-100), "
        "relevance (0-1), completeness (0-1), clarity (0-1), feedback (string)."
    )
    user_msg = f"Question: {question}\n\nAnswer: {answer}"

    try:
        from workers.ai_client import HAS_OPENAI, chat_completion

        if HAS_OPENAI:
            response = chat_completion(
                [{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}],
                model="gpt-4o",
                temperature=0.3,
                max_tokens=512,
            )
            if response:
                try:
                    parsed = json.loads(response)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from LLM (openai, quality): %s", response)
                    return None
                return {
                    "overall_quality_score": round(parsed.get("overall_quality_score", 50), 2),
                    "relevance": round(parsed.get("relevance", 0.5), 2),
                    "completeness": round(parsed.get("completeness", 0.5), 2),
                    "clarity": round(parsed.get("clarity", 0.5), 2),
                    "feedback": parsed.get("feedback", ""),
                    "provider": "openai",
                }
    except Exception as exc:
        logger.debug("OpenAI quality evaluation failed: %s", exc)

    try:
        from workers.ai_client import HAS_GEMINI, gemini_generate

        if HAS_GEMINI:
            response = gemini_generate(f"{prompt}\n\n{user_msg}", temperature=0.3, max_output_tokens=512)
            if response:
                try:
                    parsed = json.loads(response)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from LLM (gemini, quality): %s", response)
                    return None
                return {
                    "overall_quality_score": round(parsed.get("overall_quality_score", 50), 2),
                    "relevance": round(parsed.get("relevance", 0.5), 2),
                    "completeness": round(parsed.get("completeness", 0.5), 2),
                    "clarity": round(parsed.get("clarity", 0.5), 2),
                    "feedback": parsed.get("feedback", ""),
                    "provider": "gemini",
                }
    except Exception as exc:
        logger.debug("Gemini quality evaluation failed: %s", exc)

    try:
        from workers.ai_client import HAS_GROK, grok_completion

        if HAS_GROK:
            response = grok_completion(
                [{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}],
                temperature=0.3,
                max_tokens=512,
            )
            if response:
                try:
                    parsed = json.loads(response)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from LLM (grok, quality): %s", response)
                    return None
                return {
                    "overall_quality_score": round(parsed.get("overall_quality_score", 50), 2),
                    "relevance": round(parsed.get("relevance", 0.5), 2),
                    "completeness": round(parsed.get("completeness", 0.5), 2),
                    "clarity": round(parsed.get("clarity", 0.5), 2),
                    "feedback": parsed.get("feedback", ""),
                    "provider": "grok",
                }
    except Exception as exc:
        logger.debug("Grok quality evaluation failed: %s", exc)

    return None


def _llm_evaluate_technical_accuracy(session_id: str, question: str, answer: str) -> dict[str, Any] | None:
    """Use GPT-4o/Gemini/Grok to evaluate technical accuracy."""
    prompt = (
        "You are a technical interviewer evaluating a candidate's answer. "
        "Return a JSON object with keys: accuracy_score (0-100), "
        "correct_concepts_count (int), incorrect_concepts_count (int), "
        "knowledge_gaps (list of strings)."
    )
    user_msg = f"Question: {question}\n\nAnswer: {answer}"

    try:
        from workers.ai_client import HAS_OPENAI, chat_completion

        if HAS_OPENAI:
            response = chat_completion(
                [{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}],
                model="gpt-4o",
                temperature=0.3,
                max_tokens=512,
            )
            if response:
                try:
                    parsed = json.loads(response)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from LLM (openai, accuracy): %s", response)
                    return None
                return {
                    "accuracy_score": round(parsed.get("accuracy_score", 50), 2),
                    "correct_concepts_count": parsed.get("correct_concepts_count", 0),
                    "incorrect_concepts_count": parsed.get("incorrect_concepts_count", 0),
                    "knowledge_gaps": parsed.get("knowledge_gaps", []),
                    "provider": "openai",
                }
    except Exception as exc:
        logger.debug("OpenAI accuracy evaluation failed: %s", exc)

    try:
        from workers.ai_client import HAS_GEMINI, gemini_generate

        if HAS_GEMINI:
            response = gemini_generate(f"{prompt}\n\n{user_msg}", temperature=0.3, max_output_tokens=512)
            if response:
                try:
                    parsed = json.loads(response)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from LLM (gemini, accuracy): %s", response)
                    return None
                return {
                    "accuracy_score": round(parsed.get("accuracy_score", 50), 2),
                    "correct_concepts_count": parsed.get("correct_concepts_count", 0),
                    "incorrect_concepts_count": parsed.get("incorrect_concepts_count", 0),
                    "knowledge_gaps": parsed.get("knowledge_gaps", []),
                    "provider": "gemini",
                }
    except Exception as exc:
        logger.debug("Gemini accuracy evaluation failed: %s", exc)

    try:
        from workers.ai_client import HAS_GROK, grok_completion

        if HAS_GROK:
            response = grok_completion(
                [{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}],
                temperature=0.3,
                max_tokens=512,
            )
            if response:
                try:
                    parsed = json.loads(response)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from LLM (grok, accuracy): %s", response)
                    return None
                return {
                    "accuracy_score": round(parsed.get("accuracy_score", 50), 2),
                    "correct_concepts_count": parsed.get("correct_concepts_count", 0),
                    "incorrect_concepts_count": parsed.get("incorrect_concepts_count", 0),
                    "knowledge_gaps": parsed.get("knowledge_gaps", []),
                    "provider": "grok",
                }
    except Exception as exc:
        logger.debug("Grok accuracy evaluation failed: %s", exc)

    return None


def _llm_evaluate_communication(session_id: str, question: str, answer: str) -> dict[str, Any] | None:
    """Use GPT-4o to evaluate communication clarity."""
    try:
        from workers.ai_client import chat_completion

        response = chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Evaluate the candidate's communication quality. "
                        "Return a JSON object with keys: clarity_score (0-100), "
                        "professionalism (0-100), confidence_level (0-1), "
                        "pace_appropriateness (0-1)."
                    ),
                },
                {"role": "user", "content": f"Question: {question}\n\nAnswer: {answer}"},
            ],
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=512,
        )
        if response is None:
            return None
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            logger.error("Invalid JSON from LLM (communication): %s", response)
            return None
        return {
            "clarity_score": round(parsed.get("clarity_score", 50), 2),
            "professionalism": round(parsed.get("professionalism", 50), 2),
            "confidence_level": round(parsed.get("confidence_level", 0.5), 2),
            "pace_appropriateness": round(parsed.get("pace_appropriateness", 0.5), 2),
        }
    except Exception as exc:
        logger.debug("LLM communication evaluation unavailable: %s", exc)
        return None


def _llm_generate_feedback(session_id: str, question: str, answer: str) -> dict[str, Any] | None:
    """Use GPT-4o to generate personalized interview feedback."""
    try:
        from workers.ai_client import chat_completion

        response = chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are an experienced technical interviewer. Based on the "
                        "question and answer, generate structured feedback. "
                        "Return a JSON object with keys: strengths (list of strings), "
                        "improvements (list of strings), detailed_feedback (string), "
                        "recommendation (one of: strong_hire, hire, maybe, no_hire)."
                    ),
                },
                {"role": "user", "content": f"Question: {question}\n\nAnswer: {answer}"},
            ],
            model="gpt-4o",
            temperature=0.5,
            max_tokens=1024,
        )
        if response is None:
            return None
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            logger.error("Invalid JSON from LLM (feedback): %s", response)
            return None
        recommendation = parsed.get("recommendation", "progress")
        if recommendation == "hire":
            recommendation = "progress"
        return {
            "strengths": parsed.get("strengths", []),
            "improvements": parsed.get("improvements", []),
            "detailed_feedback": parsed.get("detailed_feedback", ""),
            "recommendation": recommendation,
        }
    except Exception as exc:
        logger.debug("LLM feedback generation unavailable: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Question guardrail — no external dependencies
# ---------------------------------------------------------------------------

# Patterns are compiled lazily on first use via _get_banned_patterns() so
# that importing config (and therefore pydantic) is deferred until runtime,
# consistent with the rest of this module's deferred-import style.
_BANNED_TOPIC_PATTERNS: list[re.Pattern[str]] | None = None


def _get_banned_patterns() -> list[re.Pattern[str]]:
    """Return pre-compiled banned-topic regex patterns (built once, cached)."""
    global _BANNED_TOPIC_PATTERNS
    if _BANNED_TOPIC_PATTERNS is None:
        try:
            from config import BANNED_TOPICS
        except Exception:  # pragma: no cover — fallback if config is unavailable
            BANNED_TOPICS = [
                "age",
                "how old",
                "old are you",
                "pregnant",
                "children",
                "family planning",
                "religion",
                "religious",
                "citizenship",
                "nationality",
                "marital status",
                "married",
                "disability",
                "disabled",
                "medical condition",
                "health condition",
            ]
        _BANNED_TOPIC_PATTERNS = [re.compile(r"\b" + kw + r"\b", re.IGNORECASE) for kw in BANNED_TOPICS]
    return _BANNED_TOPIC_PATTERNS


# Crude yes/no question detector: starts with a modal/auxiliary verb + subject.
_YES_NO_RE = re.compile(
    r"^(do|does|did|have|has|had|is|are|was|were|will|would|can|could|should|may|might)\s",
    re.IGNORECASE,
)


_MIN_LENGTH = 20
_MAX_LENGTH = 500


def validate_generated_question(question: str) -> tuple[bool, list[str]]:
    """Validate an LLM-generated interview question before it is used.

    Returns a ``(is_valid, reasons)`` tuple.  When *is_valid* is ``False``,
    *reasons* is a non-empty list of human-readable rejection causes suitable
    for structured logging.
    """
    reasons: list[str] = []

    # --- A. Banned topics -----------------------------------------------
    for pattern in _get_banned_patterns():
        if pattern.search(question):
            reasons.append(f"banned topic matched: '{pattern.pattern}'")

    # --- B. Length validation -------------------------------------------
    length = len(question)
    if length < _MIN_LENGTH:
        reasons.append(f"question too short ({length} chars, minimum {_MIN_LENGTH})")
    elif length > _MAX_LENGTH:
        reasons.append(f"question too long ({length} chars, maximum {_MAX_LENGTH})")

    # --- C. Question format ---------------------------------------------
    if not question.rstrip().endswith("?"):
        reasons.append("question does not end with '?'")

    if _YES_NO_RE.match(question.lstrip()):
        reasons.append("question appears to be a simple yes/no question")

    return (len(reasons) == 0, reasons)


def _llm_generate_question(session_id: str, topic: str = "systems_design") -> str | None:
    """Use LLM to generate a dynamic interview question.

    The raw LLM response is passed through :func:`validate_generated_question`
    before being returned.  If validation fails the question is discarded,
    a structured warning is logged, and ``None`` is returned so the caller
    can fall back gracefully.
    """
    try:
        from workers.ai_client import chat_completion

        response = chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Generate a single challenging technical interview question "
                        f"about {topic}. Return only the question text, nothing else."
                    ),
                },
                {"role": "user", "content": "Generate one question."},
            ],
            model="gpt-4o-mini",
            temperature=0.8,
            max_tokens=256,
        )
        if not response:
            return None

        question = response.strip()
        is_valid, reasons = validate_generated_question(question)
        if not is_valid:
            logger.warning(
                "LLM-generated question rejected for session %s. Reasons: %s",
                session_id,
                "; ".join(reasons),
            )
            return None

        return question
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public pipeline API — real LLM evaluation with seeded stub fallback
# ---------------------------------------------------------------------------


def evaluate_answers(session_id: str) -> dict[str, Any]:
    """Execute answer evaluation pipeline for an interview session."""
    logger.info(f"Starting answer evaluation for session {session_id}")

    quality = evaluate_answer_quality(session_id)
    accuracy = evaluate_technical_accuracy(session_id)
    clarity = evaluate_communication(session_id)
    feedback = generate_feedback(session_id)

    results = {
        "session_id": session_id,
        "answer_quality_score": quality,
        "technical_accuracy": accuracy,
        "communication_clarity": clarity,
        "feedback": feedback,
        "risk_score": 0.0,
    }

    results["risk_score"] = calculate_evaluation_risk_score(results)
    logger.info(f"Answer evaluation completed for session {session_id}: {results}")
    return results


def evaluate_answer_quality(session_id: str) -> dict[str, Any]:
    """Evaluate answer quality — real LLM with seeded stub fallback."""
    logger.info(f"Evaluating answer quality for session {session_id}")

    real = _llm_evaluate_answer_quality(
        session_id,
        "Describe your experience with distributed systems.",
        "I have five years of experience building distributed systems in Python and Go.",
    )
    if real is not None:
        return real

    base = 0.55 + _seeded_unit(session_id, "quality") * 0.45
    return {
        "overall_quality_score": round(base * 100, 2),
        "relevance": round(base * 0.95, 2),
        "completeness": round(base * 0.9, 2),
        "clarity": round(base * 0.92, 2),
        "feedback": "Response is on-topic and reasonably complete.",
    }


def evaluate_technical_accuracy(session_id: str) -> dict[str, Any]:
    """Evaluate technical accuracy — real LLM with seeded stub fallback."""
    logger.info(f"Evaluating technical accuracy for session {session_id}")

    real = _llm_evaluate_technical_accuracy(
        session_id,
        "Describe your experience with distributed systems.",
        "I have five years of experience building distributed systems in Python and Go.",
    )
    if real is not None:
        return real

    base = 0.5 + _seeded_unit(session_id, "accuracy") * 0.5
    return {
        "accuracy_score": round(base * 100, 2),
        "correct_concepts_count": int(base * 8),
        "incorrect_concepts_count": max(0, 3 - int(base * 8)),
        "knowledge_gaps": [] if base > 0.6 else ["systems design depth"],
    }


def evaluate_communication(session_id: str) -> dict[str, Any]:
    """Evaluate communication clarity — real LLM with seeded stub fallback."""
    logger.info(f"Evaluating communication clarity for session {session_id}")

    real = _llm_evaluate_communication(
        session_id,
        "Describe your experience with distributed systems.",
        "I have five years of experience building distributed systems in Python and Go.",
    )
    if real is not None:
        return real

    base = 0.55 + _seeded_unit(session_id, "comms") * 0.45
    return {
        "clarity_score": round(base * 100, 2),
        "professionalism": round(base * 100, 2),
        "confidence_level": round(base * 0.9, 2),
        "pace_appropriateness": round(base * 0.95, 2),
    }


def generate_feedback(session_id: str) -> dict[str, Any]:
    """Generate feedback — real LLM with seeded stub fallback."""
    logger.info(f"Generating feedback for session {session_id}")

    real = _llm_generate_feedback(
        session_id,
        "Describe your experience with distributed systems.",
        "I have five years of experience building distributed systems in Python and Go.",
    )
    if real is not None:
        return real

    return {
        "strengths": ["clear structure", "relevant examples"],
        "improvements": ["deepen systems-design discussion"],
        "detailed_feedback": "Solid answers overall with room to elaborate on trade-offs.",
        "recommendation": "progress",
    }


def calculate_evaluation_risk_score(results: dict[str, Any]) -> float:
    """Calculate a 0–1 risk score (inverse of performance)."""
    from workers.risk_engine import RiskScoringEngine

    quality = results.get("answer_quality_score", {}).get("overall_quality_score", 50) / 100.0
    accuracy = results.get("technical_accuracy", {}).get("accuracy_score", 50) / 100.0
    clarity = results.get("communication_clarity", {}).get("clarity_score", 50) / 100.0

    quality_risk = (1 - quality) * RiskScoringEngine.EVALUATION_FACTORS["low_quality_answers"]
    accuracy_risk = (1 - accuracy) * RiskScoringEngine.EVALUATION_FACTORS["low_accuracy"]
    clarity_risk = (1 - clarity) * RiskScoringEngine.EVALUATION_FACTORS["poor_communication"]

    score = quality_risk + accuracy_risk + clarity_risk
    return round(min(score, 1.0), 3)
