import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Configure settings before importing app components to use test DB
from app.config import settings
settings.DB_PATH = ":memory:"  # Use in-memory database for tests

from app.main import app
from app.evaluator import evaluate_answer, detect_domain, clean_and_tokenize
from app.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure in-memory database schema is initialized before every test."""
    init_db()

# --- Unit Tests for Helpers ---

def test_clean_and_tokenize():
    text = "What is a Binary Search Tree (BST)?"
    tokens = clean_and_tokenize(text)
    # Binary, Search, Tree, BST should be in there. Stop words like what, is, a should be filtered.
    assert "binary" in tokens
    assert "search" in tokens
    assert "tree" in tokens
    assert "bst" in tokens
    assert "what" not in tokens
    assert "is" not in tokens

def test_detect_domain():
    assert detect_domain("Explain what is a primary key and indexes in SQL database") == "dbms"
    assert detect_domain("How does paging and virtual memory work in OS?") == "os"
    assert detect_domain("What is the time complexity of quicksort algorithm?") == "dsa"
    # Fallback default
    assert detect_domain("Random sentence without technical terms") == "dsa"


# --- Unit Tests for Evaluation Engine ---

def test_evaluate_empty_answer():
    result = evaluate_answer(
        question="What is a process?",
        answer="   "
    )
    assert result["score"] == 0.0
    assert "empty" in result["feedback"].lower()
    assert result["confidence"] == 1.0

def test_evaluate_irrelevant_answer():
    # Question is about DBMS, answer is about cooking
    result = evaluate_answer(
        question="What is a primary key?",
        answer="First, boil some water, then add spaghetti and cook for 10 minutes."
    )
    assert result["score"] == 0.0
    assert "irrelevant" in result["feedback"].lower()
    assert result["confidence"] == 1.0

@patch("app.evaluator.settings")
def test_evaluate_extremely_short_answer(mock_settings):
    # Mock settings to have no API keys and provide appropriate DOMAIN_KEYWORDS
    mock_settings.GEMINI_API_KEY = ""
    mock_settings.OPENAI_API_KEY = ""
    mock_settings.DB_PATH = ":memory:"
    mock_settings.DOMAIN_KEYWORDS = {
        "dsa": {"binary", "search", "tree", "bst"}
    }
    result = evaluate_answer(
        question="What is a binary search tree?",
        answer="it is a tree"
    )
    assert result["score"] <= 3.0
    assert "brief" in result["feedback"].lower()
    assert result["confidence"] == 0.45


# --- Mocked LLM Tests ---

@patch("app.evaluator.call_openai")
@patch("app.evaluator.settings")
def test_evaluate_llm_openai_success(mock_settings, mock_call_openai):
    # Setup config to simulate OpenAI activation
    mock_settings.LLM_PROVIDER = "openai"
    mock_settings.OPENAI_API_KEY = "mock_key"
    mock_settings.DB_PATH = ":memory:"
    mock_settings.DOMAIN_KEYWORDS = {
        "dsa": {"binary", "search", "tree", "bst"}
    }
    
    mock_call_openai.return_value = {
        "score": 8.5,
        "feedback": "Great explanation of BST structure, but missing balancing details.",
        "confidence": 0.9
    }
    
    result = evaluate_answer(
        question="What is a binary search tree?",
        answer="A binary search tree is a binary tree where left child is smaller and right is larger.",
        domain="dsa"
    )
    
    assert result["score"] == 8.5
    assert "BST structure" in result["feedback"]
    assert result["confidence"] == 0.9
    mock_call_openai.assert_called_once()

@patch("app.evaluator.call_gemini")
@patch("app.evaluator.settings")
def test_evaluate_llm_gemini_success(mock_settings, mock_call_gemini):
    # Setup config to simulate Gemini activation
    mock_settings.LLM_PROVIDER = "gemini"
    mock_settings.GEMINI_API_KEY = "mock_key"
    mock_settings.DB_PATH = ":memory:"
    mock_settings.DOMAIN_KEYWORDS = {
        "os": {"virtual", "memory", "paging"}
    }
    
    mock_call_gemini.return_value = {
        "score": 9.2,
        "feedback": "Excellent breakdown of virtual memory mapping.",
        "confidence": 0.95
    }
    
    result = evaluate_answer(
        question="What is virtual memory?",
        answer="Virtual memory maps logical addresses to physical frame pages.",
        domain="os"
    )
    
    assert result["score"] == 9.2
    assert "virtual memory mapping" in result["feedback"]
    assert result["confidence"] == 0.95
    mock_call_gemini.assert_called_once()

@patch("app.evaluator.call_openai")
@patch("app.evaluator.settings")
def test_evaluate_llm_failure_degrades_gracefully(mock_settings, mock_call_openai):
    # If the API key is present but call throws an error or fails
    mock_settings.LLM_PROVIDER = "openai"
    mock_settings.OPENAI_API_KEY = "mock_key"
    mock_settings.DB_PATH = ":memory:"
    mock_settings.DOMAIN_KEYWORDS = {
        "dbms": {"primary", "key", "unique", "null"}
    }
    
    # Simulate API failure returning None
    mock_call_openai.return_value = None
    
    result = evaluate_answer(
        question="What is a primary key?",
        answer="A primary key uniquely identifies rows and cannot be null.",
        domain="dbms"
    )
    
    # Check that it degraded to rule-based evaluation (confidence is 0.45)
    assert result["confidence"] == 0.45
    assert "keyword match" in result["feedback"].lower()
    assert result["score"] > 0.0


# --- Integration/API Endpoint Tests ---

def test_api_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_api_evaluate_empty_answer():
    payload = {
        "question": "What is virtual memory?",
        "answer": ""
    }
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 0.0
    assert data["confidence"] == 1.0
    assert "empty" in data["feedback"].lower()

@patch("app.evaluator.settings")
def test_api_evaluate_valid_answer_fallback(mock_settings):
    # Mock settings to have no API keys and provide appropriate DOMAIN_KEYWORDS
    mock_settings.GEMINI_API_KEY = ""
    mock_settings.OPENAI_API_KEY = ""
    mock_settings.DB_PATH = ":memory:"
    mock_settings.DOMAIN_KEYWORDS = {
        "dbms": {"primary", "key", "unique", "null", "column", "row", "table"}
    }
    payload = {
        "question": "What is a primary key in database tables?",
        "answer": "A primary key is a column that uniquely identifies a row in a table.",
        "domain": "dbms"
    }
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Should get a positive score through the rule-based checker
    assert data["score"] > 0.0
    assert data["confidence"] == 0.45
    assert "rule-based" in data["feedback"]
