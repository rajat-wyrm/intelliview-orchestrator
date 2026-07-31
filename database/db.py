"""Database connection manager for AI Interview Orchestrator.

Centralises SQLAlchemy connection and session management. Use `SessionLocal()`
as a context-manager (or close it manually) and prefer the type-hinted
`with SessionLocal() as db:` pattern in new code.
"""

from __future__ import annotations

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_SSLMODE, DATABASE_URL

logger = logging.getLogger(__name__)

_connect_args = {}
_engine_kwargs = {
    "echo": False,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

if DATABASE_SSLMODE and DATABASE_SSLMODE != "disable":
    _connect_args["sslmode"] = DATABASE_SSLMODE
    _engine_kwargs["connect_args"] = _connect_args
    logger.info("Database SSL enabled: mode=%s", DATABASE_SSLMODE)

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session.

    Ensures failed transactions are rolled back and the session
    is always closed after the request finishes.
    """
    db = SessionLocal()

    try:
        yield db

    except Exception:
        db.rollback()
        logger.exception("Database session failed; transaction rolled back")
        raise

    finally:
        db.close()
