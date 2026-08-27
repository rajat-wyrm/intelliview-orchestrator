from orchestrator.question_bank import (
    ADAPTIVE_FOLLOWUP_EXAMPLES,
    build_adaptive_followup_prompt,
)


def test_adaptive_followup_prompt_contains_required_instructions():
    prompt = build_adaptive_followup_prompt(
        "What is database indexing?",
        "Indexing makes queries faster.",
    )

    assert "What is database indexing?" in prompt
    assert "Indexing makes queries faster." in prompt
    assert "ONE deeper follow-up question" in prompt
    assert "Stay strictly on the topic of the original question." in prompt
    assert '"original_question"' in prompt
    assert '"candidate_answer"' in prompt
    assert '"followup_prompt"' in prompt


def test_adaptive_followup_prompt_handles_whitespace():
    prompt = build_adaptive_followup_prompt(
        "  What is REST?  ",
        "  It uses HTTP methods.  ",
    )

    assert "What is REST?" in prompt
    assert "It uses HTTP methods." in prompt
    assert "  What is REST?  " not in prompt
    assert "  It uses HTTP methods.  " not in prompt


def test_adaptive_followup_examples_have_required_data_shape():
    assert len(ADAPTIVE_FOLLOWUP_EXAMPLES) == 5

    required_keys = {
        "original_question",
        "candidate_answer",
        "followup_prompt",
    }

    for example in ADAPTIVE_FOLLOWUP_EXAMPLES:
        assert set(example.keys()) == required_keys

        assert example["original_question"]
        assert example["candidate_answer"]
        assert example["followup_prompt"]
