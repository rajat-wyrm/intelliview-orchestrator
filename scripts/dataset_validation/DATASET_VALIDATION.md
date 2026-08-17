# Dataset Validation Pipeline

Validates datasets used to prompt, train, or grade the orchestrator's AI
evaluators — the interview **question bank** and any **evaluation/golden
sets** used to regression-test the answer-evaluation and hallucination
detection modules.

## Why

Bad rows in these datasets fail silently: a malformed question can reach a
candidate mid-interview, and a mislabeled golden-set row can quietly skew
accuracy metrics for the evaluation pipeline. This pipeline catches those
issues before the data is used.

## Validation Rules

| Rule | Severity | What it checks |
|---|---|---|
| `non_empty_dataset` | error | Dataset contains at least one record |
| `required_fields_present` | error | No required field is missing or empty |
| `field_types_correct` | error | Field values match the expected Python type |
| `enum_values_valid` | error | Categorical fields (e.g. `category`, `difficulty`, `expected_label`) use only allowed values |
| `numeric_ranges_valid` | error | Numeric fields (e.g. scores, usage counts) fall within expected bounds |
| `unique_ids` | error | No duplicate record IDs |
| `text_length_valid` | warning | Text fields aren't suspiciously short/long |
| `no_near_duplicates` | warning | No two records have near-identical text (normalized for case/punctuation/whitespace) |
| `class_balance` | warning | No category dominates the dataset beyond a configurable ratio |

**Errors** fail the pipeline (dataset is unusable as-is). **Warnings** are
advisory — surfaced in the report but don't block usage.

## Schemas

Two dataset types are pre-configured in `scripts/dataset_validation/schemas.py`:

- **`question_bank`** — matches `orchestrator/question_bank.py` /
  `database/models.py::Question`: `question_id`, `text`, `category`
  (technical/behavioral/situational), `difficulty` (easy/medium/hard),
  `usage_count`, `avg_score`.
- **`evaluation_dataset`** — labeled golden set for regression-testing
  `workers/evaluation_pipeline.py` and the hallucination detector:
  `sample_id`, `question`, `answer`, `expected_label`
  (grounded/hallucinated/partially_grounded), `expected_score`.

Add new schemas here as new AI modules need labeled datasets.

## Usage

### CLI

```bash
python -m scripts.dataset_validation.validator \
    --input path/to/dataset.json \
    --schema question_bank \
    --output report.json
```

Supports `.json` (a list of records, or `{"records": [...]}`) and `.csv`
input. Exits with status `1` if any error-level rule fails, so it can be
wired into CI:

```yaml
# .github/workflows example step
- name: Validate question bank dataset
  run: python -m scripts.dataset_validation.validator --input data/questions.json --schema question_bank
```

### As a library

```python
from scripts.dataset_validation.validator import DatasetValidator
from scripts.dataset_validation.schemas import QUESTION_BANK_SCHEMA

report = DatasetValidator(QUESTION_BANK_SCHEMA).validate(records)
print(report.to_markdown())
assert report.is_valid
```

## Sample Reports

Sample datasets are provided under `scripts/dataset_validation/sample_data/`:

- `questions_valid.json` — passes all checks.
- `questions_invalid.json` — deliberately contains a duplicate ID, a
  near-duplicate question, an invalid category, an invalid difficulty, an
  out-of-range score, a negative usage count, and a missing `text` field —
  used to demonstrate that every rule fires correctly.

Running the validator against `questions_invalid.json` produces:

## Testing

```bash
pytest tests/test_unit_dataset_validator.py -v
```

11 tests covering: empty datasets, missing fields, invalid enums,
out-of-range values, duplicate IDs, near-duplicates, class imbalance, and
report serialization — for both the `question_bank` and
`evaluation_dataset` schemas.

## Extending

To validate a new dataset type (e.g. a labeled set for a future proctoring
model):

1. Add a schema dict to `schemas.py` describing required fields, enums,
   numeric ranges, and text-length bounds.
2. Register it in the `SCHEMAS` dict.
3. Add sample valid/invalid fixtures under `sample_data/` and a test class
   in `tests/test_unit_dataset_validator.py`.

No changes to `validator.py` are needed — the engine is schema-driven.