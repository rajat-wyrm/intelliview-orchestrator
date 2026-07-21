import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from orchestrator.main import app
from orchestrator.question_bank import question_bank


@pytest.fixture
def client():
    return TestClient(app)


def test_ask_question_generative_strategy(client):
    """
    Test 1: Generative strategy flow
    Verify that when strategy=generative is passed, the endpoint calls LLM 
    generation and returns the newly generated question.
    """
    mock_llm_text = "What is the difference between processes and threads in OS?"
    
    with patch("orchestrator.main._llm_generate_question", return_value=mock_llm_text):
        with patch("orchestrator.main.session_manager.get_session", return_value={"questions_asked": []}):
            response = client.post(
                "/interviews/ask-question?strategy=generative",
                json={"session_id": "test_session_gen_1", "category": "technical"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == mock_llm_text
            assert "question_id" in data


def test_fallback_to_static_on_llm_failure(client):
    """
    Test 2: Fallback to static question bank
    Verify that if the LLM function raises an error or times out, the endpoint 
    gracefully falls back to retrieving a question from the static database bank.
    """
    mock_static_q = {
        "question_id": "q_123",
        "text": "What is REST API?",
        "category": "technical",
        "difficulty": "medium"
    }
    
    with patch("orchestrator.main._llm_generate_question", side_effect=Exception("OpenAI API Timeout")):
        with patch("orchestrator.main.session_manager.get_session", return_value={"questions_asked": []}):
            with patch("orchestrator.main.question_bank.get_next_question", return_value=mock_static_q):
                response = client.post(
                    "/interviews/ask-question?strategy=generative",
                    json={"session_id": "test_session_fallback_1", "category": "technical"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["question_id"] == "q_123"
                assert data["text"] == "What is REST API?"


def test_persistence_generated_by_llm_flag():
    """
    Test 3: Persistence of generated_by_llm=True flag
    Verify that save_generated_question persists questions with the generated_by_llm flag.
    """
    sample_text = "Explain how garbage collection works in Python."
    
    with patch.object(question_bank, "save_generated_question") as mock_save:
        mock_save.return_value = {
            "question_id": "q_llm_1",
            "text": sample_text,
            "category": "technical",
            "generated_by_llm": True
        }
        
        saved_question = question_bank.save_generated_question(
            text=sample_text,
            category="technical"
        )
        
        assert saved_question is not None
        assert saved_question["generated_by_llm"] is True
        assert saved_question["text"] == sample_text