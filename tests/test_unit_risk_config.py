import os
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db import Base
from database.models import RiskConfiguration
from workers.risk_engine import (
    RISK_CONFIG,
    RiskConfigManager,
    RiskScoringEngine,
    seed_default_configs,
)


@pytest.fixture(autouse=True)
def clean_config_cache():
    """Ensure config cache is cleared before and after each test."""
    RiskConfigManager.clear_cache()
    yield
    RiskConfigManager.clear_cache()
    RiskConfigManager.set_ttl(10.0)


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database with schema created."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    yield TestingSessionLocal
    engine.dispose()


def test_fallback_to_defaults():
    """Test that when DB is down/empty, fallback values are returned."""
    # Ensure no environment variables interfere
    with patch.dict(os.environ, {}, clear=True):
        # Patch SessionLocal to fail/be empty
        with patch("workers.risk_engine.SessionLocal", side_effect=Exception("DB Down")):
            assert RiskScoringEngine.VIDEO_WEIGHT == 0.4
            assert RiskScoringEngine.AUDIO_WEIGHT == 0.3
            assert RiskScoringEngine.VIDEO_FACTORS["phone_detected"] == 0.25
            assert RISK_CONFIG["video_weight"] == 0.4


def test_fallback_to_environment():
    """Test that environment variables override fallback defaults when DB is down/empty."""
    env_overrides = {
        "RISK_VIDEO_WEIGHT": "0.75",
        "RISK_VIDEO_PHONE_DETECTED": "0.99",
    }
    with patch.dict(os.environ, env_overrides):
        with patch("workers.risk_engine.SessionLocal", side_effect=Exception("DB Down")):
            assert RiskScoringEngine.VIDEO_WEIGHT == 0.75
            assert RiskScoringEngine.VIDEO_FACTORS["phone_detected"] == 0.99
            assert RISK_CONFIG["video_weight"] == 0.75


def test_database_values_override(test_db):
    """Test that values in the database override both defaults and environment variables."""
    # Seed custom values in test DB
    session = test_db()
    session.add(RiskConfiguration(key="video_weight", value=0.9))
    session.add(RiskConfiguration(key="video_phone_detected", value=0.88))
    session.commit()
    session.close()

    env_overrides = {
        "RISK_VIDEO_WEIGHT": "0.75",
        "RISK_VIDEO_PHONE_DETECTED": "0.99",
    }

    with patch.dict(os.environ, env_overrides):
        with patch("workers.risk_engine.SessionLocal", test_db):
            assert RiskScoringEngine.VIDEO_WEIGHT == 0.9
            assert RiskScoringEngine.VIDEO_FACTORS["phone_detected"] == 0.88
            assert RISK_CONFIG["video_weight"] == 0.9


def test_cache_ttl(test_db):
    """Test that TTL cache prevents querying the database on every access."""
    RiskConfigManager.set_ttl(2.0)  # 2 seconds TTL

    # 1. Query with first set of DB values
    session = test_db()
    session.add(RiskConfiguration(key="video_weight", value=0.1))
    session.commit()

    mock_session_local = MagicMock(side_effect=test_db)
    with patch("workers.risk_engine.SessionLocal", mock_session_local):
        # Access value - triggers initial fetch
        assert RiskScoringEngine.VIDEO_WEIGHT == 0.1
        first_call_count = mock_session_local.call_count
        assert first_call_count == 1

        # Modify value in database directly
        session.query(RiskConfiguration).filter_by(key="video_weight").update({"value": 0.2})
        session.commit()

        # Access value again - should hit cache, NOT database
        assert RiskScoringEngine.VIDEO_WEIGHT == 0.1
        assert mock_session_local.call_count == first_call_count

        # Clear cache manually - should fetch new value
        RiskConfigManager.clear_cache()
        assert RiskScoringEngine.VIDEO_WEIGHT == 0.2
        assert mock_session_local.call_count == first_call_count + 1

    session.close()


def test_seed_default_configs(test_db):
    """Test that seed_default_configs seeds only when empty and respects environment variables."""
    session = test_db()
    # Confirm it's empty
    assert session.query(RiskConfiguration).count() == 0

    # Seed
    env_overrides = {"RISK_VIDEO_WEIGHT": "0.55"}
    with patch.dict(os.environ, env_overrides):
        seed_default_configs(session)

    # Verify seeded values
    db_val = session.query(RiskConfiguration).filter_by(key="video_weight").first()
    assert db_val is not None
    assert db_val.value == 0.55

    db_val_phone = session.query(RiskConfiguration).filter_by(key="video_phone_detected").first()
    assert db_val_phone is not None
    assert db_val_phone.value == 0.25

    # Run seed_default_configs again, ensure it does not overwrite or double insert (idempotency)
    # Change env override to see if it updates
    env_overrides_2 = {"RISK_VIDEO_WEIGHT": "0.99"}
    with patch.dict(os.environ, env_overrides_2):
        seed_default_configs(session)

    db_val_after = session.query(RiskConfiguration).filter_by(key="video_weight").first()
    assert db_val_after.value == 0.55  # Remains unchanged because it was already seeded

    session.close()


def test_invalid_db_value_type(test_db):
    """Test that invalid value types (e.g. non-numeric strings where floats expected) fall back safely."""
    session = test_db()
    # Insert a non-float value for video_weight in DB
    session.add(RiskConfiguration(key="video_weight", value="not-a-float"))
    session.commit()
    session.close()

    with patch("workers.risk_engine.SessionLocal", test_db):
        assert RiskScoringEngine.VIDEO_WEIGHT == "not-a-float"
