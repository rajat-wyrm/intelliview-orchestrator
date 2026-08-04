"""
Unit tests: candidate_id path parameter format validation (issue #89).
Patches Redis/Postgres before importing the app, so this runs without
a live database (unlike the other test files in this folder).
"""

from unittest.mock import MagicMock
import redis
redis.from_url = MagicMock(return_value=MagicMock())
redis.Redis = MagicMock(return_value=MagicMock())

try:
    import psycopg2
    psycopg2.connect = MagicMock(return_value=MagicMock())
except ImportError:
    pass

try:
    import sqlalchemy
    sqlalchemy.create_engine = MagicMock(return_value=MagicMock())
except ImportError:
    pass

try:
    import asyncpg
    asyncpg.connect = MagicMock(return_value=MagicMock())
    asyncpg.create_pool = MagicMock(return_value=MagicMock())
except ImportError:
    pass

from fastapi.testclient import TestClient
from orchestrator.main import app

client = TestClient(app)

VALID_ID = "candidate_1a2b3c4d5e6f"


def test_get_candidate_valid_id_format_passes_validation():
    response = client.get(f"/candidates/{VALID_ID}")
    assert response.status_code != 422


def test_get_candidate_path_traversal_rejected():
    response = client.get("/candidates/..%2F..%2Fetc%2Fpasswd")
    # Either outcome is a secure rejection: 422 = our regex caught it,
    # 404 = FastAPI's router refused to match the traversal as a single
    # path segment. Both mean no data leak. We just must NOT get 200.
    assert response.status_code in (404, 422)
    assert response.status_code != 200


def test_get_candidate_short_id_rejected():
    response = client.get("/candidates/candidate_short")
    assert response.status_code == 422


def test_get_candidate_history_valid_id_format_passes_validation():
    response = client.get(f"/candidates/{VALID_ID}/history")
    assert response.status_code != 422


def test_get_candidate_history_invalid_id_rejected():
    response = client.get("/candidates/candidate_short/history")
    assert response.status_code == 422