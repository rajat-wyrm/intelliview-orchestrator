import json
import os
import sys

# Ensure the parent src/ directory is in python search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import INTERVIEWS_FILE, LOGS_FILE, get_db_conn, init_db


def migrate():
    print("Starting database migration...")
    init_db()

    conn = get_db_conn()
    cursor = conn.cursor()

    # Migrate interviews
    if os.path.exists(INTERVIEWS_FILE):
        print("Found interviews.json. Migrating...")
        try:
            with open(INTERVIEWS_FILE, encoding="utf-8") as f:
                interviews = json.load(f)
            migrated_count = 0
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
                if cursor.rowcount > 0:
                    migrated_count += 1
            print(f"Successfully migrated {migrated_count} interviews.")
        except Exception as e:
            print(f"Error migrating interviews: {e}")

    # Migrate logs
    if os.path.exists(LOGS_FILE):
        print("Found sent_logs.json. Migrating...")
        try:
            with open(LOGS_FILE, encoding="utf-8") as f:
                logs = json.load(f)
            migrated_count = 0
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
                if cursor.rowcount > 0:
                    migrated_count += 1
            print(f"Successfully migrated {migrated_count} logs.")
        except Exception as e:
            print(f"Error migrating logs: {e}")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")


if __name__ == "__main__":
    migrate()
