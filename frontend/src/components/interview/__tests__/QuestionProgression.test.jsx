import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import QuestionProgression from "../QuestionProgression";

/**
 * Feature 11.3 — Adaptive Interview Difficulty
 * Aayush — Frontend / Reporting + Tests
 *
 * Difficulty rules owned by workers/adaptive_difficulty.py (Sushma):
 *   score > 8 -> hard | score < 5 -> easy | 5..8 -> medium
 * These tests assert the UI *renders* the difficulty the API reports.
 * They deliberately do not re-implement the threshold logic.
 */

const progression = [
  { question_id: "q1", text: "Explain closures", difficulty: "medium", score: 9 },
  { question_id: "q2", text: "Design a rate limiter", difficulty: "hard", score: 7 },
  { question_id: "q3", text: "What is a deadlock", difficulty: "medium", score: 4 },
  { question_id: "q4", text: "Define REST", difficulty: "easy", score: null },
];

describe("QuestionProgression — difficulty labels", () => {
  it("renders a labelled row for every question in the report", () => {
    render(<QuestionProgression questions={progression} />);

    const rows = screen.getAllByTestId("question-row");
    expect(rows).toHaveLength(4);
  });

  it("renders each difficulty label exactly as reported by the API", () => {
    render(<QuestionProgression questions={progression} />);
    const rows = screen.getAllByTestId("question-row");

    expect(rows[0]).toHaveTextContent("Medium");
    expect(rows[1]).toHaveTextContent("Hard");
    expect(rows[2]).toHaveTextContent("Medium");
    expect(rows[3]).toHaveTextContent("Easy");
  });

  it("renders the question number, difficulty and score together", () => {
    render(<QuestionProgression questions={progression} />);
    const rows = screen.getAllByTestId("question-row");

    expect(rows[0].textContent).toMatch(/Question 1.*Medium.*Score 9/);
    expect(rows[1].textContent).toMatch(/Question 2.*Hard.*Score 7/);
    expect(rows[2].textContent).toMatch(/Question 3.*Medium.*Score 4/);
  });
});

describe("QuestionProgression — difficulty transitions", () => {
  it("preserves the order of the difficulty progression", () => {
    render(<QuestionProgression questions={progression} />);

    const sequence = screen
      .getAllByTestId("question-row")
      .map((row) => row.getAttribute("data-difficulty"));

    expect(sequence).toEqual(["medium", "hard", "medium", "easy"]);
  });

  it("reflects an escalating progression driven by high scores", () => {
    render(
      <QuestionProgression
        questions={[
          { question_id: "a", difficulty: "easy", score: 7 },
          { question_id: "b", difficulty: "medium", score: 10 },
          { question_id: "c", difficulty: "hard", score: 9 },
        ]}
      />,
    );

    const sequence = screen
      .getAllByTestId("question-row")
      .map((row) => row.getAttribute("data-difficulty"));

    expect(sequence).toEqual(["easy", "medium", "hard"]);
  });

  it("reflects a de-escalating progression driven by low scores", () => {
    render(
      <QuestionProgression
        questions={[
          { question_id: "a", difficulty: "hard", score: 4 },
          { question_id: "b", difficulty: "easy", score: 6 },
          { question_id: "c", difficulty: "medium", score: 2 },
        ]}
      />,
    );

    const sequence = screen
      .getAllByTestId("question-row")
      .map((row) => row.getAttribute("data-difficulty"));

    expect(sequence).toEqual(["hard", "easy", "medium"]);
  });

  it("normalises casing and whitespace returned by the API", () => {
    render(
      <QuestionProgression
        questions={[
          { question_id: "a", difficulty: "MEDIUM", score: 6 },
          { question_id: "b", difficulty: " Hard ", score: 9 },
        ]}
      />,
    );

    const rows = screen.getAllByTestId("question-row");
    expect(rows[0]).toHaveTextContent("Medium");
    expect(rows[0].getAttribute("data-difficulty")).toBe("medium");
    expect(rows[1]).toHaveTextContent("Hard");
    expect(rows[1].getAttribute("data-difficulty")).toBe("hard");
  });
});

describe("QuestionProgression — fallback behaviour", () => {
  it("shows a placeholder when a question has no difficulty recorded", () => {
    render(
      <QuestionProgression
        questions={[{ question_id: "a", text: "Legacy question", score: 6 }]}
      />,
    );

    const row = screen.getByTestId("question-row");
    expect(row.getAttribute("data-difficulty")).toBe("unknown");
    expect(row).toHaveTextContent("Score 6");
  });

  it("shows Pending when a question has been served but not yet scored", () => {
    render(
      <QuestionProgression
        questions={[{ question_id: "a", difficulty: "easy", score: null }]}
      />,
    );

    expect(screen.getByTestId("question-score")).toHaveTextContent("Pending");
    expect(screen.getByTestId("question-row")).toHaveTextContent("Easy");
  });

  it("ignores an unrecognised difficulty value without crashing", () => {
    render(
      <QuestionProgression
        questions={[{ question_id: "a", difficulty: "impossible", score: 5 }]}
      />,
    );

    expect(screen.getByTestId("question-row").getAttribute("data-difficulty")).toBe(
      "unknown",
    );
  });

  it("renders an empty state when the report has no questions", () => {
    render(<QuestionProgression questions={[]} />);
    expect(screen.getByTestId("progression-empty")).toBeInTheDocument();
  });

  it("renders an empty state when questions are missing entirely", () => {
    render(<QuestionProgression />);
    expect(screen.getByTestId("progression-empty")).toBeInTheDocument();
    expect(screen.queryAllByTestId("question-row")).toHaveLength(0);
  });

  it("formats fractional scores to one decimal place", () => {
    render(
      <QuestionProgression
        questions={[{ question_id: "a", difficulty: "medium", score: 7.25 }]}
      />,
    );

    expect(screen.getByTestId("question-score")).toHaveTextContent("Score 7.3");
  });
});
