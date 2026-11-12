#!/usr/bin/env python3
"""Best-effort Google Chat notifications for committed Artifex events."""

from __future__ import annotations

import argparse
import email.utils
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENV_NAME = "ARTIFEX_GOOGLE_CHAT_WEBHOOK_URL"
DB_NAME = "notifications.sqlite3"
ATTEMPT_TIMEOUT = 2.0
WALL_BUDGET = 6.0
MAX_ATTEMPTS = 2
MAX_PER_MINUTE = 10
MIN_SPACING = 1.0
SENSITIVE_RE = re.compile(r"(?i)\b(token|key|secret|password|credential)\s*[=:]\s*[^\s&]+")
CHAT_URL_RE = re.compile(r"https://chat\.googleapis\.com/[^\s]+", re.I)


def _safe(value) -> str:
    text = str(value)
    text = CHAT_URL_RE.sub("[redacted webhook]", text)
    return SENSITIVE_RE.sub(r"\1=[redacted]", text)


def _credentials(url: str) -> tuple[str, ...]:
    try:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        return tuple(value for name in ("key", "token") for value in query.get(name, ()) if value)
    except ValueError:
        return ()


def _safe_with_secrets(value, secrets: tuple[str, ...]) -> str:
    text = _safe(value)
    for secret in secrets:
        text = text.replace(secret, "[redacted]")
    return text


def valid_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        return (parsed.scheme == "https" and parsed.hostname == "chat.googleapis.com" and
                re.fullmatch(r"/v1/spaces/[^/]+/messages", parsed.path) is not None and
                bool(urllib.parse.parse_qs(parsed.query).get("key")) and
                bool(urllib.parse.parse_qs(parsed.query).get("token")))
    except ValueError:
        return False


def format_message(event: dict, ticket: str, milestone: str, now: datetime | None = None,
                   secrets: tuple[str, ...] = ()) -> str:
    instant = now or datetime.now(timezone.utc)
    utc = instant.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    local = instant.astimezone()
    zone = local.tzname() or "local"
    offset = local.strftime("%z")
    if len(offset) == 5:
        offset = offset[:3] + ":" + offset[3:]
    local_text = local.strftime("%Y-%m-%d %H:%M:%S ") + offset + f" {zone}"
    fields = [_safe_with_secrets(event.get("kind", "event"), secrets).replace("_", " "),
              f"Ticket: {_safe_with_secrets(ticket, secrets)}",
              f"Milestone: {_safe_with_secrets(milestone, secrets)}",
              f"Task: {_safe_with_secrets(event.get('task', 'workflow'), secrets)}",
              f"Time: {utc} / {local_text}"]
    summary = _safe_with_secrets(event.get("summary", ""), secrets)[:1000]
    if summary:
        fields.append(summary)
    source = event.get("source")
    if isinstance(source, str) and source.startswith("https://") and len(source) <= 500:
        fields.append(_safe_with_secrets(source, secrets))
    text = "\n".join(fields)
    while len(text.encode("utf-8")) > 4096:
        index = max((i for i, field in enumerate(fields) if field), key=lambda i: len(fields[i].encode("utf-8")))
        encoded = fields[index].encode("utf-8")
        fields[index] = encoded[:max(0, len(encoded) - max(1, len(text.encode("utf-8")) - 4096))].decode("utf-8", "ignore")
        text = "\n".join(fields)
    return text


def _connect(root: Path):
    db = sqlite3.connect(root / DB_NAME, timeout=1.0, isolation_level=None)
    db.execute("PRAGMA busy_timeout=1000")
    db.execute("CREATE TABLE IF NOT EXISTS events (event_key TEXT PRIMARY KEY, status TEXT NOT NULL, created REAL NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS attempts (at REAL NOT NULL)")
    return db


def _http_transport(url: str, body: bytes, timeout: float):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, body, {"Content-Type": "application/json"}, method="POST")
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, response.headers, response.read(1024)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, b""


def _supervised_transport(url: str, body: bytes, timeout: float):
    payload = json.dumps({"body": body.decode("utf-8"), "timeout": timeout})
    child_env = {ENV_NAME: url}
    for name in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"):
        if os.environ.get(name):
            child_env[name] = os.environ[name]
    try:
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker"],
                              input=payload, text=True, capture_output=True, timeout=timeout,
                              env=child_env, check=False)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("delivery worker timed out") from exc
    if proc.returncode != 0:
        raise OSError("delivery worker failed")
    try:
        result = json.loads(proc.stdout)
        return result["status"], result.get("headers", {}), b""
    except (json.JSONDecodeError, KeyError, TypeError):
        raise OSError("delivery worker failed") from None


