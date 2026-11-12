"""Policy and boundary tests for the optional notification sender."""

from __future__ import annotations

import json
import io
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifex_notify as notify  # noqa: E402
import artifex_flow as flow  # noqa: E402


class Clock:
    def __init__(self):
        self.value = 1000.0

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class NotifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.clock = Clock()
        self.sent = []

    def tearDown(self):
        self.temp.cleanup()

    def sender(self, transport=None):
        return notify.Notifier(self.root, "TASK-1", "alpha", env={"ARTIFEX_GOOGLE_CHAT_WEBHOOK_URL":
                            "https://chat.googleapis.com/v1/spaces/x/messages?key=canary&token=secret"},
                               clock=self.clock, sleep=self.clock.sleep,
                               transport=transport or self.transport)

    def transport(self, url, body, timeout):
        self.sent.append((url, json.loads(body), timeout))
        return 200, {}, b"ok"

    def event(self, key="task-run-1/started", kind="started", summary="started"):
        return {"key": key, "kind": kind, "task": "implementation", "summary": summary}

    def test_disabled_does_not_create_database(self):
        sender = notify.Notifier(self.root, "TASK-1", "alpha", env={}, clock=self.clock)
        self.assertEqual(sender.send(self.event()), "disabled")
        self.assertFalse((self.root / "notifications.sqlite3").exists())

    def test_reservation_survives_failure_restart_and_same_key(self):
        def fail(*_):
            raise OSError("secret=do-not-store")
        self.assertEqual(self.sender(fail).send(self.event()), "failed")
        self.assertEqual(self.sender().send(self.event()), "duplicate")
        db = sqlite3.connect(self.root / "notifications.sqlite3")
        try:
            saved = repr(db.execute("select * from events").fetchall())
        finally:
            db.close()
        self.assertNotIn("do-not-store", saved)
        self.assertEqual(self.sent, [])

    def test_valid_send_uses_safe_message_and_same_semantic_key_dedupes(self):
        sender = self.sender()
        self.assertEqual(sender.send(self.event()), "sent")
        self.assertEqual(sender.send(self.event()), "duplicate")
        self.assertEqual(len(self.sent), 1)
        body = self.sent[0][1]["text"]
        self.assertIn("TASK-1", body)
        self.assertIn("UTC", body)
        self.assertIn("+07:00", body)
        self.assertNotIn("secret", body)
        self.assertLessEqual(len(body.encode()), 4096)

    def test_message_redacts_canaries_in_supplied_fields(self):
        body = notify.format_message(self.event(summary="token=canary key=other"),
                                     "TASK-1", "alpha")
        self.assertNotIn("canary", body)
        self.assertNotIn("other", body)
        self.assertIn("token=[redacted]", body)

    def test_attempt_spacing_and_rolling_cap(self):
        sender = self.sender(lambda *_: (503, {}, b""))
        self.assertEqual(sender.send(self.event("task-a")), "failed")
        self.assertEqual(sender.send(self.event("task-b")), "failed")
        self.assertGreaterEqual(self.clock.value, 1001.0)
        outcomes = [sender.send(self.event(f"task-c{i}")) for i in range(6)]
        self.assertIn("suppressed", outcomes)
        db = sqlite3.connect(self.root / "notifications.sqlite3")
        try:
            self.assertLessEqual(db.execute("select count(*) from attempts").fetchone()[0], 10)
        finally:
            db.close()

    def test_retry_is_bounded_and_respects_attempt_spacing(self):
        attempts = []
        def retry_once(url, body, timeout):
            attempts.append(self.clock.value)
            return (503, {}, b"") if len(attempts) == 1 else (200, {}, b"")
        self.assertEqual(self.sender(retry_once).send(self.event()), "sent")
        self.assertEqual(len(attempts), 2)
        self.assertGreaterEqual(attempts[1] - attempts[0], 1.0)

    def test_invalid_destination_does_not_reach_transport(self):
        called = []
        sender = notify.Notifier(self.root, "TASK-1", "alpha", env={
            "ARTIFEX_GOOGLE_CHAT_WEBHOOK_URL": "https://example.test/?token=secret"},
            clock=self.clock, transport=lambda *a: called.append(a))
        self.assertEqual(sender.send(self.event()), "invalid")
        self.assertEqual(called, [])

    def test_ledger_path_failure_skips_network_and_returns_sanitized_status(self):
        blocked = self.root / "not-a-directory"
        blocked.write_text("occupied", encoding="utf-8")
        called = []
        sender = notify.Notifier(blocked / "initiative", "TASK-1", "alpha", env={
            "ARTIFEX_GOOGLE_CHAT_WEBHOOK_URL":
            "https://chat.googleapis.com/v1/spaces/x/messages?key=canary&token=secret"},
            transport=lambda *args: called.append(args))
        output = io.StringIO()
        with mock.patch.object(notify.sys, "stderr", output):
            self.assertEqual(sender.send(self.event()), "ledger_error")
        self.assertEqual(called, [])
        self.assertIn("delivery ledger unavailable", output.getvalue())
        self.assertNotIn("secret", output.getvalue())

    def test_concurrent_duplicate_has_one_delivery(self):
        sender1, sender2 = self.sender(), self.sender()
        barrier = threading.Barrier(2)
        results = []
        def run(sender):
            barrier.wait()
            results.append(sender.send(self.event()))
        threads = [threading.Thread(target=run, args=(s,)) for s in (sender1, sender2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertCountEqual(results, ["sent", "duplicate"])
        self.assertEqual(len(self.sent), 1)

    def test_redirect_refused_and_secret_not_emitted(self):
        calls = []
        sender = self.sender(lambda *args: (calls.append(args) or
                                            (302, {"Location": "https://example.test"}, b"token=secret")))
        self.assertEqual(sender.send(self.event()), "failed")
        self.assertEqual(len(calls), 1)

    def test_subprocess_hard_timeout(self):
        with mock.patch.object(notify.subprocess, "run", side_effect=subprocess.TimeoutExpired("test", 0.1)):
            with self.assertRaises(TimeoutError):
                notify._supervised_transport("https://chat.googleapis.com/v1/spaces/x/messages?key=a&token=b",
                                             b"{}", 0.1)

    def test_loopback_transport_does_not_follow_redirect_or_expose_body(self):
        hits = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                hits.append(self.path)
                self.send_response(302)
                self.send_header("Location", "/elsewhere")
                self.end_headers()
                self.wfile.write(b"token=remote-secret")
            def log_message(self, *_):
                pass
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, _, _ = notify._http_transport(
                f"http://127.0.0.1:{server.server_port}/hook", b"{}", 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        self.assertEqual(status, 302)
        self.assertEqual(hits, ["/hook"])

    def test_router_adapter_only_sees_committed_transitions(self):
        mdir = self.root / "milestones" / "alpha"
        session = flow.Session(mdir, must_exist=False)
        session.record({"type": "init", "milestone": "alpha", "ticket": "TASK-1"})
        def committed(*_):
            self.assertIn('"type": "started"', (mdir / "run.jsonl").read_text(encoding="utf-8"))
            return "sent"
        with mock.patch.object(notify, "send_event", side_effect=committed) as send:
            session.record({"type": "dispatched", "run_id": "run-start-1", "phase": "implementation"})
            send.assert_not_called()
            session.record({"type": "started", "run_id": "run-start-1"})
            send.assert_called_once()

    def test_delivery_exception_does_not_undo_committed_router_event(self):
        mdir = self.root / "milestones" / "alpha"
        session = flow.Session(mdir, must_exist=False)
        session.record({"type": "init", "milestone": "alpha", "ticket": "TASK-1"})
        session.record({"type": "dispatched", "run_id": "run-start-1", "phase": "implementation"})
        error_output = io.StringIO()
        with mock.patch.object(notify, "send_event", side_effect=RuntimeError("token=canary")):
            with mock.patch.object(notify.sys, "stderr", error_output):
                session.record({"type": "started", "run_id": "run-start-1"})
        self.assertEqual(session.state["active"]["run-start-1"]["started"], True)
        self.assertIn('"type": "started"', (mdir / "run.jsonl").read_text(encoding="utf-8"))
        self.assertNotIn("canary", error_output.getvalue())


if __name__ == "__main__":
    unittest.main()
