"""
Shared base utilities for SQLAlchemy ORM models.
"""

from datetime import datetime, timezone

from database.db import Base

__all__ = ["Base", "utcnow"]


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
