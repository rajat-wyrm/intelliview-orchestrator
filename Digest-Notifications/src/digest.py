import argparse
import datetime
import json
import os
import threading
import traceback
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP server that handles each request in a separate thread."""

    daemon_threads = True


from digest_builder import build_digest

# Import modular components
from models import DigestFrequency, DigestPayload, DigestRecipient, InterviewEvent
from renderer import render_digest_html, render_digest_text
from sender import send_digest_for_recipient

from database import get_db_conn, init_db

# ── Configuration ──────────────────────────────────────────────────────────────
# Configurable batch size: set env var DIGEST_BATCH_SIZE to override (default 5)
DIGEST_BATCH_SIZE = int(os.environ.get("DIGEST_BATCH_SIZE", 5))
API_TOKEN = os.environ.get("API_TOKEN", "api123")
FILE_LOCK = threading.Lock()

# File Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INTERVIEWS_FILE = os.path.join(DATA_DIR, "interviews.json")
LOGS_FILE = os.path.join(DATA_DIR, "sent_logs.json")
UNSUBSCRIBE_BASE = "https://orchestrator.example.com"


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with FILE_LOCK:
        init_db()


ensure_dirs()  # Run immediately on module import to guarantee directories exist


# ── Core Database Mapping ──────────────────────────────────────────────────────
def get_upcoming_interviews(ref_date_str=None, end_date_str=None):
    """
    Reads interviews.json, filters upcoming events on or after ref_date_str,
    and before end_date_str if provided, sorts chronologically, and returns
    the top DIGEST_BATCH_SIZE as InterviewEvent dataclass objects.
    """
    if not ref_date_str:
        ref_date_str = datetime.date.today().isoformat()

    with FILE_LOCK:
        conn = get_db_conn()
        cursor = conn.cursor()
        if end_date_str:
            cursor.execute(
                "SELECT * FROM interviews WHERE date >= ? AND date < ? AND status = 'Scheduled'",
                (ref_date_str, end_date_str),
            )
        else:
            cursor.execute(
                "SELECT * FROM interviews WHERE date >= ? AND status = 'Scheduled'",
                (ref_date_str,),
            )
        rows = cursor.fetchall()
        conn.close()

    events = []
    for row in rows:
        dt = datetime.datetime.fromisoformat(f"{row['date']}T{row['time']}")
        events.append(
            InterviewEvent(
                interview_id=row["id"],
                candidate_name=row["candidate_name"],
                role_title=row["role"],
                interviewer_name=row["interviewer_name"],
                scheduled_at=dt,
                meeting_link=row["meeting_link"],
                location=row["location"],
            )
        )

    # Sort chronologically then cap at DIGEST_BATCH_SIZE
    events.sort(key=lambda x: x.scheduled_at)
    return events[:DIGEST_BATCH_SIZE], len(events)


def _build_payload(digest_type: str, ref_date_str: str) -> DigestPayload:
    """Shared helper: load events and build the DigestPayload."""
    ref_date = datetime.date.fromisoformat(ref_date_str)
    if digest_type.lower() == "weekly":
        end_date = ref_date + datetime.timedelta(days=7)
    else:
        end_date = ref_date + datetime.timedelta(days=1)
    end_date_str = end_date.isoformat()

    top_n, total_upcoming_count = get_upcoming_interviews(ref_date_str, end_date_str)
    freq = (
        DigestFrequency.DAILY
        if digest_type.lower() == "daily"
        else DigestFrequency.WEEKLY
    )
    recipient = DigestRecipient(
        user_id="u-default-recruiter",
        email="digest-recipients@example.com",
        display_name="Recruiter",
        frequency=freq,
    )
    ref_dt = datetime.datetime.fromisoformat(ref_date_str)
    payload = build_digest(recipient, top_n, now=ref_dt)
    payload.total_upcoming_count = total_upcoming_count
    return payload


def generate_digest_html_output(digest_type="daily", ref_date_str=None):
    """
    Public API used by the web server and tests.
    Returns (html_str, count, date_range_str).
    """
    if not ref_date_str:
        ref_date_str = datetime.date.today().isoformat()

    ref_date = datetime.date.fromisoformat(ref_date_str)

    # Date range label
    if digest_type.lower() == "weekly":
        end_date = ref_date + datetime.timedelta(days=6)
        date_range = (
            f"{ref_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        )
    else:
        date_range = ref_date.strftime("%B %d, %Y")

    payload = _build_payload(digest_type, ref_date_str)

    rendered_html = render_digest_html(
        payload=payload,
        unsubscribe_url=f"{UNSUBSCRIBE_BASE}/unsubscribe?user_id={payload.recipient.user_id}",
    )
    return rendered_html, payload.total_count, date_range


def generate_all_outputs(digest_type="daily", ref_date_str=None):
    """
    Generates and writes HTML and plain-text fallback.
    Returns a result dict suitable for logging.
    """
    if not ref_date_str:
        ref_date_str = datetime.date.today().isoformat()

    payload = _build_payload(digest_type, ref_date_str)
    unsubscribe_url = (
        f"{UNSUBSCRIBE_BASE}/unsubscribe?user_id={payload.recipient.user_id}"
    )

    # ── Empty digest suppression ───────────────────────────────────────────────
    if payload.total_count == 0:
        return {
            "status": "skipped",
            "reason": "no_upcoming_interviews",
            "digest_type": digest_type,
            "reference_date": ref_date_str,
            "interviews_count": 0,
        }

    # ── HTML output ────────────────────────────────────────────────────────────
    html = render_digest_html(payload, unsubscribe_url=unsubscribe_url)
    html_path = os.path.join(OUTPUT_DIR, "digest_email.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # ── Plain-text fallback ────────────────────────────────────────────────────
    text = render_digest_text(payload, unsubscribe_url=unsubscribe_url)
    txt_path = os.path.join(OUTPUT_DIR, "digest_email.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    ref_date = datetime.date.fromisoformat(ref_date_str)
    if digest_type.lower() == "weekly":
        end_date = ref_date + datetime.timedelta(days=6)
        date_range = (
            f"{ref_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        )
    else:
        date_range = ref_date.strftime("%B %d, %Y")

    return {
        "status": "success",
        "digest_type": digest_type,
        "reference_date": ref_date_str,
        "date_range": date_range,
        "interviews_count": payload.total_count,
        "total_upcoming_count": payload.total_upcoming_count,
        "batch_size_limit": DIGEST_BATCH_SIZE,
        "output_html": html_path,
        "output_text": txt_path,
    }


def dispatch_digest(digest_type="daily", ref_date_str=None):
    """
    Generates the digest and automatically dispatches it to the recipient,
    updating the dispatch audit logs. Designed for automated/cron run.
    """
    if not ref_date_str:
        ref_date_str = datetime.date.today().isoformat()

    result = generate_all_outputs(digest_type, ref_date_str)
    if result["status"] == "skipped":
        return result

    # Build payload to get recipient and interviews list
    payload = _build_payload(digest_type, ref_date_str)
    recipient = payload.recipient

    interviews = []
    for day_events in payload.grouped_interviews.values():
        interviews.extend(day_events)

    sender_instance = SimulatedEmailSender()
    send_result = send_digest_for_recipient(
        recipient=recipient,
        interviews=interviews,
        email_sender=sender_instance,
        unsubscribe_base_url=UNSUBSCRIBE_BASE,
    )

    if (
        send_result.get("status") == "sent_simulated"
        or send_result.get("provider") == "none"
    ):
        status_label = "Simulated / no provider configured"
    else:
        status_label = "Sent"

    # Insert into database logs
    with FILE_LOCK:
        log_entry = {
            "id": f"log-{int(datetime.datetime.now().timestamp() * 1000)}",
            "timestamp": datetime.datetime.now().isoformat(),
            "type": digest_type.capitalize(),
            "count": result["interviews_count"],
            "date_range": result["date_range"],
            "recipient": recipient.email,
            "status": status_label,
        }
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sent_logs (id, timestamp, type, count, date_range, recipient, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                log_entry["id"],
                log_entry["timestamp"],
                log_entry["type"],
                log_entry["count"],
                log_entry["date_range"],
                log_entry["recipient"],
                log_entry["status"],
            ),
        )
        conn.commit()
        conn.close()

    return {"status": "success", "digest_result": result, "send_result": send_result}


class SimulatedEmailSender:
    def send_html_email(self, to_email: str, subject: str, html_body: str) -> dict:
        # Write to a file for simulation purposes
        sim_path = os.path.join(OUTPUT_DIR, "simulated_email.html")
        with open(sim_path, "w", encoding="utf-8") as f:
            f.write(html_body)
        return {
            "status": "sent_simulated",
            "provider": "none",
            "message": "Simulated send: No real provider configured.",
        }


# ── HTTP Request Handler ───────────────────────────────────────────────────────
class DashboardHandler(BaseHTTPRequestHandler):
    def validate_auth(self) -> bool:
        incoming_token = self.headers.get("X-API-Token", "").strip()
        if incoming_token != API_TOKEN:
            self.send_json(
                401, {"status": "error", "message": "Invalid or missing API Token"}
            )
            return False
        return True

    def log_message(self, format, *args):
        pass

    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def send_file(self, file_path, content_type):
        if not os.path.exists(file_path):
            self.send_error(404, "File not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path in ("/", "/index.html"):
            self.send_file(
                os.path.join(BASE_DIR, "src", "web", "index.html"), "text/html"
            )
        elif path == "/main.js":
            self.send_file(
                os.path.join(BASE_DIR, "src", "web", "main.js"),
                "application/javascript",
            )
        elif path == "/api/interviews":
            params = urllib.parse.parse_qs(parsed_url.query)
            try:
                limit = int(params.get("limit", [10])[0])
            except ValueError:
                limit = 10
            try:
                offset = int(params.get("offset", [0])[0])
            except ValueError:
                offset = 0

            with FILE_LOCK:
                conn = get_db_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM interviews")
                total = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT * FROM interviews ORDER BY date ASC, time ASC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
                rows = cursor.fetchall()
                conn.close()

            interviews = []
            for row in rows:
                interviews.append(
                    {
                        "id": row["id"],
                        "candidate_name": row["candidate_name"],
                        "role": row["role"],
                        "interviewer_name": row["interviewer_name"],
                        "date": row["date"],
                        "time": row["time"],
                        "status": row["status"],
                        "meeting_link": row["meeting_link"],
                        "location": row["location"],
                    }
                )

            self.send_json(
                200,
                {
                    "interviews": interviews,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            )
        elif path == "/api/logs":
            params = urllib.parse.parse_qs(parsed_url.query)
            try:
                limit = int(params.get("limit", [10])[0])
            except ValueError:
                limit = 10
            try:
                offset = int(params.get("offset", [0])[0])
            except ValueError:
                offset = 0

            with FILE_LOCK:
                conn = get_db_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sent_logs")
                total = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT * FROM sent_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
                rows = cursor.fetchall()
                conn.close()

            logs = []
            for row in rows:
                logs.append(
                    {
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "type": row["type"],
                        "count": row["count"],
                        "date_range": row["date_range"],
                        "recipient": row["recipient"],
                        "status": row["status"],
                    }
                )

            self.send_json(
                200, {"logs": logs, "total": total, "limit": limit, "offset": offset}
            )
        elif path == "/api/config":
            self.send_json(200, {"batch_size": DIGEST_BATCH_SIZE})
        elif path == "/api/download/txt":
            txt_path = os.path.join(OUTPUT_DIR, "digest_email.txt")
            if not os.path.exists(txt_path):
                self.send_json(
                    404,
                    {
                        "error": "Text file not generated yet. Click Generate Preview first."
                    },
                )
                return
            with open(txt_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header(
                "Content-Disposition", 'attachment; filename="digest_email.txt"'
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404, "Page Not Found")

    def do_POST(self):
        if not self.validate_auth():
            return
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json(400, {"status": "error", "message": "Invalid JSON"})
            return

        if path == "/api/interviews":
            required = ["candidate_name", "role", "interviewer_name", "date", "time"]
            if not all(k in data for k in required):
                self.send_json(400, {"status": "error", "message": "Missing fields"})
                return

            try:
                datetime.datetime.strptime(data["date"], "%Y-%m-%d")
            except ValueError:
                self.send_json(
                    400,
                    {
                        "status": "error",
                        "message": "Invalid date format. Expected YYYY-MM-DD.",
                    },
                )
                return

            try:
                datetime.datetime.strptime(data["time"], "%H:%M")
            except ValueError:
                self.send_json(
                    400,
                    {
                        "status": "error",
                        "message": "Invalid time format. Expected HH:MM.",
                    },
                )
                return

            with FILE_LOCK:
                new_id = f"int-{int(datetime.datetime.now().timestamp() * 1000)}"
                new_interview = {
                    "id": new_id,
                    "candidate_name": data["candidate_name"],
                    "role": data["role"],
                    "interviewer_name": data["interviewer_name"],
                    "date": data["date"],
                    "time": data["time"],
                    "status": "Scheduled",
                    "meeting_link": data.get("meeting_link"),
                    "location": data.get("location"),
                }
                conn = get_db_conn()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO interviews (id, candidate_name, role, interviewer_name, date, time, status, meeting_link, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        new_interview["id"],
                        new_interview["candidate_name"],
                        new_interview["role"],
                        new_interview["interviewer_name"],
                        new_interview["date"],
                        new_interview["time"],
                        new_interview["status"],
                        new_interview.get("meeting_link"),
                        new_interview.get("location"),
                    ),
                )
                conn.commit()
                conn.close()
            self.send_json(201, {"status": "success", "interview": new_interview})

        elif path == "/api/generate":
            digest_type = data.get("type", "daily")
            if digest_type not in ("daily", "weekly"):
                self.send_json(
                    400,
                    {
                        "status": "error",
                        "message": "Invalid digest type. Must be 'daily' or 'weekly'.",
                    },
                )
                return

            ref_date = data.get("ref_date") or None
            if ref_date:
                try:
                    datetime.date.fromisoformat(ref_date)
                except ValueError:
                    self.send_json(
                        400,
                        {
                            "status": "error",
                            "message": "Invalid reference date format. Must be YYYY-MM-DD.",
                        },
                    )
                    return

            try:
                result = generate_all_outputs(digest_type, ref_date)
                if result["status"] == "skipped":
                    self.send_json(
                        200,
                        {
                            "status": "skipped",
                            "message": "No upcoming interviews found. Digest suppressed.",
                            "count": 0,
                            "html": "",
                            "text": "",
                            "date_range": "",
                        },
                    )
                    return

                html_path = result["output_html"]
                txt_path = result["output_text"]
                with open(html_path, encoding="utf-8") as f:
                    html = f.read()
                with open(txt_path, encoding="utf-8") as f:
                    text = f.read()

                self.send_json(
                    200,
                    {
                        "status": "success",
                        "html": html,
                        "text": text,
                        "count": result["interviews_count"],
                        "total_upcoming_count": result.get(
                            "total_upcoming_count", result["interviews_count"]
                        ),
                        "date_range": result["date_range"],
                        "batch_size_limit": result["batch_size_limit"],
                    },
                )
            except Exception as e:
                error_id = uuid.uuid4().hex[:8]
                print("==================================================")
                print(f"ERROR [{error_id}]: Exception in /api/generate")
                traceback.print_exc()
                print("==================================================")
                self.send_json(
                    500,
                    {
                        "status": "error",
                        "message": f"An internal server error occurred. Please contact the administrator with Error ID: {error_id}.",
                    },
                )

        elif path == "/api/send":
            digest_type = data.get("type", "daily")
            count = data.get("count", 0)
            date_range = data.get("date_range", "")

            if count == 0:
                self.send_json(
                    200,
                    {
                        "status": "skipped",
                        "message": "No interviews to send — digest suppressed.",
                    },
                )
                return

            try:
                # Reconstruct recipient and get the interviews in the window
                ref_date_str = data.get("ref_date") or datetime.date.today().isoformat()
                payload = _build_payload(digest_type, ref_date_str)
                recipient = payload.recipient

                # Extract flat list of interviews from payload.grouped_interviews
                interviews = []
                for day_events in payload.grouped_interviews.values():
                    interviews.extend(day_events)

                sender_instance = SimulatedEmailSender()
                result = send_digest_for_recipient(
                    recipient=recipient,
                    interviews=interviews,
                    email_sender=sender_instance,
                    unsubscribe_base_url=UNSUBSCRIBE_BASE,
                )

                # Determine the status label based on the sender result/provider
                if (
                    result.get("status") == "sent_simulated"
                    or result.get("provider") == "none"
                ):
                    status_label = "Simulated / no provider configured"
                    message_label = "Email digest send simulated successfully (no provider configured)."
                else:
                    status_label = "Sent"
                    message_label = "Email digest sent successfully!"

                with FILE_LOCK:
                    log_entry = {
                        "id": f"log-{int(datetime.datetime.now().timestamp() * 1000)}",
                        "timestamp": datetime.datetime.now().isoformat(),
                        "type": digest_type.capitalize(),
                        "count": count,
                        "date_range": date_range,
                        "recipient": recipient.email,
                        "status": status_label,
                    }
                    conn = get_db_conn()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO sent_logs (id, timestamp, type, count, date_range, recipient, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            log_entry["id"],
                            log_entry["timestamp"],
                            log_entry["type"],
                            log_entry["count"],
                            log_entry["date_range"],
                            log_entry["recipient"],
                            log_entry["status"],
                        ),
                    )
                    conn.commit()
                    conn.close()

                self.send_json(
                    200,
                    {
                        "status": "success",
                        "message": message_label,
                        "sender_result": result,
                    },
                )
            except Exception as e:
                error_id = uuid.uuid4().hex[:8]
                print("==================================================")
                print(f"ERROR [{error_id}]: Exception in /api/send")
                traceback.print_exc()
                print("==================================================")
                self.send_json(
                    500,
                    {
                        "status": "error",
                        "message": f"An internal server error occurred. Please contact the administrator with Error ID: {error_id}.",
                    },
                )
        else:
            self.send_json(404, {"status": "error", "message": "Endpoint not found"})

    def do_DELETE(self):
        if not self.validate_auth():
            return
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/interviews"):
            params = urllib.parse.parse_qs(parsed_url.query)
            interview_id = params.get("id", [None])[0]
            if not interview_id:
                self.send_json(
                    400, {"status": "error", "message": "Missing ID parameter"}
                )
                return
            with FILE_LOCK:
                conn = get_db_conn()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM interviews WHERE id = ?", (interview_id,)
                )
                exists = cursor.fetchone()[0]
                if not exists:
                    conn.close()
                    self.send_json(
                        404, {"status": "error", "message": "Interview not found"}
                    )
                    return
                cursor.execute("DELETE FROM interviews WHERE id = ?", (interview_id,))
                conn.commit()
                conn.close()
            self.send_json(200, {"status": "success", "message": "Interview deleted"})
        else:
            self.send_json(404, {"status": "error", "message": "Endpoint not found"})


# ── Main Entry Point ───────────────────────────────────────────────────────────
def main():
    ensure_dirs()

    parser = argparse.ArgumentParser(description="Digest Notification Engine")
    parser.add_argument("--cli", action="store_true", help="Run in CLI generation mode")
    parser.add_argument(
        "--type", choices=["daily", "weekly"], default="daily", help="Type of digest"
    )
    parser.add_argument("--ref-date", help="Reference date YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--serve", action="store_true", help="Run interactive web server dashboard"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port for dashboard (default: 8000)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface for dashboard (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--cron",
        action="store_true",
        help="Run in cron mode (generate and dispatch automatically)",
    )
    args = parser.parse_args()

    if args.serve:
        server_address = (args.host, args.port)
        httpd = ThreadingHTTPServer(server_address, DashboardHandler)
        print("==================================================")
        host_display = "localhost" if args.host == "127.0.0.1" else args.host
        print(f"Dashboard running at: http://{host_display}:{args.port}")
        print(f"Batch size limit    : {DIGEST_BATCH_SIZE} (DIGEST_BATCH_SIZE)")
        print("Press Ctrl+C to terminate.")
        print("==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.server_close()

    elif args.cli:
        ref_date = args.ref_date or datetime.date.today().isoformat()
        result = generate_all_outputs(args.type, ref_date)
        print(json.dumps(result, indent=2))

    elif args.cron:
        ref_date = args.ref_date or datetime.date.today().isoformat()
        result = dispatch_digest(args.type, ref_date)
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
