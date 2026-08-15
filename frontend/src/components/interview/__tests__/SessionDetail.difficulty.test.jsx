import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

/**
 * Feature 11.3 — Adaptive Interview Difficulty
 * Aayush — integration-level tests for the session report dialog.
 *
 * SWR is mocked per-endpoint so the dialog can be exercised without a
 * running backend. Existing fields (candidate, risk score, status) are
 * asserted alongside the new progression section to catch regressions.
 */

const swrResponses = new Map();

vi.mock("swr", () => ({
  default: (key) => {
    if (!key) return { data: undefined, error: undefined, isLoading: false, mutate: vi.fn() };
    const data = swrResponses.get(key);
    return { data, error: undefined, isLoading: false, mutate: vi.fn() };
  },
}));

vi.mock("@/lib/store", () => ({
  useAppStore: (selector) => selector({ token: "test-token" }),
}));

// src/hooks/useMomentTracking.js contains JSX but carries a .js extension,
// which the Vitest transform rejects. Stubbing it keeps this suite focused
// on the difficulty progression. Pre-existing issue, not introduced here.
vi.mock("@/hooks/useMomentTracking", () => ({
  MomentTimeline: () => null,
  useMomentTracking: () => ({
    moments: [],
    isTracking: false,
    startTracking: vi.fn(),
    stopTracking: vi.fn(),
    trackEvent: vi.fn(),
  }),
}));

const SessionDetail = (await import("@/components/SessionDetail")).default;

const SESSION_ID = "sess-123";

const sessionStatus = {
  session_id: SESSION_ID,
  status: "COMPLETED",
  candidate_id: "cand-9",
  risk_score: 0.21,
  assigned_node: "worker-1",
};

const report = {
  session_id: SESSION_ID,
  questions: [
    { question_id: "q1", text: "Explain closures", difficulty: "medium", score: 9 },
    { question_id: "q2", text: "Design a rate limiter", difficulty: "hard", score: 7 },
    { question_id: "q3", text: "What is a deadlock", difficulty: "medium", score: 4 },
    { question_id: "q4", text: "Define REST", difficulty: "easy", score: null },
  ],
};

beforeEach(() => {
  swrResponses.clear();
  swrResponses.set(`/session-status/${SESSION_ID}`, sessionStatus);
});

describe("SessionDetail — adaptive difficulty reporting", () => {
  it("renders the difficulty progression section when the report has questions", () => {
    swrResponses.set(`/interviews/${SESSION_ID}/report`, report);

    render(<SessionDetail sessionId={SESSION_ID} onClose={() => {}} />);

    expect(screen.getByText(/Question difficulty progression/i)).toBeInTheDocument();
    expect(screen.getAllByTestId("question-row")).toHaveLength(4);
  });

  it("renders the difficulty transitions in report order", () => {
    swrResponses.set(`/interviews/${SESSION_ID}/report`, report);

    render(<SessionDetail sessionId={SESSION_ID} onClose={() => {}} />);

    const sequence = screen
      .getAllByTestId("question-row")
      .map((row) => row.getAttribute("data-difficulty"));

    expect(sequence).toEqual(["medium", "hard", "medium", "easy"]);
  });

  it("shows the unanswered question with its difficulty and a pending score", () => {
    swrResponses.set(`/interviews/${SESSION_ID}/report`, report);

    render(<SessionDetail sessionId={SESSION_ID} onClose={() => {}} />);

    const rows = screen.getAllByTestId("question-row");
    expect(rows[3]).toHaveTextContent("Easy");
    expect(rows[3]).toHaveTextContent("Pending");
  });

  it("hides the progression section when the report endpoint returns nothing", () => {
    render(<SessionDetail sessionId={SESSION_ID} onClose={() => {}} />);

    expect(screen.queryByText(/Question difficulty progression/i)).toBeNull();
    expect(screen.queryAllByTestId("question-row")).toHaveLength(0);
  });

  it("hides the progression section when the report has an empty question list", () => {
    swrResponses.set(`/interviews/${SESSION_ID}/report`, { questions: [] });

    render(<SessionDetail sessionId={SESSION_ID} onClose={() => {}} />);

    expect(screen.queryByText(/Question difficulty progression/i)).toBeNull();
  });

  it("degrades gracefully when the backend omits per-question difficulty", () => {
    swrResponses.set(`/interviews/${SESSION_ID}/report`, {
      questions: [{ question_id: "q1", text: "Legacy question", score: 6 }],
    });

    render(<SessionDetail sessionId={SESSION_ID} onClose={() => {}} />);

    const row = screen.getByTestId("question-row");
    expect(row.getAttribute("data-difficulty")).toBe("unknown");
    expect(row).toHaveTextContent("Score 6");
  });
});

describe("SessionDetail — existing behaviour is unchanged", () => {
  it("still renders the existing session fields with the new section present", () => {
    swrResponses.set(`/interviews/${SESSION_ID}/report`, report);

    render(<SessionDetail sessionId={SESSION_ID} onClose={() => {}} />);

    expect(screen.getByText("Session detail")).toBeInTheDocument();
    expect(screen.getByText("cand-9")).toBeInTheDocument();
    expect(screen.getByText("worker-1")).toBeInTheDocument();
    expect(screen.getByText("0.210")).toBeInTheDocument();
  });

  it("still renders the existing session fields when no report exists", () => {
    render(<SessionDetail sessionId={SESSION_ID} onClose={() => {}} />);

    expect(screen.getByText("Session detail")).toBeInTheDocument();
    expect(screen.getByText("cand-9")).toBeInTheDocument();
  });

  it("renders nothing when the dialog is closed", () => {
    render(<SessionDetail sessionId={null} onClose={() => {}} />);

    expect(screen.queryByText("Session detail")).toBeNull();
  });
});
