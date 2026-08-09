"""
tests/test_digest_notifications.py

Consolidated test suite for Digest Notifications.
Contains key integration and unit tests (max 15 tests, no forbidden names or calendar generator checks).

Run with:
    python -m pytest tests/ -v
  or
    python tests/test_digest_notifications.py
"""

import datetime
import json
import os
import sys
import unittest
from unittest.mock import MagicMock

# Path setup
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, os.path.abspath(SRC_DIR))

from digest import (
    DashboardHandler,
    _build_payload,
    generate_all_outputs,
    generate_digest_html_output,
    get_upcoming_interviews,
)
from digest_builder import build_digest, group_interviews_by_date
from models import DigestFrequency, DigestPayload, DigestRecipient, InterviewEvent
from renderer import render_digest_html, render_digest_text
from sender import send_digest_for_recipient


def _make_recipient(freq=DigestFrequency.DAILY):
    return DigestRecipient(
        user_id="u-test-001",
        email="recruiter@example.com",
        display_name="Recruiter",
        frequency=freq,
    )


def _make_event(
    interview_id="iv-001",
    candidate="Alex Rivera",
    role="Frontend Engineer",
    interviewer="Sarah Connor",
    dt=None,
):
    return InterviewEvent(
        interview_id=interview_id,
        candidate_name=candidate,
        role_title=role,
        interviewer_name=interviewer,
        scheduled_at=dt or datetime.datetime(2026, 7, 1, 10, 0),
    )


