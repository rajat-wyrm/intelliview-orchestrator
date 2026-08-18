"""
Dataset Validation Pipeline
============================
Validates AI training / evaluation datasets (question bank exports,
evaluation golden-sets, hallucination-detector label sets, etc.) against
a configurable rule set before they are used to train, prompt, or grade
the orchestrator's AI evaluators.

Usage (CLI):
    python -m scripts.dataset_validation.validator \
        --input scripts/dataset_validation/sample_data/questions_valid.json \
        --schema question_bank \
        --output report.json

Usage (library):
    from scripts.dataset_validation.validator import DatasetValidator
    from scripts.dataset_validation.schemas import QUESTION_BANK_SCHEMA

    validator = DatasetValidator(QUESTION_BANK_SCHEMA)
    report = validator.validate(records)
    print(report.to_markdown())
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Rule outcome primitives
# ---------------------------------------------------------------------------


@dataclass
class RuleResult:
    rule_name: str
    severity: str  # "error" | "warning"
    passed: bool
    message: str
    offending_examples: list[Any] = field(default_factory=list)


@dataclass
class ValidationReport:
    dataset_name: str
    total_records: int
    results: list[RuleResult] = field(default_factory=list)

    @property
    def errors(self) -> list[RuleResult]:
        return [r for r in self.results if r.severity == "error" and not r.passed]

    @property
    def warnings(self) -> list[RuleResult]:
        return [r for r in self.results if r.severity == "warning" and not r.passed]

    @property
    def is_valid(self) -> bool:
        """A dataset is usable if it has no ERROR-level failures (warnings are advisory)."""
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "total_records": self.total_records,
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "checks": [
                {
                    "rule": r.rule_name,
                    "severity": r.severity,
                    "passed": r.passed,
                    "message": r.message,
                    "offending_examples": r.offending_examples[:5],
                }
                for r in self.results
            ],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Dataset Validation Report — {self.dataset_name}",
            "",
            f"- Records checked: **{self.total_records}**",
            f"- Result: **{'PASS' if self.is_valid else 'FAIL'}**",
            f"- Errors: **{len(self.errors)}**  |  Warnings: **{len(self.warnings)}**",
            "",
            "| Rule | Severity | Status | Detail |",
            "|---|---|---|---|",
        ]
        for r in self.results:
            status = (
                "✅ pass"
                if r.passed
                else ("❌ fail" if r.severity == "error" else "⚠️ warn")
            )
            lines.append(f"| {r.rule_name} | {r.severity} | {status} | {r.message} |")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class DatasetValidator:
    """
    Schema-driven validator. A schema dict declares:
      required_fields: {field_name: python_type}
      enum_fields: {field_name: {allowed values}}
      numeric_ranges: {field_name: (min, max)}
      text_length: {field_name: (min_chars, max_chars)}
      id_field: str  -> checked for uniqueness
      dedup_field: str | None  -> checked for near-duplicate text
      balance_field: str | None -> checked for class-balance skew
      balance_max_ratio: float  -> max allowed (most_common / least_common) ratio
    """

    def __init__(self, schema: dict[str, Any]):
        self.schema = schema

    def validate(
        self, records: list[dict[str, Any]], dataset_name: str = "dataset"
    ) -> ValidationReport:
        report = ValidationReport(dataset_name=dataset_name, total_records=len(records))

        report.results.append(self._check_non_empty(records))
        report.results.append(self._check_required_fields(records))
        report.results.append(self._check_field_types(records))
        report.results.append(self._check_enum_fields(records))
        report.results.append(self._check_numeric_ranges(records))
        report.results.append(self._check_text_length(records))

        if self.schema.get("id_field"):
            report.results.append(self._check_unique_ids(records))

        if self.schema.get("dedup_field"):
            report.results.append(self._check_near_duplicates(records))

        if self.schema.get("balance_field"):
            report.results.append(self._check_class_balance(records))

        return report

    # -- individual checks ---------------------------------------------------

    def _check_non_empty(self, records: list[dict[str, Any]]) -> RuleResult:
        passed = len(records) > 0
        return RuleResult(
            "non_empty_dataset",
            "error",
            passed,
            "Dataset has at least one record." if passed else "Dataset is empty.",
        )

    def _check_required_fields(self, records: list[dict[str, Any]]) -> RuleResult:
        required = list(self.schema.get("required_fields", {}).keys())
        offenders = []
        for i, rec in enumerate(records):
            missing = [f for f in required if rec.get(f) in (None, "", [])]
            if missing:
                offenders.append(
                    {
                        "index": i,
                        "id": rec.get(self.schema.get("id_field")),
                        "missing": missing,
                    }
                )
        passed = len(offenders) == 0
        return RuleResult(
            "required_fields_present",
            "error",
            passed,
            (
                "All required fields present."
                if passed
                else f"{len(offenders)} record(s) missing required fields."
            ),
            offenders,
        )

    def _check_field_types(self, records: list[dict[str, Any]]) -> RuleResult:
        type_map = self.schema.get("required_fields", {})
        offenders = []
        for i, rec in enumerate(records):
            for f_name, f_type in type_map.items():
                if (
                    f_name in rec
                    and rec[f_name] is not None
                    and not isinstance(rec[f_name], f_type)
                ):
                    offenders.append(
                        {
                            "index": i,
                            "id": rec.get(self.schema.get("id_field")),
                            "field": f_name,
                            "expected": f_type.__name__,
                            "got": type(rec[f_name]).__name__,
                        }
                    )
        passed = len(offenders) == 0
        return RuleResult(
            "field_types_correct",
            "error",
            passed,
            (
                "All fields match expected types."
                if passed
                else f"{len(offenders)} type mismatch(es) found."
            ),
            offenders,
        )

    def _check_enum_fields(self, records: list[dict[str, Any]]) -> RuleResult:
        enum_fields = self.schema.get("enum_fields", {})
        offenders = []
        for i, rec in enumerate(records):
            for f_name, allowed in enum_fields.items():
                val = rec.get(f_name)
                if val is not None and val not in allowed:
                    offenders.append(
                        {
                            "index": i,
                            "id": rec.get(self.schema.get("id_field")),
                            "field": f_name,
                            "value": val,
                            "allowed": sorted(allowed),
                        }
                    )
        passed = len(offenders) == 0
        return RuleResult(
            "enum_values_valid",
            "error",
            passed,
            (
                "All categorical fields use allowed values."
                if passed
                else f"{len(offenders)} invalid categorical value(s)."
            ),
            offenders,
        )

    def _check_numeric_ranges(self, records: list[dict[str, Any]]) -> RuleResult:
        ranges = self.schema.get("numeric_ranges", {})
        offenders = []
        for i, rec in enumerate(records):
            for f_name, (lo, hi) in ranges.items():
                val = rec.get(f_name)
                if (
                    val is not None
                    and isinstance(val, int | float)
                    and not (lo <= val <= hi)
                ):
                    offenders.append(
                        {
                            "index": i,
                            "id": rec.get(self.schema.get("id_field")),
                            "field": f_name,
                            "value": val,
                            "range": [lo, hi],
                        }
                    )
        passed = len(offenders) == 0
        return RuleResult(
            "numeric_ranges_valid",
            "error",
            passed,
            (
                "All numeric fields within expected range."
                if passed
                else f"{len(offenders)} out-of-range value(s)."
            ),
            offenders,
        )

    def _check_text_length(self, records: list[dict[str, Any]]) -> RuleResult:
        text_rules = self.schema.get("text_length", {})
        offenders = []
        for i, rec in enumerate(records):
            for f_name, (min_len, max_len) in text_rules.items():
                val = rec.get(f_name)
                if isinstance(val, str) and not (
                    min_len <= len(val.strip()) <= max_len
                ):
                    offenders.append(
                        {
                            "index": i,
                            "id": rec.get(self.schema.get("id_field")),
                            "field": f_name,
                            "length": len(val.strip()),
                            "expected": [min_len, max_len],
                        }
                    )
        passed = len(offenders) == 0
        return RuleResult(
            "text_length_valid",
            "warning",
            passed,
            (
                "All text fields within expected length bounds."
                if passed
                else f"{len(offenders)} field(s) outside length bounds."
            ),
            offenders,
        )

    def _check_unique_ids(self, records: list[dict[str, Any]]) -> RuleResult:
        id_field = self.schema["id_field"]
        ids = [rec.get(id_field) for rec in records if rec.get(id_field) is not None]
        counts = Counter(ids)
        dupes = [k for k, v in counts.items() if v > 1]
        passed = len(dupes) == 0
        return RuleResult(
            "unique_ids",
            "error",
            passed,
            (
                "All record IDs are unique."
                if passed
                else f"{len(dupes)} duplicate ID(s) found."
            ),
            dupes,
        )

    def _check_near_duplicates(self, records: list[dict[str, Any]]) -> RuleResult:
        """Flags exact/near-duplicate text after normalization (lowercase, whitespace, punctuation)."""
        dedup_field = self.schema["dedup_field"]
        seen: dict[str, Any] = {}
        offenders = []
        for i, rec in enumerate(records):
            raw = rec.get(dedup_field)
            if not isinstance(raw, str):
                continue
            norm = re.sub(r"[^\w\s]", "", raw.lower())
            norm = re.sub(r"\s+", " ", norm).strip()
            if norm in seen:
                offenders.append(
                    {
                        "index": i,
                        "id": rec.get(self.schema.get("id_field")),
                        "duplicate_of_index": seen[norm],
                    }
                )
            else:
                seen[norm] = i
        passed = len(offenders) == 0
        return RuleResult(
            "no_near_duplicates",
            "warning",
            passed,
            (
                "No near-duplicate records detected."
                if passed
                else f"{len(offenders)} near-duplicate record(s) found."
            ),
            offenders,
        )

    def _check_class_balance(self, records: list[dict[str, Any]]) -> RuleResult:
        balance_field = self.schema["balance_field"]
        max_ratio = self.schema.get("balance_max_ratio", 5.0)
        counts = Counter(
            rec.get(balance_field)
            for rec in records
            if rec.get(balance_field) is not None
        )
        if not counts:
            return RuleResult(
                "class_balance", "warning", True, "No values to check balance for."
            )
        most, least = max(counts.values()), min(counts.values())
        ratio = most / least if least else float("inf")
        passed = ratio <= max_ratio
        return RuleResult(
            "class_balance",
            "warning",
            passed,
            f"Class distribution for '{balance_field}': {dict(counts)} (ratio {ratio:.1f}x, max allowed {max_ratio}x).",
            [] if passed else [dict(counts)],
        )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_records(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text())
        return data if isinstance(data, list) else data.get("records", [])
    if p.suffix.lower() == ".csv":
        with p.open(newline="") as f:
            return list(csv.DictReader(f))
    raise ValueError(f"Unsupported file type: {p.suffix}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    from scripts.dataset_validation.schemas import SCHEMAS

    parser = argparse.ArgumentParser(
        description="Validate an AI training/evaluation dataset."
    )
    parser.add_argument(
        "--input", required=True, help="Path to .json or .csv dataset file"
    )
    parser.add_argument("--schema", required=True, choices=list(SCHEMAS.keys()))
    parser.add_argument(
        "--output", default=None, help="Optional path to write JSON report"
    )
    args = parser.parse_args()

    records = load_records(args.input)
    validator = DatasetValidator(SCHEMAS[args.schema])
    report = validator.validate(records, dataset_name=Path(args.input).name)

    print(report.to_markdown())

    if args.output:
        Path(args.output).write_text(json.dumps(report.to_dict(), indent=2))
        print(f"\nJSON report written to {args.output}")

    raise SystemExit(0 if report.is_valid else 1)


if __name__ == "__main__":
    main()
