"""
test_api.py — Unit tests for Risk Weight Configuration API
Run: pytest tests/test_api.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from orchestrator.main import app
from orchestrator.store import clear_all

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    """Clear store before each test for isolation."""
    clear_all()
    yield
    clear_all()


# ── Helpers ────────────────────────────────────────────────────────────────────


def make_config(job_position="Software Engineer", weights=None):
    return {
        "job_position": job_position,
        "description": "Test config",
        "weights": weights
        or {
            "tab_switching": 2.0,
            "browser_activity": 3.0,
            "audio_interruptions": 1.0,
            "multiple_persons": 2.0,
            "candidate_absence": 1.5,
            "gaze_deviation": 1.0,
            "background_noise": 0.5,
        },
    }


# ── POST /risk-configs ─────────────────────────────────────────────────────────


class TestCreate:
    def test_create_returns_201(self):
        r = client.post("/risk-configs/", json=make_config())
        assert r.status_code == 201

    def test_create_returns_correct_position(self):
        r = client.post("/risk-configs/", json=make_config("Customer Support"))
        assert r.json()["job_position"] == "Customer Support"

    def test_create_returns_id(self):
        r = client.post("/risk-configs/", json=make_config())
        assert "id" in r.json()
        assert len(r.json()["id"]) > 0

    def test_create_duplicate_position_returns_409(self):
        client.post("/risk-configs/", json=make_config("SWE"))
        r = client.post("/risk-configs/", json=make_config("SWE"))
        assert r.status_code == 409

    def test_create_case_insensitive_duplicate_check(self):
        client.post("/risk-configs/", json=make_config("software engineer"))
        r = client.post("/risk-configs/", json=make_config("Software Engineer"))
        assert r.status_code == 409

    def test_create_empty_position_returns_422(self):
        payload = make_config()
        payload["job_position"] = ""
        r = client.post("/risk-configs/", json=payload)
        assert r.status_code == 422

    def test_create_negative_weight_returns_422(self):
        payload = make_config(
            weights={
                "tab_switching": -1.0,
                "browser_activity": 1.0,
                "audio_interruptions": 1.0,
                "multiple_persons": 1.0,
                "candidate_absence": 1.0,
                "gaze_deviation": 1.0,
                "background_noise": 1.0,
            }
        )
        r = client.post("/risk-configs/", json=payload)
        assert r.status_code == 422

    def test_create_all_zero_weights_returns_422(self):
        payload = make_config(
            weights={
                k: 0.0
                for k in [
                    "tab_switching",
                    "browser_activity",
                    "audio_interruptions",
                    "multiple_persons",
                    "candidate_absence",
                    "gaze_deviation",
                    "background_noise",
                ]
            }
        )
        r = client.post("/risk-configs/", json=payload)
        assert r.status_code == 422

    def test_create_missing_weights_uses_defaults(self):
        payload = {"job_position": "PM Role", "weights": {}}
        r = client.post("/risk-configs/", json=payload)
        # Empty weights {} → all fields default to 1.0 → valid
        assert r.status_code == 201
        assert r.json()["weights"]["tab_switching"] == 1.0


# ── GET /risk-configs ──────────────────────────────────────────────────────────


class TestList:
    def test_list_empty(self):
        r = client.get("/risk-configs/")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_returns_all(self):
        client.post("/risk-configs/", json=make_config("SWE"))
        client.post("/risk-configs/", json=make_config("PM"))
        r = client.get("/risk-configs/")
        assert len(r.json()) == 2


# ── GET /risk-configs/{id} ─────────────────────────────────────────────────────


class TestGetById:
    def test_get_existing(self):
        created = client.post("/risk-configs/", json=make_config()).json()
        r = client.get(f"/risk-configs/{created['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]

    def test_get_nonexistent_returns_404(self):
        r = client.get("/risk-configs/nonexistent-id")
        assert r.status_code == 404


# ── GET /risk-configs/by-position/{job_position} ──────────────────────────────


class TestGetByPosition:
    def test_get_by_position(self):
        client.post("/risk-configs/", json=make_config("Data Scientist"))
        r = client.get("/risk-configs/by-position/Data Scientist")
        assert r.status_code == 200
        assert r.json()["job_position"] == "Data Scientist"

    def test_get_by_position_case_insensitive(self):
        client.post("/risk-configs/", json=make_config("data scientist"))
        r = client.get("/risk-configs/by-position/DATA SCIENTIST")
        assert r.status_code == 200

    def test_get_by_position_not_found_returns_404(self):
        r = client.get("/risk-configs/by-position/Unknown Role")
        assert r.status_code == 404


# ── PUT /risk-configs/{id} ─────────────────────────────────────────────────────


class TestUpdate:
    def test_update_weights(self):
        created = client.post("/risk-configs/", json=make_config()).json()
        r = client.put(
            f"/risk-configs/{created['id']}",
            json={
                "weights": {
                    "tab_switching": 9.0,
                    "browser_activity": 1.0,
                    "audio_interruptions": 1.0,
                    "multiple_persons": 1.0,
                    "candidate_absence": 1.0,
                    "gaze_deviation": 1.0,
                    "background_noise": 1.0,
                }
            },
        )
        assert r.status_code == 200
        assert r.json()["weights"]["tab_switching"] == 9.0

    def test_update_description_only(self):
        created = client.post("/risk-configs/", json=make_config()).json()
        r = client.put(
            f"/risk-configs/{created['id']}", json={"description": "Updated desc"}
        )
        assert r.status_code == 200
        assert r.json()["description"] == "Updated desc"

    def test_update_nonexistent_returns_404(self):
        r = client.put("/risk-configs/bad-id", json={"description": "x"})
        assert r.status_code == 404

    def test_update_preserves_other_fields(self):
        created = client.post("/risk-configs/", json=make_config("DevOps")).json()
        client.put(f"/risk-configs/{created['id']}", json={"description": "new desc"})
        r = client.get(f"/risk-configs/{created['id']}")
        assert r.json()["job_position"] == "DevOps"


# ── DELETE /risk-configs/{id} ──────────────────────────────────────────────────


class TestDelete:
    def test_delete_existing(self):
        created = client.post("/risk-configs/", json=make_config()).json()
        r = client.delete(f"/risk-configs/{created['id']}")
        assert r.status_code == 204

    def test_delete_removes_from_list(self):
        created = client.post("/risk-configs/", json=make_config()).json()
        client.delete(f"/risk-configs/{created['id']}")
        r = client.get("/risk-configs/")
        assert len(r.json()) == 0

    def test_delete_nonexistent_returns_404(self):
        r = client.delete("/risk-configs/bad-id")
        assert r.status_code == 404


# ── Risk Engine Integration ────────────────────────────────────────────────────


class TestRiskEngineIntegration:
    def test_known_position_returns_custom_weights(self):
        client.post("/risk-configs/", json=make_config("QA Engineer"))
        r = client.get("/risk-engine/weights/QA Engineer")
        assert r.status_code == 200
        assert r.json()["is_custom"] == True

    def test_unknown_position_returns_defaults(self):
        r = client.get("/risk-engine/weights/Unknown Position")
        assert r.status_code == 200
        assert r.json()["is_custom"] == False
        assert r.json()["weights"]["tab_switching"] == 1.0

    def test_engine_never_returns_404(self):
        """Risk engine must always return weights — never break existing scoring."""
        r = client.get("/risk-engine/weights/Completely Made Up Role")
        assert r.status_code == 200


# ── GET /questions ─────────────────────────────────────────────────────────────


def test_questions_reject_negative_limit():
    response = client.get("/questions?limit=-1")
    assert response.status_code == 422
