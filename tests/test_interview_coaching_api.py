from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from database.db import get_db
from database.models import InterviewSession
from orchestrator.main import app

client = TestClient(app)


def test_get_interview_coaching_success():
    mock_db = MagicMock()

    mock_session = InterviewSession(
        session_id="session_123",
        candidate_id="cand_123",
        overall_score=9.0,
        questions_asked=[
            {
                "question_id": "q1",
                "text": "What is AI?",
            }
        ],
        answers_provided=[
            {
                "question_id": "q1",
                "answer_text": "Artificial Intelligence",
            }
        ],
        feedback_generated=[
            {
                "question_id": "q1",
                "feedback": "Good answer",
                "score": 9.0,
            }
        ],
        evaluation_analysis={
            "llm_feedback": {
                "strengths": ["Strong fundamentals"],
                "improvements": ["Add more examples"],
                "recommendation": "progress",
                "detailed_feedback": "Overall good performance.",
            }
        },
    )

    def side_effect(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        return mock_result

    mock_db.execute.side_effect = side_effect
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/interviews/session_123/coaching")

        assert response.status_code == 200, response.text

        data = response.json()

        assert data["session_id"] == "session_123"
        assert data["candidate_id"] == "cand_123"
        assert data["overall_score"] == 9.0

        assert data["strengths"] == ["Strong fundamentals"]

        assert data["focus_areas"] == ["Add more examples"]

        assert data["recommendation"] == "progress"

        assert data["detailed_feedback"] == ("Overall good performance.")

        assert len(data["question_feedback"]) == 1

        question = data["question_feedback"][0]

        assert question["question_id"] == "q1"
        assert question["question"] == "What is AI?"
        assert question["answer"] == "Artificial Intelligence"
        assert question["score"] == 9.0
        assert question["feedback"] == "Good answer"

        assert data["action_items"] == []

    finally:
        app.dependency_overrides.clear()


def test_get_interview_coaching_session_not_found():
    mock_db = MagicMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/interviews/invalid_session/coaching")

        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"

    finally:
        app.dependency_overrides.clear()


def test_get_interview_coaching_missing_data():
    mock_db = MagicMock()

    mock_session = InterviewSession(
        session_id="session_123",
        candidate_id="cand_123",
        overall_score=None,
        questions_asked=[],
        answers_provided=[],
        feedback_generated=[],
        evaluation_analysis={},
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_session

    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/interviews/session_123/coaching")

        assert response.status_code == 200

        data = response.json()

        assert data["session_id"] == "session_123"
        assert data["candidate_id"] == "cand_123"
        assert data["overall_score"] is None
        assert data["strengths"] == []
        assert data["focus_areas"] == []
        assert data["action_items"] == []
        assert data["question_feedback"] == []
        assert data["recommendation"] is None
        assert data["detailed_feedback"] is None

    finally:
        app.dependency_overrides.clear()
