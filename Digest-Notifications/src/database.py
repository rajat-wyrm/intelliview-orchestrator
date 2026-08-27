import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "notifications.db")

INTERVIEWS_FILE = os.path.join(DATA_DIR, "interviews.json")
LOGS_FILE = os.path.join(DATA_DIR, "sent_logs.json")


def get_db_conn():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id TEXT PRIMARY KEY,
            candidate_name TEXT NOT NULL,
            role TEXT NOT NULL,
            interviewer_name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled',
            meeting_link TEXT,
            location TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL,
            count INTEGER NOT NULL,
            date_range TEXT NOT NULL,
            recipient TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    conn.commit()

    # Automatic migration helper if SQLite database table is empty and JSON files exist
    cursor.execute("SELECT COUNT(*) FROM interviews")
    count_interviews = cursor.fetchone()[0]
    if count_interviews == 0 and os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE, encoding="utf-8") as f:
                interviews = json.load(f)
            for item in interviews:
                cursor.execute(
                    "INSERT OR IGNORE INTO interviews (id, candidate_name, role, interviewer_name, date, time, status, meeting_link, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        item.get("id"),
                        item.get("candidate_name"),
                        item.get("role"),
                        item.get("interviewer_name"),
                        item.get("date"),
                        item.get("time"),
                        item.get("status", "Scheduled"),
                        item.get("meeting_link"),
                        item.get("location"),
                    ),
                )
            conn.commit()
        except Exception as e:
            print(f"Auto-migration of interviews failed: {e}")

    cursor.execute("SELECT COUNT(*) FROM sent_logs")
    count_logs = cursor.fetchone()[0]
    if count_logs == 0 and os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, encoding="utf-8") as f:
                logs = json.load(f)
            for item in logs:
                cursor.execute(
                    "INSERT OR IGNORE INTO sent_logs (id, timestamp, type, count, date_range, recipient, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        item.get("id"),
                        item.get("timestamp"),
                        item.get("type"),
                        item.get("count"),
                        item.get("date_range"),
                        item.get("recipient"),
                        item.get("status"),
                    ),
                )
            conn.commit()
        except Exception as e:
            print(f"Auto-migration of logs failed: {e}")

    conn.close()