class TestDigestNotifications(unittest.TestCase):
    # ── 1. Model Tests ──
    def test_event_date_key_and_display(self):
        ev = _make_event(dt=datetime.datetime(2026, 7, 4, 14, 30))
        self.assertEqual(ev.date_key, "2026-07-04")
        self.assertIn("14:30", ev.scheduled_at.time().isoformat())

    def test_payload_total_count(self):
        recipient = _make_recipient()
        events = [_make_event("iv-1"), _make_event("iv-2")]
        payload = build_digest(recipient, events)
        self.assertEqual(payload.total_count, 2)

    # ── 2. Builder Tests ──
    def test_group_interviews_by_date(self):
        events = [
            _make_event("iv-1", dt=datetime.datetime(2026, 7, 1, 15, 0)),
            _make_event("iv-2", dt=datetime.datetime(2026, 7, 1, 9, 0)),
            _make_event("iv-3", dt=datetime.datetime(2026, 7, 2, 10, 0)),
        ]
        grouped = group_interviews_by_date(events)
        self.assertEqual(list(grouped.keys()), ["2026-07-01", "2026-07-02"])
        # Verify chronological sorting within the day
        self.assertEqual(grouped["2026-07-01"][0].interview_id, "iv-2")

    # ── 3. Renderer Tests ──
    def test_html_and_text_rendering(self):
        recipient = _make_recipient()
        events = [_make_event(candidate="Jordan Smith")]
        payload = build_digest(recipient, events)

        # Test HTML Renderer
        html = render_digest_html(payload, unsubscribe_url="http://test.com/unsub")
        self.assertIn("Jordan Smith", html)
        self.assertIn("http://test.com/unsub", html)

        # Test Text Renderer
        txt = render_digest_text(payload, unsubscribe_url="http://test.com/unsub")
        self.assertIn("Jordan Smith", txt)
        self.assertIn("http://test.com/unsub", txt)

    # ── 4. Sender Tests ──
    def test_send_digest_skips_when_empty(self):
        sender = MagicMock()
        result = send_digest_for_recipient(
            recipient=_make_recipient(),
            interviews=[],
            email_sender=sender,
            unsubscribe_base_url="https://orchestrator.example.com",
        )
        self.assertEqual(result["status"], "skipped")
        sender.send_html_email.assert_not_called()

    def test_send_digest_success(self):
        sender = MagicMock()
        sender.send_html_email.return_value = {"status": "sent", "provider": "mock"}
        result = send_digest_for_recipient(
            recipient=_make_recipient(),
            interviews=[_make_event()],
            email_sender=sender,
            unsubscribe_base_url="https://orchestrator.example.com",
        )
        self.assertEqual(result["status"], "sent")
        sender.send_html_email.assert_called_once()

    # ── 5. Engine & Spec Compliance Tests ──
    def test_upcoming_interviews_cap_at_five(self):
        # get_upcoming_interviews must limit results to the configured batch limit (default 5)
        events, _total_count = get_upcoming_interviews("2026-06-01")
        self.assertLessEqual(len(events), 5)

    def test_generate_digest_html_output(self):
        html, count, _date_range = generate_digest_html_output("daily", "2026-06-27")
        self.assertIn("Daily Digest", html)
        self.assertGreaterEqual(count, 0)

    def test_empty_digest_suppression(self):
        result = generate_all_outputs("daily", "2099-01-01")
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "no_upcoming_interviews")

    def test_output_files_generated(self):
        result = generate_all_outputs("daily", "2026-06-27")
        self.assertEqual(result["status"], "success")
        self.assertTrue(os.path.exists(result["output_html"]))
        self.assertTrue(os.path.exists(result["output_text"]))

    def test_daily_vs_weekly_date_scoping(self):
        # ref_date is 2026-07-01
        ref_date = datetime.date(2026, 7, 1)
        day_1 = (ref_date + datetime.timedelta(days=1)).isoformat()
        day_3 = (ref_date + datetime.timedelta(days=3)).isoformat()
        day_10 = (ref_date + datetime.timedelta(days=10)).isoformat()

        mock_data = [
            {
                "id": "int-1",
                "candidate_name": "A",
                "role": "R",
                "interviewer_name": "I",
                "date": day_1,
                "time": "10:00",
            },
            {
                "id": "int-2",
                "candidate_name": "B",
                "role": "R",
                "interviewer_name": "I",
                "date": day_3,
                "time": "11:00",
            },
            {
                "id": "int-3",
                "candidate_name": "C",
                "role": "R",
                "interviewer_name": "I",
                "date": day_10,
                "time": "12:00",
            },
        ]
        import sqlite3

        # Keep init_conn open so the in-memory DB persists for the duration of this test
        init_conn = sqlite3.connect(
            "file:scoping_db?mode=memory&cache=shared", uri=True
        )
        init_conn.row_factory = sqlite3.Row
        init_conn.execute(
            "CREATE TABLE interviews (id TEXT, candidate_name TEXT, role TEXT, interviewer_name TEXT, date TEXT, time TEXT, status TEXT, meeting_link TEXT, location TEXT)"
        )
        for item in mock_data:
            init_conn.execute(
                "INSERT INTO interviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item["id"],
                    item["candidate_name"],
                    item["role"],
                    item["interviewer_name"],
                    item["date"],
                    item["time"],
                    item.get("status", "Scheduled"),
                    item.get("meeting_link"),
                    item.get("location"),
                ),
            )
        init_conn.commit()

        def get_shared_conn():
            c = sqlite3.connect("file:scoping_db?mode=memory&cache=shared", uri=True)
            c.row_factory = sqlite3.Row
            return c

        with unittest.mock.patch("digest.get_db_conn", side_effect=get_shared_conn):
            # Daily digest at day_1 (2026-07-02) should include only the day_1 interview
            daily_payload = _build_payload("daily", day_1)
            self.assertEqual(daily_payload.total_count, 1)
            flat_daily = [
                ev
                for events in daily_payload.grouped_interviews.values()
                for ev in events
            ]
            self.assertEqual(flat_daily[0].interview_id, "int-1")

            # Weekly digest at ref_date (2026-07-01) should include day_1 and day_3, but not day_10
            weekly_payload = _build_payload("weekly", ref_date.isoformat())
            self.assertEqual(weekly_payload.total_count, 2)
            flat_weekly = [
                ev
                for events in weekly_payload.grouped_interviews.values()
                for ev in events
            ]
            self.assertEqual(flat_weekly[0].interview_id, "int-1")
            self.assertEqual(flat_weekly[1].interview_id, "int-2")

        init_conn.close()

    def test_cors_headers_not_wildcarded(self):
        class FakeHandler(DashboardHandler):
            def __init__(self):
                self.headers_sent = []
                self.wfile = unittest.mock.MagicMock()

            def send_response(self, code, message=None):
                pass

            def send_header(self, keyword, value):
                self.headers_sent.append((keyword, value))

            def end_headers(self):
                pass

        handler = FakeHandler()
        handler.send_json(200, {})
        for keyword, _value in handler.headers_sent:
            self.assertNotEqual(keyword.lower(), "access-control-allow-origin")

    def test_api_send_invokes_sender_module(self):
        import unittest.mock

        from digest import DashboardHandler

        class FakeHandler(DashboardHandler):
            def __init__(self):
                self.headers_sent = []
                self.json_sent = None
                self.headers = {"Content-Length": "80", "X-API-Token": "api123"}
                self.rfile = unittest.mock.MagicMock()
                self.wfile = unittest.mock.MagicMock()
                self.path = "/api/send"

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                self.headers_sent.append((keyword, value))

            def end_headers(self):
                pass

            def send_json(self, status_code, data):
                self.status_code = status_code
                self.json_sent = data

            def validate_auth(self):
                return True

        handler = FakeHandler()
        body_data = json.dumps(
            {
                "type": "daily",
                "count": 2,
                "date_range": "June 27, 2026",
                "ref_date": "2026-06-27",
            }
        ).encode("utf-8")
        handler.rfile.read.return_value = body_data

        mock_send = unittest.mock.MagicMock(
            return_value={"status": "sent_simulated", "provider": "none"}
        )

        import sqlite3

        db_conn_send_mock = sqlite3.connect(":memory:")
        db_conn_send_mock.row_factory = sqlite3.Row
        db_conn_send_mock.execute(
            "CREATE TABLE sent_logs (id TEXT, timestamp TEXT, type TEXT, count INTEGER, date_range TEXT, recipient TEXT, status TEXT)"
        )
        db_conn_send_mock.commit()

        with unittest.mock.patch("digest.send_digest_for_recipient", mock_send):
            with unittest.mock.patch(
                "digest.get_upcoming_interviews", return_value=([], 0)
            ):
                with unittest.mock.patch(
                    "digest.get_db_conn", return_value=db_conn_send_mock
                ):
                    handler.do_POST()

        mock_send.assert_called_once()
        self.assertIn("no provider configured", handler.json_sent["message"])

    def test_concurrent_interview_scheduling(self):
        import socket
        import threading
        import time
        import urllib.request

        from digest import DashboardHandler, ThreadingHTTPServer

        from database import get_db_conn

        # Backup interviews from SQLite database
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM interviews")
        original_interviews = cursor.fetchall()

        try:
            # Clear interviews table
            cursor.execute("DELETE FROM interviews")
            conn.commit()

            # Find an open port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            s.close()

            # Start server in background thread
            server_address = ("127.0.0.1", port)
            httpd = ThreadingHTTPServer(server_address, DashboardHandler)

            server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            server_thread.start()
            time.sleep(0.5)  # Wait for server to boot

            errors = []

            def send_post_request(candidate_name):
                payload = json.dumps(
                    {
                        "candidate_name": candidate_name,
                        "role": "Engineer",
                        "interviewer_name": "Sarah",
                        "date": "2026-07-15",
                        "time": "10:00",
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/interviews", data=payload
                )
                req.add_header("X-API-Token", "api123")
                req.add_header("Content-Type", "application/json")
                try:
                    res = urllib.request.urlopen(req)
                    self.assertEqual(res.getcode(), 201)
                except Exception as e:
                    errors.append(e)

            # Start two concurrent threads
            t1 = threading.Thread(target=send_post_request, args=("Candidate A",))
            t2 = threading.Thread(target=send_post_request, args=("Candidate B",))

            t1.start()
            t2.start()
            t1.join()
            t2.join()

            # Shutdown server
            httpd.shutdown()
            httpd.server_close()

            # Check for errors during threads execution
            self.assertEqual(len(errors), 0, f"Concurrent requests failed: {errors}")

            # Assert both interviews are present in the SQLite database
            cursor.execute("SELECT * FROM interviews")
            interviews = cursor.fetchall()
            names = [i["candidate_name"] for i in interviews]
            self.assertIn("Candidate A", names)
            self.assertIn("Candidate B", names)
        finally:
            # Restore interviews table
            cursor.execute("DELETE FROM interviews")
            for row in original_interviews:
                cursor.execute(
                    "INSERT INTO interviews (id, candidate_name, role, interviewer_name, date, time, status, meeting_link, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        row["id"],
                        row["candidate_name"],
                        row["role"],
                        row["interviewer_name"],
                        row["date"],
                        row["time"],
                        row["status"],
                        row["meeting_link"],
                        row["location"],
                    ),
                )
            conn.commit()
            conn.close()

    def test_api_generate_secure_exception_handling(self):
        import unittest.mock

        from digest import DashboardHandler

        class FakeHandler(DashboardHandler):
            def __init__(self):
                self.headers_sent = []
                self.json_sent = None
                self.headers = {"Content-Length": "40", "X-API-Token": "api123"}
                self.rfile = unittest.mock.MagicMock()
                self.wfile = unittest.mock.MagicMock()
                self.path = "/api/generate"

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                self.headers_sent.append((keyword, value))

            def end_headers(self):
                pass

            def send_json(self, status_code, data):
                self.status_code = status_code
                self.json_sent = data

            def validate_auth(self):
                return True

        handler = FakeHandler()
        body_data = json.dumps({"type": "daily", "ref_date": "2026-06-27"}).encode(
            "utf-8"
        )
        handler.rfile.read.return_value = body_data

        mock_gen = unittest.mock.MagicMock(
            side_effect=ValueError("CRITICAL DATABASE CORRUPTION EXCEPTION")
        )

        with unittest.mock.patch("digest.generate_all_outputs", mock_gen):
            handler.do_POST()

        self.assertEqual(handler.status_code, 500)
        self.assertEqual(handler.json_sent["status"], "error")
        self.assertNotIn(
            "CRITICAL DATABASE CORRUPTION EXCEPTION", handler.json_sent["message"]
        )
        self.assertNotIn("ValueError", handler.json_sent["message"])
        self.assertIn("internal server error occurred", handler.json_sent["message"])
        self.assertIn("Error ID:", handler.json_sent["message"])

    def test_api_create_interview_date_time_validation(self):
        import unittest.mock

        from digest import DashboardHandler

        class FakeHandler(DashboardHandler):
            def __init__(self):
                self.headers_sent = []
                self.json_sent = None
                self.headers = {"Content-Length": "40", "X-API-Token": "api123"}
                self.rfile = unittest.mock.MagicMock()
                self.wfile = unittest.mock.MagicMock()
                self.path = "/api/interviews"

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                self.headers_sent.append((keyword, value))

            def end_headers(self):
                pass

            def send_json(self, status_code, data):
                self.status_code = status_code
                self.json_sent = data

            def validate_auth(self):
                return True

        # Test malformed date
        handler = FakeHandler()
        body_data = json.dumps(
            {
                "candidate_name": "John Doe",
                "role": "Engineer",
                "interviewer_name": "Sarah",
                "date": "2026/07/15",
                "time": "10:00",
            }
        ).encode("utf-8")
        handler.rfile.read.return_value = body_data
        handler.do_POST()

        self.assertEqual(handler.status_code, 400)
        self.assertEqual(handler.json_sent["status"], "error")
        self.assertIn("Invalid date format", handler.json_sent["message"])

        # Test malformed time
        handler2 = FakeHandler()
        body_data2 = json.dumps(
            {
                "candidate_name": "John Doe",
                "role": "Engineer",
                "interviewer_name": "Sarah",
                "date": "2026-07-15",
                "time": "10-00",
            }
        ).encode("utf-8")
        handler2.rfile.read.return_value = body_data2
        handler2.do_POST()

        self.assertEqual(handler2.status_code, 400)
        self.assertEqual(handler2.json_sent["status"], "error")
        self.assertIn("Invalid time format", handler2.json_sent["message"])

    def test_digest_truncation_notices(self):
        import datetime

        from models import (
            DigestFrequency,
            DigestRecipient,
            InterviewEvent,
        )
        from renderer import render_digest_html, render_digest_text

        recipient = DigestRecipient(
            user_id="u-trunc",
            email="recruiter@example.com",
            display_name="Sarah Recruiter",
            frequency=DigestFrequency.DAILY,
        )

        events = [
            InterviewEvent(
                interview_id=f"int-{i}",
                candidate_name=f"Candidate {i}",
                role_title="Software Engineer",
                interviewer_name="Alice",
                scheduled_at=datetime.datetime(2026, 7, 15, 10, 0),
            )
            for i in range(5)
        ]

        payload = DigestPayload(
            recipient=recipient,
            generated_at=datetime.datetime(2026, 7, 15, 9, 0),
            grouped_interviews={"2026-07-15": events},
            total_upcoming_count=5,
        )

        html = render_digest_html(payload, unsubscribe_url="http://unsub")
        text = render_digest_text(payload, unsubscribe_url="http://unsub")

        self.assertNotIn("Notice: Showing", html)
        self.assertNotIn("Showing 5 of 6", text)

        payload.total_upcoming_count = 6
        html_trunc = render_digest_html(payload, unsubscribe_url="http://unsub")
        text_trunc = render_digest_text(payload, unsubscribe_url="http://unsub")

        self.assertIn("Notice:", html_trunc)
        self.assertIn("Showing 5 of 6 upcoming interviews", html_trunc)
        self.assertIn("Showing 5 of 6 upcoming interviews", text_trunc)

    def test_api_pagination(self):
        import unittest.mock

        from digest import DashboardHandler

        interviews_mock = [
            {
                "id": "1",
                "candidate_name": "A",
                "role": "Eng",
                "interviewer_name": "X",
                "date": "2026-06-01",
                "time": "10:00",
            },
            {
                "id": "2",
                "candidate_name": "B",
                "role": "Eng",
                "interviewer_name": "Y",
                "date": "2026-06-02",
                "time": "11:00",
            },
            {
                "id": "3",
                "candidate_name": "C",
                "role": "Eng",
                "interviewer_name": "Z",
                "date": "2026-06-03",
                "time": "12:00",
            },
        ]
        logs_mock = [
            {
                "id": "l1",
                "timestamp": "2026-06-01T10:00:00",
                "type": "Daily",
                "count": 1,
                "date_range": "2026-06-01",
                "recipient": "r1",
                "status": "Sent",
            },
            {
                "id": "l2",
                "timestamp": "2026-06-02T10:00:00",
                "type": "Daily",
                "count": 2,
                "date_range": "2026-06-02",
                "recipient": "r2",
                "status": "Sent",
            },
            {
                "id": "l3",
                "timestamp": "2026-06-03T10:00:00",
                "type": "Daily",
                "count": 3,
                "date_range": "2026-06-03",
                "recipient": "r3",
                "status": "Sent",
            },
        ]

        class FakeHandler(DashboardHandler):
            def __init__(self, path):
                self.headers_sent = []
                self.json_sent = None
                self.headers = {}
                self.path = path

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                self.headers_sent.append((keyword, value))

            def end_headers(self):
                pass

            def send_json(self, status_code, data):
                self.status_code = status_code
                self.json_sent = data

        import sqlite3

        db_conn_mock = sqlite3.connect(":memory:")
        db_conn_mock.row_factory = sqlite3.Row
        db_conn_mock.execute(
            "CREATE TABLE interviews (id TEXT, candidate_name TEXT, role TEXT, interviewer_name TEXT, date TEXT, time TEXT, status TEXT, meeting_link TEXT, location TEXT)"
        )
        for item in interviews_mock:
            db_conn_mock.execute(
                "INSERT INTO interviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item["id"],
                    item["candidate_name"],
                    item["role"],
                    item["interviewer_name"],
                    item["date"],
                    item["time"],
                    item.get("status", "Scheduled"),
                    item.get("meeting_link"),
                    item.get("location"),
                ),
            )
        db_conn_mock.commit()

        handler = FakeHandler("/api/interviews?limit=2&offset=1")
        with unittest.mock.patch("digest.get_db_conn", return_value=db_conn_mock):
            handler.do_GET()
        self.assertEqual(handler.status_code, 200)
        self.assertEqual(handler.json_sent["total"], 3)
        self.assertEqual(handler.json_sent["limit"], 2)
        self.assertEqual(handler.json_sent["offset"], 1)
        self.assertEqual(len(handler.json_sent["interviews"]), 2)
        self.assertEqual(handler.json_sent["interviews"][0]["candidate_name"], "B")
        self.assertEqual(handler.json_sent["interviews"][1]["candidate_name"], "C")

        db_conn_logs_mock = sqlite3.connect(":memory:")
        db_conn_logs_mock.row_factory = sqlite3.Row
        db_conn_logs_mock.execute(
            "CREATE TABLE sent_logs (id TEXT, timestamp TEXT, type TEXT, count INTEGER, date_range TEXT, recipient TEXT, status TEXT)"
        )
        for item in logs_mock:
            db_conn_logs_mock.execute(
                "INSERT INTO sent_logs VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item["id"],
                    item["timestamp"],
                    item["type"],
                    item["count"],
                    item["date_range"],
                    item["recipient"],
                    item["status"],
                ),
            )
        db_conn_logs_mock.commit()

        handler_logs = FakeHandler("/api/logs?limit=1&offset=2")
        with unittest.mock.patch("digest.get_db_conn", return_value=db_conn_logs_mock):
            handler_logs.do_GET()
        self.assertEqual(handler_logs.status_code, 200)
        self.assertEqual(handler_logs.json_sent["total"], 3)
        self.assertEqual(handler_logs.json_sent["limit"], 1)
        self.assertEqual(handler_logs.json_sent["offset"], 2)
        self.assertEqual(len(handler_logs.json_sent["logs"]), 1)
        self.assertEqual(handler_logs.json_sent["logs"][0]["id"], "l1")

    def test_scheduled_cron_dispatch(self):
        import sqlite3
        import unittest.mock

        from digest import dispatch_digest

        mock_send = unittest.mock.MagicMock(
            return_value={"status": "sent_simulated", "provider": "none"}
        )

        init_conn = sqlite3.connect("file:cron_db?mode=memory&cache=shared", uri=True)
        init_conn.row_factory = sqlite3.Row
        init_conn.execute(
            "CREATE TABLE interviews (id TEXT, candidate_name TEXT, role TEXT, interviewer_name TEXT, date TEXT, time TEXT, status TEXT, meeting_link TEXT, location TEXT)"
        )
        init_conn.execute(
            "CREATE TABLE sent_logs (id TEXT, timestamp TEXT, type TEXT, count INTEGER, date_range TEXT, recipient TEXT, status TEXT)"
        )
        init_conn.execute(
            "INSERT INTO interviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "int-1",
                "John Doe",
                "Engineer",
                "Sarah",
                "2026-07-15",
                "10:00",
                "Scheduled",
                None,
                None,
            ),
        )
        init_conn.commit()

        def get_shared_conn():
            c = sqlite3.connect("file:cron_db?mode=memory&cache=shared", uri=True)
            c.row_factory = sqlite3.Row
            return c

        with unittest.mock.patch("digest.get_db_conn", side_effect=get_shared_conn):
            with unittest.mock.patch("digest.send_digest_for_recipient", mock_send):
                result = dispatch_digest("daily", "2026-07-15")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["digest_result"]["interviews_count"], 1)
        mock_send.assert_called_once()

        cursor = init_conn.cursor()
        cursor.execute("SELECT * FROM sent_logs")
        logs = cursor.fetchall()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["type"], "Daily")
        self.assertEqual(logs[0]["count"], 1)
        self.assertEqual(logs[0]["recipient"], "digest-recipients@example.com")
        init_conn.close()


if __name__ == "__main__":
    unittest.main()
