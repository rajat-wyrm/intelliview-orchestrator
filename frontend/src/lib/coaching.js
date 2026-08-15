/**
 * Coaching data helpers.
 *
 * The coaching portal currently sources its content from the existing
 * `GET /interviews/{session_id}/report` endpoint (see
 * docs/interview_report_api.md) rather than a dedicated coaching endpoint,
 * so we don't have to introduce new backend surface area to ship the
 * frontend experience.
 *
 * normalizeCoachingData() is the single seam between "whatever the report
 * API returns today" and "what the coaching UI renders". If/when a
 * purpose-built coaching response lands (tracked with Harsha for the API
 * shape, Satvika for the AI-generated coaching content), only this
 * function — and its accompanying unit tests — should need to change.
 */

function normalizeCoachingData(report) {
  if (!report) return null;

  const llm = report.llm_feedback ?? null;
  const overall = report.overall_evaluation ?? null;
  const risk = report.risk_assessment ?? null;

  const strengths = Array.isArray(llm?.strengths) ? llm.strengths : [];
  const improvements = Array.isArray(llm?.improvements) ? llm.improvements : [];

  const questions = Array.isArray(report.questions)
    ? report.questions.map((q) => ({
        id: q.question_id,
        text: q.text ?? "",
        answer: q.answer ?? null,
        score: typeof q.score === "number" ? q.score : null,
        feedback: q.feedback ?? null,
        // Optional / forward-compatible fields — not part of the documented
        // report shape yet, but rendered if a future payload includes them.
        sampleAnswer: q.sample_answer ?? q.improved_answer ?? q.model_answer ?? null,
      }))
    : [];

  const hasCoachingContent =
    strengths.length > 0 ||
    improvements.length > 0 ||
    Boolean(llm?.detailed_feedback) ||
    Boolean(overall) ||
    questions.length > 0;

  return {
    sessionId: report.session_id ?? null,
    candidate: report.candidate ?? null,
    summary: report.interview_summary ?? null,
    overall,
    risk,
    strengths,
    improvements,
    recommendation: llm?.recommendation ?? null,
    detailedFeedback: llm?.detailed_feedback ?? null,
    questions,
    hasCoachingContent,
  };
}

/**
 * Builds a { label, score } series (oldest → newest) of a candidate's past
 * completed sessions with a recorded overall_score, for the "performance
 * over time" trend. Returns an empty array if there isn't enough history
 * to plot (fewer than 2 scored sessions).
 */
function buildScoreTrend(history) {
  if (!Array.isArray(history)) return [];

  const scored = history
    .filter((h) => typeof h.overall_score === "number")
    .sort((a, b) => new Date(a.created_at ?? 0) - new Date(b.created_at ?? 0));

  if (scored.length < 2) return [];

  return scored.map((h) => ({
    sessionId: h.session_id,
    date: h.created_at ?? null,
    score: h.overall_score,
  }));
}

export { normalizeCoachingData, buildScoreTrend };