class Notifier:
    def __init__(self, root: Path, ticket: str, milestone: str, *, env=None, clock=time.monotonic,
                 sleep=time.sleep, transport=None):
        self.root, self.ticket, self.milestone = Path(root), ticket, milestone
        self.env = os.environ if env is None else env
        self.clock, self.sleep = clock, sleep
        self.transport = transport or _supervised_transport

    def send(self, event: dict) -> str:
        url = self.env.get(ENV_NAME)
        if not url:
            return "disabled"
        key = str(event.get("key", ""))
        secrets = _credentials(url)
        if not key or len(key) > 500 or _safe(key) != key or any(secret in key for secret in secrets):
            return "invalid"
        db = None
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            db = _connect(self.root)
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("INSERT INTO events VALUES (?, 'reserved', ?)", (key, self.clock()))
            except sqlite3.IntegrityError:
                db.execute("ROLLBACK")
                return "duplicate"
            db.execute("COMMIT")
            if not valid_url(url):
                db.execute("UPDATE events SET status='invalid' WHERE event_key=?", (key,))
                return "invalid"
            deadline = self.clock() + WALL_BUDGET
            safe_event = {name: _safe_with_secrets(value, secrets) if value is not None else None
                          for name, value in event.items()}
            body = json.dumps({"text": format_message(safe_event, self.ticket, self.milestone,
                                                       secrets=secrets)},
                              ensure_ascii=False).encode("utf-8")
            result = "failed"
            for index in range(MAX_ATTEMPTS):
                while True:
                    delay = self._reserve_attempt(db, deadline)
                    if delay is None:
                        result = "suppressed"
                        break
                    if delay:
                        self.sleep(delay)
                        continue
                    break
                if result == "suppressed":
                    break
                remaining = deadline - self.clock()
                if remaining <= 0:
                    break
                try:
                    status, headers, _ = self.transport(url, body, min(ATTEMPT_TIMEOUT, remaining))
                except Exception:
                    status, headers = 0, {}
                if 200 <= status < 300:
                    result = "sent"
                    break
                retryable = status == 0 or status == 429 or status >= 500
                if index + 1 >= MAX_ATTEMPTS or not retryable:
                    break
                retry_after = _retry_after(headers)
                delay = max(1.0, retry_after or 0.0)
                if self.clock() + delay >= deadline:
                    break
                self.sleep(delay)
            db.execute("UPDATE events SET status=? WHERE event_key=?", (result, key))
            return result
        except (sqlite3.Error, OSError):
            print("artifex notification skipped: delivery ledger unavailable", file=sys.stderr)
            return "ledger_error"
        finally:
            if db is not None:
                db.close()

    def _reserve_attempt(self, db, deadline):
        while True:
            now = self.clock()
            if now >= deadline:
                return None
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM attempts WHERE at <= ?", (now - 60.0,))
            rows = db.execute("SELECT at FROM attempts ORDER BY at DESC LIMIT 1").fetchone()
            count = db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            delay = max(0.0, rows[0] + MIN_SPACING - now) if rows else 0.0
            if count >= MAX_PER_MINUTE or now + delay >= deadline:
                db.execute("ROLLBACK")
                return None
            if delay:
                db.execute("ROLLBACK")
                return delay
            db.execute("INSERT INTO attempts VALUES (?)", (now,))
            db.execute("COMMIT")
            return 0.0


def _retry_after(headers):
    try:
        value = float(headers.get("Retry-After", ""))
        return max(0.0, min(value, WALL_BUDGET))
    except (TypeError, ValueError):
        try:
            when = email.utils.parsedate_to_datetime(headers.get("Retry-After", ""))
            return max(0.0, min((when - datetime.now(when.tzinfo or timezone.utc)).total_seconds(), WALL_BUDGET))
        except (TypeError, ValueError, OverflowError):
            return None


def send_event(root: Path, ticket: str, milestone: str, event: dict) -> str:
    return Notifier(root, ticket, milestone).send(event)


def notify_committed(session, event: dict, checkpoints: list, suppress: bool = False) -> None:
    """Adapt only durable router transitions into notification events."""
    if suppress:
        return
    state = session.state
    ticket, milestone = state.get("ticket", "unknown"), state.get("milestone", "unknown")
    from artifex_flow import PHASES

    notice = None
    if event.get("type") == "started":
        run = state.get("active", {}).get(event.get("run_id"), {})
        task = PHASES.get(run.get("phase"), {}).get("name", "workflow")
        notice = {"key": f"{event['run_id']}/started", "kind": "started",
                  "task": task, "summary": "Task started"}
    elif event.get("type") == "result" and not any(cp.get("kind") == "result_rejected" for cp in checkpoints):
        result = event["result"]
        task = PHASES.get(result.get("phase"), {}).get("name", "workflow")
        notice = {"key": f"{result['run_id']}/finished", "kind": "finished",
                  "task": task, "summary": f"Outcome: {str(result['status']).replace('_', ' ')}"}
    if notice:
        try:
            _warn_status(send_event(session.mdir.resolve().parent.parent, ticket, milestone, notice))
        except Exception:
            print("artifex notification skipped: sender unavailable", file=sys.stderr)
    if any(cp.get("halted") for cp in checkpoints):
        cp = next(cp for cp in checkpoints if cp.get("halted"))
        result = event.get("result", {})
        episode = cp.get("run_id") or result.get("run_id") or "episode"
        try:
            _warn_status(send_event(session.mdir.resolve().parent.parent, ticket, milestone,
                                    {"key": f"halt/{cp['kind']}/{episode}",
                                     "kind": "blocker", "task": event.get("phase", "workflow"),
                                     "summary": cp.get("message", "Workflow halted")}))
        except Exception:
            print("artifex notification skipped: sender unavailable", file=sys.stderr)


def _warn_status(status: str) -> None:
    if status in {"failed", "suppressed", "invalid", "ledger_error"}:
        print(f"artifex notification skipped: {status}", file=sys.stderr)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv == ["--worker"]:
        request = json.load(sys.stdin)
        try:
            status, headers, _ = _http_transport(os.environ[ENV_NAME], request["body"].encode("utf-8"),
                                                  min(float(request["timeout"]), ATTEMPT_TIMEOUT))
            safe_headers = {"Retry-After": headers.get("Retry-After", "")} if headers else {}
            json.dump({"status": status, "headers": safe_headers}, sys.stdout)
            return 0
        except Exception:
            return 1
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, required=True, help="initiative artifact folder")
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--milestone", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--kind", choices=("started", "finished", "approval-needed", "blocker"), required=True)
    parser.add_argument("--task", default="workflow")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--source")
    args = parser.parse_args(argv)
    status = send_event(args.dir, args.ticket, args.milestone,
                        {"key": args.key, "kind": args.kind, "task": args.task,
                         "summary": args.summary, "source": args.source})
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
