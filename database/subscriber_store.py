import os
import sqlite3
from datetime import datetime

DATA_DIR = os.environ.get("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_NAME = os.path.join(DATA_DIR, "subscribers.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    return sqlite3.connect(DB_NAME)


def create_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            webhook_id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            secret_ref TEXT NOT NULL,
            active BOOLEAN DEFAULT 1,
            created_at TEXT
        )
        """)

    conn.commit()
    conn.close()


def add_subscriber(webhook_id, url, secret_ref, active=True):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    INSERT INTO subscribers 
    (webhook_id, url, secret_ref, active, created_at)
    VALUES (?, ?, ?, ?, ?)
    """,
        (webhook_id, url, secret_ref, 1 if active else 0, datetime.now().isoformat()),
    )

    conn.commit()
    conn.close()


def remove_subscriber(webhook_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM subscribers WHERE webhook_id=?", (webhook_id,))

    conn.commit()
    conn.close()


def list_subscribers():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM subscribers WHERE active=1")

    data = cursor.fetchall()

    conn.close()

    return data
