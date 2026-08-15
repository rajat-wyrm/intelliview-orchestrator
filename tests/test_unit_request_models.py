"""
Unit tests for the API request models and validation.
"""

import pytest
from pydantic import ValidationError

from orchestrator.main import StartInterviewRequest


def test_candidate_id_required():
    with pytest.raises(ValidationError):
        StartInterviewRequest(candidate_id="")


def test_candidate_id_too_long():
    with pytest.raises(ValidationError):
        StartInterviewRequest(candidate_id="x" * 129)


def test_candidate_id_strips_and_accepts_alnum_dots():
    req = StartInterviewRequest(candidate_id="  cand_123.test  ")
    assert req.candidate_id == "cand_123.test"


def test_candidate_id_rejects_invalid_chars():
    with pytest.raises(ValidationError):
        StartInterviewRequest(candidate_id="bad/id")


def test_priority_default_is_medium():
    req = StartInterviewRequest(candidate_id="c1")
    assert req.priority == "medium"


def test_priority_lowercased_and_validated():
    req = StartInterviewRequest(candidate_id="c1", priority="HIGH")
    assert req.priority == "high"
    with pytest.raises(ValidationError):
        StartInterviewRequest(candidate_id="c1", priority="urgent")


def test_optional_fields_stripped():
    req = StartInterviewRequest(
        candidate_id="c1",
        candidate_name="  Mukta Redij  ",
        position="  Senior Engineer  ",
    )
    assert req.candidate_name == "Mukta Redij"
    assert req.position == "Senior Engineer"

def test_language_default_is_english():
    req = StartInterviewRequest(candidate_id="c1")
    assert req.language == "en"
def test_language_accepts_explicit_value():
    req = StartInterviewRequest(candidate_id="c1", language="hi")
    assert req.language == "hi"