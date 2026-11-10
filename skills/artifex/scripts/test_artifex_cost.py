"""Tests for artifex_cost.py. Run: python -m unittest test_artifex_cost -v"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifex_cost as ac  # noqa: E402


def jsonl(path: Path, rows) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def claude_msg(mid, t, read=1000, write=10, uncached=1, out=5):
    return {"type": "assistant", "timestamp": f"2026-11-10T10:{t}.000Z",
            "message": {"id": mid, "usage": {"input_tokens": uncached, "cache_read_input_tokens": read,
                                              "cache_creation_input_tokens": write, "output_tokens": out}}}


def codex_meta(tid, t, parent=None, nickname=None):
    payload = {"id": tid, "timestamp": f"2026-11-10T10:{t}.000Z"}
    if parent:
        payload.update(source={"subagent": {"thread_spawn": {"parent_thread_id": parent}}}, agent_nickname=nickname)
    return {"type": "session_meta", "timestamp": payload["timestamp"], "payload": payload}


def codex_count(t, inp, cached, out):
    usage = {"input_tokens": inp, "cached_input_tokens": cached, "cache_write_input_tokens": 0, "output_tokens": out}
    return {"timestamp": f"2026-11-10T10:{t}.000Z", "type": "event_msg",
            "payload": {"type": "token_count", "info": {"total_token_usage": usage, "last_token_usage": usage}}}


def event(seq, t, type_, **extra):
    return {"seq": seq, "ts": f"2026-11-10T10:{t}+00:00", "type": type_, **extra}


class CostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.claude, self.codex = root / "claude", root / "codex"
        self.initiative = root / "T-1"
        self.mdir = self.initiative / "milestones" / "M1"
        self.hosts = ac.Hosts(self.claude, self.codex)

    def tearDown(self):
        self.tmp.cleanup()

    def log(self, umbrella, agent=None):
        rows = [event(1, "00:00", "init", milestone="M1", ticket="T-1", umbrella_session=umbrella),
                event(2, "01:00", "dispatched", run_id="M1-P3-1", phase="P3", session_name="T-1 P3 implementation M1")]
        if agent:
            rows.append(event(3, "01:30", "started", run_id="M1-P3-1", agent=agent))
        rows.append(event(4, "05:00", "result", result={"run_id": "M1-P3-1", "status": "completed"}, problems=[]))
        jsonl(self.mdir / "run.jsonl", rows)

    def test_claude_umbrella_windows_agent_by_name_and_phase_session_by_title(self):
        proj = self.claude / "projects" / "D--repo"
        jsonl(proj / "u1.jsonl", [claude_msg("a", "00:30"), claude_msg("a", "00:31"),
                                  claude_msg("b", "02:00"), claude_msg("c", "06:00")])
        jsonl(proj / "u1" / "subagents" / "agent-x1.jsonl", [claude_msg("s", "01:40", read=50)])
        (proj / "u1" / "subagents" / "agent-x1.meta.json").write_text(
            json.dumps({"description": "T-1 P3 implementation M1"}), encoding="utf-8")
        jsonl(proj / "p1.jsonl", [claude_msg("p", "00:10", read=7)])
        (proj / "p1").mkdir()
        (proj / "p1" / "custom-title.json").write_text(json.dumps({"customTitle": "T-1 P1 research"}),
                                                        encoding="utf-8")
        self.initiative.mkdir(parents=True, exist_ok=True)
        (self.initiative / "state.json").write_text(json.dumps(
            {"sessions": {"T-1 P1 research": {"role": "P1", "session_id": "local_not-a-file"}}}), encoding="utf-8")
        self.log("u1")
        rep = ac.report(self.mdir, self.hosts, self.initiative)
        umbrella = rep["umbrella"][0]
        self.assertEqual(umbrella["total"]["turns"], 3)
        self.assertEqual([(w["window"], w["turns"]) for w in umbrella["windows"]],
                         [("1:init", 1), ("2:dispatched M1-P3-1", 1), ("4:result M1-P3-1=completed", 1)])
        run = rep["runs"]["M1-P3-1"]
        self.assertEqual((run["matched_by"], run["cache_read"]), ("session name", 50))
        session = rep["phase_sessions"]["T-1 P1 research"]
        self.assertEqual((session["matched_by"], session["cache_read"]), ("title", 7))
        self.assertEqual(rep["unresolved"], [])
        self.assertIn("Agent runs", ac.render(rep))

    def test_codex_running_totals_become_turns_and_children_link_by_parent(self):
        sessions = self.codex / "sessions" / "2026" / "11" / "10"
        jsonl(sessions / "rollout-2026-11-10T10-00-00-u2.jsonl", [
            codex_meta("u2", "00:00"),
            codex_count("00:30", 100, 60, 5), codex_count("00:30", 100, 60, 5),
            codex_count("02:00", 250, 200, 9)])
        jsonl(sessions / "rollout-2026-11-10T10-01-40-c1.jsonl", [
            codex_meta("c1", "01:40", parent="u2", nickname="worker"), codex_count("01:50", 40, 30, 2)])
        self.log("u2")
        rep = ac.report(self.mdir, self.hosts)
        umbrella = rep["umbrella"][0]
        self.assertEqual(umbrella["host"], "codex")
        self.assertEqual({k: umbrella["total"][k] for k in ("turns", "uncached", "cache_read", "output")},
                         {"turns": 2, "uncached": 50, "cache_read": 200, "output": 9})
        run = rep["runs"]["M1-P3-1"]
        self.assertEqual((run["matched_by"], run["uncached"], run["cache_read"]), ("time window", 10, 30))

    def test_recorded_agent_id_wins_and_missing_transcripts_are_listed(self):
        sessions = self.codex / "sessions" / "2026" / "11" / "10"
        jsonl(sessions / "rollout-2026-11-10T10-01-40-c9.jsonl", [codex_meta("c9", "01:40"),
                                                                 codex_count("01:50", 10, 0, 1)])
        self.log("gone", agent="c9")
        rep = ac.report(self.mdir, self.hosts)
        self.assertEqual(rep["runs"]["M1-P3-1"]["matched_by"], "agent id")
        self.assertEqual(rep["unresolved"], ["umbrella gone: not found"])


if __name__ == "__main__":
    unittest.main()
