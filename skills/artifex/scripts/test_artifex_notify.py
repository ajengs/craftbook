"""Policy and boundary tests for the optional notification sender."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifex_notify as notify  # noqa: E402
import artifex_flow as flow  # noqa: E402
from test_artifex_flow import GitRepo, git  # noqa: E402


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
                               clock=self.clock, rate_clock=self.clock, sleep=self.clock.sleep,
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

    def test_configured_credentials_are_redacted_and_rejected_from_keys(self):
        sender = self.sender()
        token = "secret"
        key = "canary"
        self.assertEqual(sender.send(self.event(key="issue/" + token,
                                                summary="credential " + key)), "invalid")
        self.assertEqual(sender.send(self.event(key="safe", summary="credential " + key)), "sent")
        self.assertNotIn(key, self.sent[0][1]["text"])
        db = sqlite3.connect(self.root / "notifications.sqlite3")
        try:
            self.assertNotIn(token, repr(db.execute("select event_key from events").fetchall()))
        finally:
            db.close()

    def test_message_size_bound_handles_large_fixed_and_multibyte_fields(self):
        text = notify.format_message({"kind": "started", "task": "界" * 5000,
                                      "summary": "é" * 5000}, "TASK-1", "alpha")
        self.assertLessEqual(len(text.encode("utf-8")), 4096)

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

    def test_persisted_attempt_rate_limit_survives_monotonic_clock_reset(self):
        url = "https://chat.googleapis.com/v1/spaces/x/messages?key=canary&token=secret"
        wall_clock = Clock()
        wall_clock.value = 178023.5
        first_boot_clock = Clock()
        first_boot_clock.value = 178023.5
        first = notify.Notifier(self.root, "TASK-1", "alpha", env={notify.ENV_NAME: url},
                                clock=first_boot_clock, rate_clock=wall_clock,
                                sleep=first_boot_clock.sleep, transport=self.transport)
        self.assertEqual(first.send(self.event("before-reboot")), "sent")

        second_boot_clock = Clock()
        second_boot_clock.value = 4367.4
        wall_clock.value += 1.1
        second = notify.Notifier(self.root, "TASK-1", "alpha", env={notify.ENV_NAME: url},
                                 clock=second_boot_clock, rate_clock=wall_clock,
                                 sleep=second_boot_clock.sleep, transport=self.transport)
        self.assertEqual(second.send(self.event("after-reboot")), "sent")
        self.assertEqual(len(self.sent), 2)
        db = sqlite3.connect(self.root / "notifications.sqlite3")
        try:
            attempts = [row[0] for row in db.execute("select at from attempts order by at")]
        finally:
            db.close()
        self.assertEqual(len(attempts), 2)
        self.assertGreaterEqual(attempts[1] - attempts[0], 1.0)

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

    def test_loopback_http_retries_quota_and_server_errors_only(self):
        responses = {"event-0": [429, 200], "event-1": [503, 200], "event-2": [400]}
        attempts = {}
        hits = []
        started = time.monotonic()

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                event = body["text"].rsplit("\n", 1)[-1]
                attempt = attempts.get(event, 0)
                attempts[event] = attempt + 1
                sequence = responses[event]
                status = sequence[min(attempt, len(sequence) - 1)]
                hits.append({"event": event, "attempt": attempt + 1, "status": status,
                             "at": time.monotonic() - started})
                self.send_response(status)
                if status == 429:
                    self.send_header("Retry-After", "0")
                self.end_headers()
            def log_message(self, *_):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        local_url = f"http://127.0.0.1:{server.server_port}/hook"
        env = {notify.ENV_NAME:
               "https://chat.googleapis.com/v1/spaces/test/messages?key=test&token=test"}
        try:
            sender = notify.Notifier(self.root, "TASK-1", "alpha", env=env,
                                     transport=lambda _url, body, timeout:
                                     notify._http_transport(local_url, body, timeout))
            outcomes = [sender.send(self.event(key=f"http-status-{index}", summary=f"event-{index}"))
                        for index in range(3)]
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        self.assertEqual(outcomes, ["sent", "sent", "failed"], hits)
        self.assertEqual([(hit["event"], hit["attempt"], hit["status"]) for hit in hits],
                         [("event-0", 1, 429), ("event-0", 2, 200),
                          ("event-1", 1, 503), ("event-1", 2, 200),
                          ("event-2", 1, 400)])

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

    def test_validated_completion_emits_finished_after_commit(self):
        repo_root = self.root / "repo"
        repo_root.mkdir()
        repo = GitRepo(repo_root)
        mdir = self.root / "initiative" / "milestones" / "alpha"
        mdir.mkdir(parents=True)
        handoff = mdir / "implementation-handoff.md"
        handoff.write_text(f"---\nbranch: feature\nworkdir: {repo.work}\ntarget: main\ndepends_on: none\n---\n",
                           encoding="utf-8")
        payloads = []

        def captured(url, body, timeout):
            payload = json.loads(body)
            if payload["text"].startswith("finished"):
                self.assertIn('"type": "result"', (mdir / "run.jsonl").read_text(encoding="utf-8"))
                self.assertFalse(flow.Session(mdir).state["active"])
            payloads.append(payload)
            return 200, {}, b"ok"

        def invoke(*args):
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = flow.main([*args, "--dir", str(mdir)])
            self.assertEqual(code, 0, errors.getvalue())
            return output.getvalue() if args[0] == "status" else json.loads(output.getvalue())

        webhook = "https://chat.googleapis.com/v1/spaces/test/messages?key=test&token=test"
        with mock.patch.dict(os.environ, {notify.ENV_NAME: webhook}), \
                mock.patch.object(notify, "_supervised_transport", side_effect=captured):
            invoke("init", "--milestone", "alpha", "--ticket", "TASK-1")
            invoke("handoff", "--kind", "implementation", str(handoff))
            self.assertEqual(payloads, [])
            session = flow.Session(mdir)
            run_id = next(iter(session.state["active"]))
            invoke("event", "started", "--run-id", run_id)
            invoke("next")
            invoke("status")
            invoke("runs")
            self.assertEqual(len(payloads), 1)
            head = repo.commit("feature.py", "value = 1\n", "feature")
            git(repo.work, "push", "-q", "origin", "feature")
            result_file = mdir / "results" / f"{run_id}.json"
            result_file.parent.mkdir(parents=True, exist_ok=True)
            result_file.write_text(json.dumps({"run_id": run_id, "phase": "P3", "status": "completed",
                                                "head": head, "pr_url": "https://example.test/pr/1"}),
                                   encoding="utf-8")
            result = invoke("result", str(result_file))

        self.assertEqual([checkpoint["kind"] for checkpoint in result["checkpoints"]], ["pr_opened"])
        self.assertNotIn(run_id, flow.Session(mdir).state["active"])
        self.assertEqual(len(payloads), 2)
        self.assertIn("started", payloads[0]["text"])
        self.assertIn("Ticket: TASK-1", payloads[1]["text"])
        self.assertIn("Milestone: alpha", payloads[1]["text"])
        self.assertIn("finished", payloads[1]["text"])
        self.assertIn("Outcome: completed", payloads[1]["text"])

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

    def test_dry_run_suppresses_committed_event_notification(self):
        mdir = self.root / "milestones" / "alpha"
        session = flow.Session(mdir, must_exist=False)
        session.record({"type": "init", "milestone": "alpha", "ticket": "TASK-1"})
        session.record({"type": "dispatched", "run_id": "run-start-1", "phase": "implementation"})
        with mock.patch.object(notify, "send_event") as send:
            with mock.patch.object(flow, "Session", return_value=session):
                with mock.patch.object(flow, "load_siblings", return_value=[]):
                    flow.main(["event", "started", "--run-id", "run-start-1", "--dir", str(mdir), "--dry-run"])
            send.assert_not_called()

    def test_repeated_rejected_result_uses_same_blocker_key(self):
        mdir = self.root / "milestones" / "alpha"
        session = flow.Session(mdir, must_exist=False)
        session.record({"type": "init", "milestone": "alpha", "ticket": "TASK-1"})
        session.record({"type": "dispatched", "run_id": "run-1", "phase": "P3"})
        session.record({"type": "started", "run_id": "run-1"})
        event = {"type": "result", "result": {"run_id": "run-1", "phase": "P3", "status": "completed"},
                 "problems": ["missing head"]}
        keys = []
        def capture(root, ticket, milestone, notice):
            if notice["kind"] == "blocker":
                keys.append(notice["key"])
            return "sent"
        with mock.patch.object(notify, "send_event", side_effect=capture):
            session.record(event)
            session.record(event)
        self.assertEqual(keys, ["halt/result_rejected/run-1", "halt/result_rejected/run-1"])

    def test_non_run_halt_reuses_identity_until_resolution_then_renews_it(self):
        mdir = self.root / "milestones" / "alpha"
        session = flow.Session(mdir, must_exist=False)
        session.record({"type": "init", "milestone": "alpha", "ticket": "TASK-1"})
        keys = []
        with mock.patch.object(notify, "send_event", side_effect=lambda _root, _ticket, _milestone, notice:
                               keys.append(notice["key"]) or "sent"):
            session.record({"type": "handoff", "kind": "implementation", "path": "handoff.md",
                            "sha256": "h1", "fields": {"branch": "work", "workdir": "D:/work",
                            "target": "main", "depends_on": []}, "target_ahead": {"commits": 1}})
            self.assertTrue(session.state["halt"])
            session.record({"type": "context", "fields": {"target": "main"},
                            "target_ahead": {"commits": 2}})
            session.record({"type": "resume", "note": "Resolved first target episode"})
            self.assertFalse(session.state["halt"])
            session.record({"type": "context", "fields": {"target": "main"},
                            "target_ahead": {"commits": 2}})
        self.assertEqual(len(keys), 3)
        self.assertTrue(keys[0].startswith("halt/target_unpushed/"))
        self.assertTrue(keys[1].startswith("halt/target_unpushed/"))
        self.assertTrue(keys[2].startswith("halt/target_unpushed/"))
        self.assertEqual(keys[0], keys[1])
        self.assertNotEqual(keys[1], keys[2])


if __name__ == "__main__":
    unittest.main()
