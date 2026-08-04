"""
SQLite persistence layer for evaluation logs.

Uses Python's built-in sqlite3 module — zero additional dependencies.
"""

import sqlite3
import threading
from datetime import datetime
from typing import Optional
from app.config import settings

# Thread-local storage for connections (SQLite connections are not thread-safe)
_local = threading.local()


def _get_connection() -> sqlite3.Connection:
    """Get a thread-local database connection."""
    if not hasattr(_local, "connection") or _local.connection is None:
        _local.connection = sqlite3.connect(settings.DB_PATH)
        _local.connection.row_factory = sqlite3.Row
        _local.connection.execute("PRAGMA journal_mode=WAL")
        _local.connection.execute("PRAGMA foreign_keys=ON")
    return _local.connection


def init_db():
    """Initialize the database schema. Safe to call multiple times."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            domain TEXT NOT NULL,
            score REAL NOT NULL,
            feedback TEXT NOT NULL,
            confidence REAL NOT NULL,
            evaluation_method TEXT NOT NULL DEFAULT 'rule_based',
            llm_provider TEXT
        )
    """)
    # Create indexes for common queries
    conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON evaluation_logs(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_domain ON evaluation_logs(domain)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_score ON evaluation_logs(score)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_method ON evaluation_logs(evaluation_method)")
    conn.commit()


def log_evaluation(
    question: str,
    answer: str,
    domain: str,
    score: float,
    feedback: str,
    confidence: float,
    evaluation_method: str = "rule_based",
    llm_provider: Optional[str] = None
) -> int:
    """
    Insert an evaluation record into the database.
    Returns the ID of the new row.
    """
    conn = _get_connection()
    cursor = conn.execute(
        """
        INSERT INTO evaluation_logs 
            (timestamp, question, answer, domain, score, feedback, confidence, evaluation_method, llm_provider)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat() + "Z",
            question,
            answer,
            domain,
            score,
            feedback,
            confidence,
            evaluation_method,
            llm_provider,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_log_by_id(log_id: int) -> Optional[dict]:
    """Retrieve a single evaluation log by its ID."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM evaluation_logs WHERE id = ?", (log_id,)).fetchone()
    return dict(row) if row else None


def get_logs(
    page: int = 1,
    page_size: int = 20,
    domain: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    evaluation_method: Optional[str] = None,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
) -> dict:
    """
    Retrieve paginated evaluation logs with optional filters.
    
    Returns: { "logs": [...], "total": int, "page": int, "page_size": int, "total_pages": int }
    """
    conn = _get_connection()
    
    where_clauses = []
    params = []

    if domain:
        where_clauses.append("domain = ?")
        params.append(domain.lower())
    if min_score is not None:
        where_clauses.append("score >= ?")
        params.append(min_score)
    if max_score is not None:
        where_clauses.append("score <= ?")
        params.append(max_score)
    if start_date:
        where_clauses.append("timestamp >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("timestamp <= ?")
        params.append(end_date)
    if evaluation_method:
        where_clauses.append("evaluation_method = ?")
        params.append(evaluation_method)
    if search:
        where_clauses.append("(question LIKE ? OR answer LIKE ? OR feedback LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])

    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = "WHERE " + where_sql

    # Validate sort column to prevent SQL injection
    allowed_sort = {"timestamp", "score", "confidence", "domain", "evaluation_method", "id"}
    if sort_by not in allowed_sort:
        sort_by = "timestamp"
    sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

    # Count total matching
    count_sql = f"SELECT COUNT(*) FROM evaluation_logs {where_sql}"
    total = conn.execute(count_sql, params).fetchone()[0]

    # Fetch page
    offset = (page - 1) * page_size
    data_sql = f"SELECT * FROM evaluation_logs {where_sql} ORDER BY {sort_by} {sort_dir} LIMIT ? OFFSET ?"
    rows = conn.execute(data_sql, params + [page_size, offset]).fetchall()

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "logs": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_summary_stats() -> dict:
    """
    Compute aggregate statistics for the dashboard KPI cards and charts.
    """
    conn = _get_connection()

    total = conn.execute("SELECT COUNT(*) FROM evaluation_logs").fetchone()[0]
    
    if total == 0:
        return {
            "total_evaluations": 0,
            "avg_score": 0.0,
            "avg_confidence": 0.0,
            "method_breakdown": {"llm": 0, "rule_based": 0},
            "domain_breakdown": {},
            "score_distribution": [0] * 10,
            "recent_trend": [],
        }

    avg_score = conn.execute("SELECT AVG(score) FROM evaluation_logs").fetchone()[0] or 0.0
    avg_confidence = conn.execute("SELECT AVG(confidence) FROM evaluation_logs").fetchone()[0] or 0.0

    # Method breakdown
    method_rows = conn.execute(
        "SELECT evaluation_method, COUNT(*) as cnt FROM evaluation_logs GROUP BY evaluation_method"
    ).fetchall()
    method_breakdown = {row["evaluation_method"]: row["cnt"] for row in method_rows}

    # Domain breakdown
    domain_rows = conn.execute(
        "SELECT domain, COUNT(*) as cnt FROM evaluation_logs GROUP BY domain"
    ).fetchall()
    domain_breakdown = {row["domain"]: row["cnt"] for row in domain_rows}

    # Score distribution (buckets: 0-1, 1-2, ..., 9-10)
    score_distribution = [0] * 10
    score_rows = conn.execute(
        "SELECT CAST(score AS INTEGER) as bucket, COUNT(*) as cnt FROM evaluation_logs GROUP BY bucket"
    ).fetchall()
    for row in score_rows:
        bucket = min(row["bucket"], 9)  # scores of exactly 10 go into bucket 9
        score_distribution[bucket] += row["cnt"]

    # Recent trend: average score per day for the last 30 days
    trend_rows = conn.execute("""
        SELECT DATE(timestamp) as day, AVG(score) as avg_score, COUNT(*) as cnt
        FROM evaluation_logs
        WHERE timestamp >= DATE('now', '-30 days')
        GROUP BY day
        ORDER BY day ASC
    """).fetchall()
    recent_trend = [{"date": row["day"], "avg_score": round(row["avg_score"], 2), "count": row["cnt"]} for row in trend_rows]

    return {
        "total_evaluations": total,
        "avg_score": round(avg_score, 2),
        "avg_confidence": round(avg_confidence, 2),
        "method_breakdown": method_breakdown,
        "domain_breakdown": domain_breakdown,
        "score_distribution": score_distribution,
        "recent_trend": recent_trend,
    }
