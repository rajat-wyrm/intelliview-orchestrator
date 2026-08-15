"use client";
import { memo } from "react";
import { Badge } from "@/components/Badge";

const DIFFICULTY_VARIANT = {
  easy: "success",
  medium: "warn",
  hard: "danger",
};

const DIFFICULTY_LABEL = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};

/** Normalise a difficulty value from the API to a known key, or null. */
function normaliseDifficulty(value) {
  if (typeof value !== "string") return null;
  const key = value.trim().toLowerCase();
  return key in DIFFICULTY_LABEL ? key : null;
}

/** Format a 0-10 score for display without trailing noise. */
function formatScore(score) {
  if (score == null || Number.isNaN(Number(score))) return null;
  const n = Number(score);
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

function QuestionProgressionImpl({ questions }) {
  if (!Array.isArray(questions) || questions.length === 0) {
    return (
      <p data-testid="progression-empty" className="text-sm text-muted">
        No questions recorded for this session yet.
      </p>
    );
  }

  return (
    <ol data-testid="difficulty-progression" className="space-y-2">
      {questions.map((q, i) => {
        const key = normaliseDifficulty(q?.difficulty);
        const score = formatScore(q?.score);

        return (
          <li
            key={q?.question_id ?? `question-${i}`}
            data-testid="question-row"
            data-difficulty={key ?? "unknown"}
            className="flex items-center gap-2 rounded-md border border-border bg-bg-card px-3 py-2"
          >
            <span className="text-sm text-zinc-200">Question {i + 1}</span>
            <span aria-hidden="true" className="text-muted">
              —
            </span>
            <Badge variant={key ? DIFFICULTY_VARIANT[key] : "muted"}>
              {key ? DIFFICULTY_LABEL[key] : "—"}
            </Badge>
            <span aria-hidden="true" className="text-muted">
              —
            </span>
            <span
              data-testid="question-score"
              className="text-sm text-zinc-400"
            >
              {score != null ? `Score ${score}` : "Pending"}
            </span>
            {q?.text && (
              <span className="ml-auto truncate text-xs text-muted">
                {q.text}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

const QuestionProgression = memo(QuestionProgressionImpl);
export default QuestionProgression;
