from datetime import datetime
from unittest.mock import MagicMock, patch

with (
    patch("sentence_transformers.SentenceTransformer", return_value=MagicMock()),
    patch("redis.from_url", return_value=MagicMock()),
    patch("sqlalchemy.create_engine", return_value=MagicMock()),
):
    from database.db import get_db
    from database.models import Candidate, InterviewSession
    from orchestrator.main import app

from fastapi.testclient import TestClient

client = TestClient(app)


def test_get_interview_report_success():
    mock_db = MagicMock()

    mock_session = InterviewSession(
        session_id="session_123",
        candidate_id="cand_123",
        start_time=datetime(2023, 1, 1, 10, 0, 0),
        end_time=datetime(2023, 1, 1, 11, 0, 0),
        questions_asked=[{"question_id": "q1", "text": "What is AI?"}],
        answers_provided=[
            {"question_id": "q1", "answer_text": "Artificial Intelligence"}
        ],
        feedback_generated=[{"question_id": "q1", "feedback": "Good", "score": 9.0}],
        evaluation_analysis={
            "quality": 8.0,
            "llm_feedback": {
                "strengths": ["Strong fundamentals"],
                "improvements": ["More detail needed"],
                "recommendation": "progress",
                "detailed_feedback": "Overall good.",
            },
        },
        risk_score=0.1,
    )

    mock_candidate = Candidate(
        candidate_id="cand_123", name="John Doe", email="john@example.com"
    )

    def side_effect(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "interview_sessions" in stmt_str or "interviewsession" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_session
        elif "candidates" in stmt_str or "candidate" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_candidate
        else:
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_db.execute.side_effect = side_effect
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/interviews/session_123/report")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["session_id"] == "session_123"
    assert data["candidate"]["name"] == "John Doe"
    assert data["interview_summary"]["duration_minutes"] == 60.0
    assert len(data["questions"]) == 1
    assert data["questions"][0]["answer"] == "Artificial Intelligence"
    assert data["questions"][0]["feedback"] == "Good"
    assert data["questions"][0]["score"] == 9.0
    assert data["llm_feedback"]["strengths"] == ["Strong fundamentals"]
    assert data["risk_assessment"]["classification"] == "LOW"

    app.dependency_overrides.clear()


def test_get_interview_report_session_not_found():
    mock_db = MagicMock()

    def side_effect(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_db.execute.side_effect = side_effect
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/interviews/invalid_session/report")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"

    app.dependency_overrides.clear()


def test_get_interview_report_candidate_not_found():
    mock_db = MagicMock()

    mock_session = InterviewSession(session_id="session_123", candidate_id="cand_123")

    def side_effect(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "interview_sessions" in stmt_str or "interviewsession" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_session
        else:
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_db.execute.side_effect = side_effect
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/interviews/session_123/report")
    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"

    app.dependency_overrides.clear()


def test_get_interview_report_with_sentiment_analysis():
    mock_db = MagicMock()

    mock_session = InterviewSession(
        session_id="session_sentiment_999",
        candidate_id="cand_999",
        start_time=datetime(2026, 7, 1, 10, 0, 0),
        end_time=datetime(2026, 7, 1, 10, 30, 0),
        questions_asked=[{"question_id": "q1", "text": "Describe your background."}],
        answers_provided=[
            {"question_id": "q1", "answer_text": "I led the backend team."}
        ],
        feedback_generated=[
            {"question_id": "q1", "feedback": "Great leadership.", "score": 9.5}
        ],
        evaluation_analysis={
            "quality": 9.0,
            "llm_feedback": {
                "strengths": ["Leadership", "Architecture"],
                "improvements": [],
                "recommendation": "hire",
                "detailed_feedback": "Excellent candidate.",
            },
        },
        audio_analysis={
            "sentiment": "Confident",
            "sentiment_scores": {"Confident": 0.75, "Neutral": 0.20, "Nervous": 0.05},
            "sentiment_summary": {
                "dominant_sentiment": "Confident",
                "confident_percentage": 75.0,
                "neutral_percentage": 20.0,
                "nervous_percentage": 5.0,
                "summary_text": "Candidate was confident 75% of the time",
            },
            "sentiment_timeline": [
                {
                    "timestamp": 0.0,
                    "start": 0.0,
                    "end": 15.0,
                    "text": "I led the backend team.",
                    "sentiment": "Confident",
                    "confidence": 0.85,
                    "scores": {"Confident": 0.85, "Neutral": 0.10, "Nervous": 0.05},
                }
            ],
        },
        risk_score=0.05,
    )

    mock_candidate = Candidate(
        candidate_id="cand_999", name="Alice Smith", email="alice@example.com"
    )

    def side_effect(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "interview_sessions" in stmt_str or "interviewsession" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_session
        elif "candidates" in stmt_str or "candidate" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_candidate
        else:
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_db.execute.side_effect = side_effect
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/interviews/session_sentiment_999/report")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["session_id"] == "session_sentiment_999"
    assert data["sentiment_analysis"] is not None
    assert data["sentiment_analysis"]["sentiment"] == "Confident"
    assert data["sentiment_analysis"]["scores"]["Confident"] == 0.75
    assert data["sentiment_analysis"]["summary"]["confident_percentage"] == 75.0
    assert (
        data["sentiment_analysis"]["summary"]["summary_text"]
        == "Candidate was confident 75% of the time"
    )
    assert len(data["sentiment_analysis"]["timeline"]) == 1
    assert data["sentiment_analysis"]["timeline"][0]["sentiment"] == "Confident"
    assert data["sentiment_analysis"]["timeline"][0]["start"] == 0.0

    app.dependency_overrides.clear()
