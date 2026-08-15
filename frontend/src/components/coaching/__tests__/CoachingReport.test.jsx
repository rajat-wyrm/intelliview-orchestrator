import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import useSWR from "swr";
import CoachingReport from "../CoachingReport";
import { useAppStore } from "@/lib/store";

vi.mock("swr");
vi.mock("@/lib/store", () => ({
  useAppStore: vi.fn(),
}));

const SESSION_ID = "sess-123";

function mockAuthed() {
  useAppStore.mockImplementation((selector) => selector({ token: "test-token" }));
}

const FULL_REPORT = {
  session_id: SESSION_ID,
  candidate: { candidate_id: "cand-1", name: "Ada Lovelace" },
  interview_summary: { start_time: "2026-08-01T10:00:00Z", duration_minutes: 32 },
  overall_evaluation: { quality: 8.2, accuracy: 7.5, clarity: 9.0 },
  risk_assessment: { classification: "low", score: 0.1 },
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

// Configures the mocked useSWR to respond per-key so we can control the
// report fetch and the candidate history fetch independently.
function mockSwrResponses(responses) {
  useSWR.mockImplementation((key) => {
    if (!key) return { data: undefined, error: undefined, isLoading: false, mutate: vi.fn() };
    for (const [match, value] of responses) {
      if (key.includes(match)) {
        return {
          data: value.data,
          error: value.error,
          isLoading: value.isLoading ?? false,
          mutate: value.mutate ?? vi.fn(),
        };
      }
    }
    return { data: undefined, error: undefined, isLoading: false, mutate: vi.fn() };
  });
}

describe("CoachingReport", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockAuthed();
  });

  it("renders a prompt to select a session when sessionId is missing", () => {
    mockSwrResponses([]);
    render(<CoachingReport sessionId={null} />);

    expect(screen.getByTestId("coaching-missing-session")).toBeInTheDocument();
    expect(screen.getByText(/no session selected/i)).toBeInTheDocument();
  });

  it("shows a loading state while the report is being fetched", () => {
    mockSwrResponses([["/report", { data: undefined, isLoading: true }]]);
    render(<CoachingReport sessionId={SESSION_ID} />);

    expect(screen.getByTestId("coaching-loading")).toBeInTheDocument();
  });

  it("shows an error state when the report fails to load, and retry calls mutate", () => {
    const mutate = vi.fn();
    mockSwrResponses([
      ["/report", { data: undefined, error: new Error("Network error"), mutate }],
    ]);
    render(<CoachingReport sessionId={SESSION_ID} />);

    expect(screen.getByTestId("coaching-error")).toBeInTheDocument();
    expect(screen.getByText(/network error/i)).toBeInTheDocument();
  });

  it("shows an empty state when the report has no usable coaching content", () => {
    mockSwrResponses([
      ["/report", { data: { session_id: SESSION_ID, candidate: { candidate_id: "c1" } } }],
    ]);
    render(<CoachingReport sessionId={SESSION_ID} />);

    expect(screen.getByTestId("coaching-empty")).toBeInTheDocument();
    expect(screen.getByText(/coaching feedback isn't available yet/i)).toBeInTheDocument();
  });

  it("gracefully handles missing/partial fields without crashing", () => {
    mockSwrResponses([
      [
        "/report",
        {
          data: {
            session_id: SESSION_ID,
            candidate: { candidate_id: "c1" },
            llm_feedback: { detailed_feedback: "Keep practicing." },
          },
        },
      ],
    ]);
    render(<CoachingReport sessionId={SESSION_ID} />);

    expect(screen.getByTestId("coaching-report")).toBeInTheDocument();
    expect(screen.getByTestId("coaching-feedback")).toBeInTheDocument();
    expect(screen.getByText("Keep practicing.")).toBeInTheDocument();
    // Sections with no data should not render
    expect(screen.queryByTestId("coaching-questions")).not.toBeInTheDocument();
    expect(screen.queryByTestId("coaching-history")).not.toBeInTheDocument();
  });

  it("renders all coaching sections for a full, successful report", () => {
    mockSwrResponses([
      ["/report", { data: FULL_REPORT }],
      [
        "/history",
        {
          data: {
            history: [
              { session_id: "s1", overall_score: 6, created_at: "2026-06-01" },
              { session_id: "s2", overall_score: 8, created_at: "2026-07-01" },
            ],
          },
        },
      ],
    ]);
    render(<CoachingReport sessionId={SESSION_ID} />);

    expect(screen.getByTestId("coaching-report")).toBeInTheDocument();
    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByTestId("coaching-strengths")).toBeInTheDocument();
    expect(screen.getByText("Clear structure")).toBeInTheDocument();
    expect(screen.getByTestId("coaching-weaknesses")).toBeInTheDocument();
    expect(screen.getByText("Speak slower")).toBeInTheDocument();
    expect(screen.getByTestId("coaching-feedback")).toBeInTheDocument();
    expect(screen.getByText("Solid overall performance.")).toBeInTheDocument();
    expect(screen.getByTestId("coaching-questions")).toBeInTheDocument();
    expect(screen.getByText("Tell me about yourself")).toBeInTheDocument();
    expect(screen.getByText(/a more concise sample answer/i)).toBeInTheDocument();
    expect(screen.getByTestId("coaching-history")).toBeInTheDocument();
  });

  it("does not render the performance-over-time section with fewer than 2 scored sessions", () => {
    mockSwrResponses([
      ["/report", { data: FULL_REPORT }],
      ["/history", { data: { history: [{ session_id: "s1", overall_score: 6 }] } }],
    ]);
    render(<CoachingReport sessionId={SESSION_ID} />);

    expect(screen.queryByTestId("coaching-history")).not.toBeInTheDocument();
  });
});