"""Tests for artifex_state.py. Run: python -m unittest test_artifex_state -v"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifex_flow as af  # noqa: E402
import artifex_state as st  # noqa: E402


class StateCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "CRAFT-1"
        self.cli("init", "--ticket", "CRAFT-1", "--title", "Version flag")

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, expect=0):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = st.main(["--dir", str(self.dir), *args])
        self.assertEqual(code, expect, err.getvalue())
        text = out.getvalue()
        return json.loads(text) if expect == 0 and (args[0] != "render" or "--out" in args) else text

    def state(self):
        return json.loads((self.dir / "state.json").read_text(encoding="utf-8"))

    def test_set_replaces_fields_instead_of_appending(self):
        self.cli("set", "status", "phase=P2", "next=Approve the specs")
        rev = self.cli("set", "status", "phase=P3", "status=implementing", "next=")["revision"]
        self.assertEqual(self.state()["status"], {"phase": "P3", "status": "implementing"})
        self.assertEqual(rev, 3)

    def test_upsert_merges_one_row_and_json_values_parse(self):
        self.cli("upsert", "artifacts", "specs-M1", "path=milestones/M1/specs.md", "sha256=abc")
        self.cli("upsert", "artifacts", "specs-M1", "decision=written", 'affects:=["handoff"]')
        self.assertEqual(self.state()["artifacts"]["specs-M1"],
                         {"path": "milestones/M1/specs.md", "sha256": "abc", "decision": "written",
                          "affects": ["handoff"]})

    def test_remove_and_decide(self):
        self.cli("upsert", "blockers", "gh-auth", "text=gh is not authenticated")
        self.cli("remove", "blockers", "gh-auth")
        self.cli("decide", "Version 1.0.0", "--artifact", "analysis")
        state = self.state()
        self.assertEqual(state["blockers"], {})
        self.assertEqual(state["decisions"][0]["text"], "Version 1.0.0")

    def test_unknown_fields_sections_and_statuses_are_refused_without_writing(self):
        before = self.state()["revision"]
        self.cli("set", "status", "colour=red", expect=2)
        self.cli("set", "nope", "a=b", expect=2)
        self.cli("set", "status", "status=done-ish", expect=2)
        self.cli("upsert", "tables", "x", expect=2)
        self.cli("remove", "blockers", "missing", expect=2)
        self.assertEqual(self.state()["revision"], before)

    def test_milestone_status_is_refused_once_the_router_runs_it(self):
        self.cli("upsert", "milestones", "M1", "scope=x", "status=draft")
        mdir = self.dir / "milestones" / "M1"
        mdir.mkdir(parents=True)
        with contextlib.redirect_stdout(io.StringIO()):
            af.main(["init", "--dir", str(mdir), "--milestone", "M1", "--ticket", "CRAFT-1"])
        self.cli("upsert", "milestones", "M1", "status=implementing", expect=2)
        self.cli("upsert", "milestones", "M1", "scope=y")
        self.assertIn("| M1 | y | router: running |", self.cli("render"))

    def test_render_shows_latest_state_and_router_status(self):
        self.cli("set", "status", "phase=P2", "next=stale step")
        self.cli("set", "status", "next=Approve the specs")
        self.cli("upsert", "milestones", "M1", "scope=version flag")
        mdir = self.dir / "milestones" / "M1"
        mdir.mkdir(parents=True)
        with contextlib.redirect_stdout(io.StringIO()):
            af.main(["init", "--dir", str(mdir), "--milestone", "M1", "--ticket", "CRAFT-1"])
        text = self.cli("render")
        self.assertIn("- Next: Approve the specs", text)
        self.assertNotIn("stale step", text)
        self.assertIn("### Router — M1", text)
        self.assertIn("no implementation handoff recorded", text)
        out = self.cli("render", "--out", str(self.dir / "STATE.md"))
        self.assertTrue(Path(out["written"]).exists())


class HostTests(unittest.TestCase):
    def test_claude_code_reports_its_transcript_and_app_ids(self):
        host = st.detect_host({"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "abc",
                               "CLAUDE_CODE_HOST_SESSION_ID": "local_x", "CODEX_HOME": "c"})
        self.assertEqual((host["host"], host["session_id"], host["host_session_id"]), ("claude-code", "abc", "local_x"))

    def test_codex_needs_a_codex_variable_other_than_codex_home(self):
        self.assertEqual(st.detect_host({"CODEX_HOME": "c"})["host"], "unknown")
        host = st.detect_host({"CODEX_SANDBOX": "seatbelt", "CODEX_THREAD_ID": "t1"})
        self.assertEqual((host["host"], host["session_id"]), ("codex", "t1"))

    def test_override_wins(self):
        self.assertEqual(st.detect_host({"ARTIFEX_HOST": "codex"})["host"], "codex")


class DocTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "T-1"
        StateCliTests.cli(self, "init", "--ticket", "T-1")

    def tearDown(self):
        self.tmp.cleanup()

    cli = StateCliTests.cli
    state = StateCliTests.state

    def test_surface_follows_the_host(self):
        claude = self.cli("doc", "surface", "kickoff", "--host", "claude-code")
        self.assertEqual((claude["surface"], claude["document"]), ("claude-docs", "kickoff"))
        self.assertTrue(any("file pane" in step for step in claude["steps"]))
        codex = self.cli("doc", "surface", "specs", "--milestone", "M1", "--host", "codex")
        self.assertEqual(codex["surface"], "local-file")
        self.assertTrue(codex["path"].endswith(str(Path("milestones/M1/specs.md"))))
        self.assertTrue(any("Pages" in step for step in codex["steps"]))
        self.assertEqual(Path(codex["session_setup"]["workspace_folder"]), self.dir.resolve())
        self.assertNotIn("session_setup", claude)
        self.assertTrue(any("Waiting on you" in rule for rule in claude["review_message"]))
        self.assertEqual(self.cli("doc", "surface", "kickoff", "--host", "other")["surface"], "choose")
        self.cli("doc", "surface", "specs", "--host", "codex", expect=2)

    def test_approve_hashes_the_file_and_checks_the_surface(self):
        (self.dir / "kickoff.md").write_text("# Kickoff\n", encoding="utf-8")
        self.cli("doc", "approve", "kickoff", "--host", "claude-code", "--surface", "local-file", expect=2)
        self.cli("doc", "approve", "kickoff", "--host", "claude-code", "--surface", "claude-docs", expect=2)
        out = self.cli("doc", "approve", "kickoff", "--host", "claude-code", "--surface", "claude-docs",
                       "--url", "https://claude.ai/artifact/x")
        row = self.state()["artifacts"]["kickoff"]
        self.assertEqual((row["decision"], row["surface"], row["sha256"]), ("approved", "claude-docs", out["sha256"]))

    def test_fallback_is_recorded_and_missing_files_refused(self):
        self.cli("doc", "approve", "analysis", "--host", "codex", "--surface", "local-file", expect=2)
        (self.dir / "analysis.md").write_text("x\n", encoding="utf-8")
        self.cli("doc", "approve", "analysis", "--host", "codex", "--surface", "chat",
                 "--fallback", "viewer would not open")
        self.assertEqual(self.state()["artifacts"]["analysis"]["fallback"], "viewer would not open")

    def test_approvals_only_through_doc_approve(self):
        self.cli("upsert", "artifacts", "kickoff", "decision=approved", expect=2)
        self.cli("upsert", "artifacts", "handoff-M1", "decision=written", "sha256=abc")


class BriefTests(unittest.TestCase):
    QUESTION = "Do you authorize the umbrella and every phase session to exchange coordination messages?"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "T-1"
        request = Path(self.tmp.name) / "request.txt"
        request.write_text('/artifex Ticket T-1. Add "--version" for $USER\nsecond line\n', encoding="utf-8")
        self.cli("init", "--ticket", "T-1", "--request-file", str(request))

    def tearDown(self):
        self.tmp.cleanup()

    cli = StateCliTests.cli
    state = StateCliTests.state

    def consent(self, status="authorized", response="yes"):
        reply = Path(self.tmp.name) / "reply.txt"
        reply.write_text(response, encoding="utf-8")
        self.cli("consent", "--status", status, "--question", self.QUESTION, "--response-file", str(reply),
                 "--source", "umbrella chat", "--route", "local_u")

    def brief(self, *args, expect=0):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = st.main(["--dir", str(self.dir), "brief", *args])
        self.assertEqual(code, expect, err.getvalue())
        return out.getvalue()

    def test_brief_quotes_request_question_and_reply_verbatim(self):
        self.consent()
        text = self.brief("P1")
        self.assertIn('> /artifex Ticket T-1. Add "--version" for $USER\n> second line', text)
        self.assertIn(f"> {self.QUESTION}", text)
        self.assertIn("The user replied, verbatim:\n> yes", text)
        self.assertIn("Umbrella route: local_u", text)
        self.assertIn("doc surface kickoff", text)
        self.assertIn('named "T-1 P1 research"', text)

    def test_delivery_from_the_invocation_is_quoted_in_the_brief(self):
        self.consent()
        self.cli("delivery", "--status", "authorized", "--from-request", "--source", "invocation")
        self.cli("set", "delivery", "response=yes", expect=2)
        text = self.brief("P1")
        self.assertIn("## Delivery authorization", text)
        self.assertIn("(stated in the user's Artifex invocation)", text)
        self.assertIn("don't ask the user again", text)

    def test_brief_refuses_without_a_verbatim_consent_record(self):
        self.brief("P1", expect=2)
        self.cli("set", "consent", "response=yes", expect=2)

    def test_declined_consent_briefs_manual_relay(self):
        self.consent(status="declined", response="no")
        self.assertIn("Don't message the umbrella", self.brief("P1"))

    def test_p2_brief_needs_a_milestone_and_lists_approved_artifacts(self):
        self.consent()
        self.brief("P2", expect=2)
        (self.dir / "kickoff.md").write_text("k\n", encoding="utf-8")
        self.cli("doc", "approve", "kickoff", "--host", "codex", "--surface", "local-file")
        self.cli("upsert", "milestones", "M1", "scope=version flag")
        text = self.brief("P2", "--milestone", "M1")
        self.assertIn("Milestone: M1. Scope: version flag", text)
        self.assertIn("- kickoff:", text)
        self.assertIn("doc surface specs --milestone M1", text)


if __name__ == "__main__":
    unittest.main()
