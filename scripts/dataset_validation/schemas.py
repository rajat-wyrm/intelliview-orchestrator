"""
Dataset schemas for intelliview-orchestrator.

Add a new SCHEMAS entry here whenever a new dataset type needs validation
(e.g. a golden set for a new AI module).
"""

# Matches orchestrator/question_bank.py + database/models.py::Question
QUESTION_BANK_SCHEMA = {
    "id_field": "question_id",
    "dedup_field": "text",
    "balance_field": "category",
    "balance_max_ratio": 4.0,
    "required_fields": {
        "question_id": str,
        "text": str,
        "category": str,
        "difficulty": str,
    },
    "enum_fields": {
        "category": {"technical", "behavioral", "situational"},
        "difficulty": {"easy", "medium", "hard"},
    },
    "text_length": {
        "text": (10, 1000),
    },
    "numeric_ranges": {
        "usage_count": (0, 10**9),
        "avg_score": (0, 100),
    },
}

# Golden/evaluation set: (question, answer, expected label) used to
# regression-test workers/evaluation_pipeline.py and the hallucination
# detector before/after prompt or model changes.
EVALUATION_DATASET_SCHEMA = {
    "id_field": "sample_id",
    "dedup_field": "answer",
    "balance_field": "expected_label",
    "balance_max_ratio": 3.0,
    "required_fields": {
        "sample_id": str,
        "question": str,
        "answer": str,
        "expected_label": str,
    },
    "enum_fields": {
        "expected_label": {"grounded", "hallucinated", "partially_grounded"},
    },
    "text_length": {
        "question": (10, 1000),
        "answer": (1, 5000),
    },
    "numeric_ranges": {
        "expected_score": (0, 100),
    },
    "conditional_required": [
        {
            "when_field": "expected_label",
            "when_value": "hallucinated",
            "then_field": "expected_score",
        },
    ],
}

SCHEMAS = {
    "question_bank": QUESTION_BANK_SCHEMA,
    "evaluation_dataset": EVALUATION_DATASET_SCHEMA,
}
