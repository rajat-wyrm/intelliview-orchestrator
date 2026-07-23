# Interview Report API

## `GET /interviews/{session_id}/report`

Retrieves a comprehensive final report for a given interview session. It aggregates questions asked, candidate answers, and LLM-generated feedback into a structured format.

> [!NOTE]
> This endpoint is primarily intended for **completed** interview sessions. While it handles incomplete sessions gracefully (by returning `null` or empty arrays for missing data), the evaluation analysis and comprehensive feedback are only generated after the interview concludes.

### Response

Returns an `InterviewReportResponse` JSON object with the following structure:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "candidate": {
    "candidate_id": "c12345",
    "name": "Jane Doe",
    "email": "jane.doe@example.com"
  },
  "interview_summary": {
    "start_time": "2026-07-09T14:00:00Z",
    "end_time": "2026-07-09T15:00:00Z",
    "duration_minutes": 60.0
  },
  "questions": [
    {
      "question_id": "q1",
      "text": "Can you explain the difference between a process and a thread?",
      "answer": "A process has its own memory space...",
      "score": 8.5,
      "feedback": "Good explanation, but missed addressing context switching overhead."
    }
  ],
  "overall_evaluation": {
    "quality": 8.0,
    "accuracy": 8.5,
    "clarity": 7.5
  },
  "llm_feedback": {
    "strengths": ["Strong foundational knowledge", "Clear communication"],
    "improvements": ["Needs to elaborate more on edge cases"],
    "recommendation": "progress",
    "detailed_feedback": "Jane performed well overall..."
  },
  "risk_assessment": {
    "score": 0.15,
    "classification": "LOW",
    "factors": ["Slight hesitation on advanced topics"]
  },
  "metadata": {
    "token_usage": null,
    "estimated_cost_usd": null
  }
}
```

### Note
- If the token/cost feature (Issue Feature #3) is not yet merged, `token_usage` and `estimated_cost_usd` under `metadata` will be `null`.
