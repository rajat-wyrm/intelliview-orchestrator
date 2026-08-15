import { describe, it, expect } from "vitest";
import { normalizeCoachingData, buildScoreTrend } from "../coaching";

describe("normalizeCoachingData", () => {
  it("returns null when report is missing", () => {
    expect(normalizeCoachingData(null)).toBeNull();
    expect(normalizeCoachingData(undefined)).toBeNull();
  });

  it("maps a full report into coaching shape", () => {
    const report = {
      session_id: "sess-1",
      candidate: { candidate_id: "cand-1", name: "Ada Lovelace" },
      interview_summary: { start_time: "2026-08-01T10:00:00Z", duration_minutes: 32 },
      overall_evaluation: { quality: 8.2, accuracy: 7.5, clarity: 9.0 },
      risk_assessment: { classification: "low", score: 0.12 },
      llm_feedback: {
        strengths: ["Clear structure", "Strong examples"],
        improvements: ["Speak slower"],
        recommendation: "progress",
        detailed_feedback: "Solid overall performance.",
      },
      questions: [
        {
          question_id: "q1",
          text: "Tell me about yourself",
          answer: "I am a developer",
          score: 8,
          feedback: "Good answer",
          sample_answer: "A more concise sample answer",
        },
      ],
    };

    const result = normalizeCoachingData(report);

    expect(result.sessionId).toBe("sess-1");
    expect(result.candidate).toEqual(report.candidate);
    expect(result.strengths).toEqual(["Clear structure", "Strong examples"]);
    expect(result.improvements).toEqual(["Speak slower"]);
    expect(result.recommendation).toBe("progress");
    expect(result.detailedFeedback).toBe("Solid overall performance.");
    expect(result.questions).toHaveLength(1);
    expect(result.questions[0].sampleAnswer).toBe("A more concise sample answer");
    expect(result.hasCoachingContent).toBe(true);
  });

  it("falls back to improved_answer/model_answer when sample_answer is absent", () => {
    const report = {
      session_id: "sess-2",
      questions: [
        { question_id: "q1", text: "Q1", improved_answer: "improved" },
        { question_id: "q2", text: "Q2", model_answer: "model" },
        { question_id: "q3", text: "Q3" },
      ],
    };

    const result = normalizeCoachingData(report);
    expect(result.questions[0].sampleAnswer).toBe("improved");
    expect(result.questions[1].sampleAnswer).toBe("model");
    expect(result.questions[2].sampleAnswer).toBeNull();
  });

  it("marks hasCoachingContent false for a report with no usable coaching fields", () => {
    const report = { session_id: "sess-3", candidate: { candidate_id: "c1" } };
    const result = normalizeCoachingData(report);

    expect(result.hasCoachingContent).toBe(false);
    expect(result.strengths).toEqual([]);
    expect(result.improvements).toEqual([]);
    expect(result.questions).toEqual([]);
  });

  it("does not throw when llm_feedback fields are missing/malformed", () => {
    const report = {
      session_id: "sess-4",
      llm_feedback: { strengths: null, improvements: "not-an-array" },
    };
    const result = normalizeCoachingData(report);

    expect(result.strengths).toEqual([]);
    expect(result.improvements).toEqual([]);
  });
});

describe("buildScoreTrend", () => {
  it("returns an empty array for non-array input", () => {
    expect(buildScoreTrend(null)).toEqual([]);
    expect(buildScoreTrend(undefined)).toEqual([]);
  });

  it("returns an empty array when fewer than 2 scored sessions exist", () => {
    expect(buildScoreTrend([])).toEqual([]);
    expect(
      buildScoreTrend([{ session_id: "s1", overall_score: 7, created_at: "2026-01-01" }])
    ).toEqual([]);
  });

  it("ignores sessions without a numeric overall_score", () => {
    const history = [
      { session_id: "s1", overall_score: 6, created_at: "2026-01-01" },
      { session_id: "s2", overall_score: null, created_at: "2026-02-01" },
      { session_id: "s3", overall_score: 8, created_at: "2026-03-01" },
    ];
    const trend = buildScoreTrend(history);
    expect(trend.map((t) => t.sessionId)).toEqual(["s1", "s3"]);
  });

  it("sorts chronologically oldest to newest", () => {
    const history = [
      { session_id: "s2", overall_score: 8, created_at: "2026-03-01" },
      { session_id: "s1", overall_score: 6, created_at: "2026-01-01" },
    ];
    const trend = buildScoreTrend(history);
    expect(trend.map((t) => t.sessionId)).toEqual(["s1", "s2"]);
    expect(trend.map((t) => t.score)).toEqual([6, 8]);
  });
});