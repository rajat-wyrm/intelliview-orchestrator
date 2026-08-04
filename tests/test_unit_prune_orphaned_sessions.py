"""Unit tests for the orphaned-QUEUED-session pruning task."""

import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("POSTGRES_HOST", "localhost")

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from database.db import Base
from database.models import InterviewSession
from orchestrator.session_manager import SessionManager
from orchestrator.time_utils import utcnow


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _make_session(session_id, status, updated_minutes_ago):
    now = utcnow().replace(tzinfo=None)
    ts = now - timedelta(minutes=updated_minutes_ago)
    return InterviewSession(
        session_id=session_id,
        candidate_id=f"cand-{session_id}",
        status=status,
        created_at=ts,
        updated_at=ts,
    )


def test_prunes_only_queued_sessions_older_than_24h(db_session):
    db_session.add_all(
        [
            _make_session("old_queued", SessionManager.QUEUED, updated_minutes_ago=25 * 60),
            _make_session("fresh_queued", SessionManager.QUEUED, updated_minutes_ago=60),
            _make_session("old_processing", SessionManager.PROCESSING, updated_minutes_ago=25 * 60),
        ]
    )
    db_session.commit()

    import workers.tasks as tasks_module

    tasks_module.SessionLocal = lambda: db_session
    tasks_module.state_sync = MagicMock()

    result = tasks_module.prune_orphaned_queued_sessions()

    assert result["pruned"] == 1
    remaining = {s.session_id for s in db_session.execute(select(InterviewSession)).scalars().all()}
    assert remaining == {"fresh_queued", "old_processing"}
    tasks_module.state_sync.delete_session_state.assert_called_once_with("old_queued")


def test_no_orphaned_sessions_returns_zero(db_session):
    import workers.tasks as tasks_module

    tasks_module.SessionLocal = lambda: db_session
    tasks_module.state_sync = MagicMock()

    assert tasks_module.prune_orphaned_queued_sessions() == {"pruned": 0}