from unittest.mock import MagicMock, patch

import pytest

from database.db import get_db


def test_get_db_closes_session():
    """Database session should always be closed after successful use."""
    mock_db = MagicMock()

    with patch("database.db.SessionLocal", return_value=mock_db):
        dependency = get_db()

        session = next(dependency)
        assert session is mock_db

        with pytest.raises(StopIteration):
            next(dependency)

    mock_db.close.assert_called_once()
    mock_db.rollback.assert_not_called()


def test_get_db_rolls_back_and_closes_on_exception():
    """Failed database operations should rollback and close the session."""
    mock_db = MagicMock()

    with patch("database.db.SessionLocal", return_value=mock_db):
        dependency = get_db()

        session = next(dependency)
        assert session is mock_db

        with pytest.raises(RuntimeError, match="database failure"):
            dependency.throw(RuntimeError("database failure"))

    mock_db.rollback.assert_called_once()
    mock_db.close.assert_called_once()
