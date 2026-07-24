"""Unit tests for the LLM question guardrail (Issue #121).

Tests cover every validation branch of validate_generated_question() plus
the integration with _llm_generate_question() via mocking.
No external services are required.
"""

from unittest.mock import MagicMock, patch

import pytest

from workers.evaluation_pipeline import validate_generated_question

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_question() -> str:
    """A well-formed, safe, open-ended technical question."""
    return "How would you design a distributed rate-limiter at the API gateway layer?"


# ---------------------------------------------------------------------------
# A. Banned topic detection
# ---------------------------------------------------------------------------


class TestBannedTopics:
    @pytest.mark.parametrize(
        "question",
        [
            "How old are you?",
            "What is your age?",
            "Are you pregnant or planning to start a family?",
            "Do you have any children?",
            "Tell me about your family planning.",
            "What is your religion?",
            "Are you religious?",
            "What is your citizenship status?",
            "What is your nationality?",
            "What is your marital status?",
            "Are you married?",
            "Do you have any disability?",
            "Are you disabled in any way?",
            "Do you have a medical condition that affects work?",
            "Do you have any health condition we should know about?",
        ],
    )
    def test_banned_topic_is_rejected(self, question: str):
        is_valid, reasons = validate_generated_question(question)
        assert not is_valid
        assert any("banned topic" in r for r in reasons), reasons

    def test_unrelated_word_age_not_flagged_in_technical_context(self):
        """'age' inside a compound word must not false-positive via word boundary."""
        q = "How would you handle a database outage in production at scale?"
        _, reasons = validate_generated_question(q)
        banned_hits = [r for r in reasons if "banned topic" in r]
        assert not banned_hits, f"False positive on 'outage': {reasons}"

    def test_case_insensitive_matching(self):
        is_valid, reasons = validate_generated_question("What is your RELIGION?")
        assert not is_valid
        assert any("banned topic" in r for r in reasons)


# ---------------------------------------------------------------------------
# B. Length validation
# ---------------------------------------------------------------------------


class TestLengthValidation:
    def test_too_short_is_rejected(self):
        short = "Why Python?"  # 11 chars
        is_valid, reasons = validate_generated_question(short)
        assert not is_valid
        assert any("too short" in r for r in reasons)

    def test_too_long_is_rejected(self):
        over_limit = ("A" * 500) + "?"  # 501 chars
        is_valid_over, reasons_over = validate_generated_question(over_limit)
        assert not is_valid_over
        assert any("too long" in r for r in reasons_over)

    def test_exactly_min_length_does_not_trigger_short(self):
        q = "Explain CAP theorem?"  # 20 chars
        assert len(q) == 20
        _, reasons = validate_generated_question(q)
        assert not any("too short" in r for r in reasons)

    def test_exactly_max_length_does_not_trigger_long(self):
        filler = "x" * 498
        q = filler + " ?"  # 500 chars
        assert len(q) == 500
        _, reasons = validate_generated_question(q)
        assert not any("too long" in r for r in reasons)


# ---------------------------------------------------------------------------
# C. Question format
# ---------------------------------------------------------------------------


class TestQuestionFormat:
    def test_missing_question_mark_is_rejected(self):
        q = "Explain how you would design a rate limiter"
        is_valid, reasons = validate_generated_question(q)
        assert not is_valid
        assert any("does not end with" in r for r in reasons)

    def test_trailing_whitespace_after_question_mark_passes(self):
        q = "How would you design a caching layer?   "
        _, reasons = validate_generated_question(q)
        assert not any("does not end with" in r for r in reasons)

    @pytest.mark.parametrize(
        "q",
        [
            "Do you like Python?",
            "Have you worked with Kubernetes?",
            "Is Redis a good cache?",
            "Can you explain CAP theorem?",
            "Would you use a monolith or microservices?",
            "Did you ever deploy to production?",
        ],
    )
    def test_yes_no_question_is_rejected(self, q: str):
        is_valid, reasons = validate_generated_question(q)
        assert not is_valid
        assert any("yes/no" in r for r in reasons)

    def test_open_ended_question_passes_format_check(self):
        q = _valid_question()
        _, reasons = validate_generated_question(q)
        assert not any("yes/no" in r for r in reasons)
        assert not any("does not end with" in r for r in reasons)


# ---------------------------------------------------------------------------
# E. Valid question — golden path
# ---------------------------------------------------------------------------


class TestValidQuestion:
    def test_well_formed_question_passes_all_checks(self):
        is_valid, reasons = validate_generated_question(_valid_question())
        assert is_valid, f"Expected valid but got reasons: {reasons}"
        assert reasons == []

    def test_return_type_is_tuple_of_bool_and_list(self):
        result = validate_generated_question(_valid_question())
        assert isinstance(result, tuple)
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)

    def test_multiple_violations_accumulate(self):
        """A single bad question can fail multiple checks simultaneously."""
        # Too short, no "?", banned topic, yes/no opener
        bad = "Are you married"
        is_valid, reasons = validate_generated_question(bad)
        assert not is_valid
        assert len(reasons) >= 3  # banned topic + too short + no "?" + yes/no


# ---------------------------------------------------------------------------
# F. Integration: _llm_generate_question wires the validator
# ---------------------------------------------------------------------------


class TestLlmGenerateQuestionIntegration:
    def _patch_chat(self, return_value):
        """Return a context manager that patches chat_completion at import time."""
        ai_mock = MagicMock()
        ai_mock.chat_completion = MagicMock(return_value=return_value)
        ai_mock.HAS_OPENAI = True
        return patch.dict("sys.modules", {"workers.ai_client": ai_mock})

    def test_valid_llm_response_is_returned(self):
        from workers.evaluation_pipeline import _llm_generate_question

        good_q = _valid_question()
        with self._patch_chat(good_q):
            result = _llm_generate_question("sess-valid")
        assert result == good_q

    def test_invalid_llm_response_returns_none_and_logs(self, caplog):
        import logging

        from workers.evaluation_pipeline import _llm_generate_question

        bad_q = "Do you have any children?"  # banned topic + yes/no

        with self._patch_chat(bad_q):
            with caplog.at_level(logging.WARNING, logger="workers.evaluation_pipeline"):
                result = _llm_generate_question("sess-bad")

        assert result is None
        assert any("rejected" in msg.lower() for msg in caplog.messages), caplog.messages

    def test_empty_llm_response_returns_none(self):
        from workers.evaluation_pipeline import _llm_generate_question

        with self._patch_chat(""):
            result = _llm_generate_question("sess-empty")
        assert result is None

    def test_llm_exception_returns_none(self):
        from workers.evaluation_pipeline import _llm_generate_question

        ai_mock = MagicMock()
        ai_mock.chat_completion = MagicMock(side_effect=RuntimeError("API down"))
        ai_mock.HAS_OPENAI = True
        with patch.dict("sys.modules", {"workers.ai_client": ai_mock}):
            result = _llm_generate_question("sess-exc")
        assert result is None
