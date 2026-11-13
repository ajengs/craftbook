"""Tests for artifex_state.py. Run: python -m unittest test_artifex_state -v"""

from __future__ import annotations

import contextlib
import hashlib
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
        self.cli("init", "--mode", "project", "--mode-source", "explicit", "--title", "Version flag",
                 "--request", "/artifex project CRAFT-1 add a version flag")

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

    def test_render_artifact_table_shows_source_column_only_when_recorded(self):
        self.cli("upsert", "artifacts", "kickoff", "path=kickoff.md", "decision=pending")
        self.assertNotIn("| Source |", self.cli("render"))
        self.cli("upsert", "artifacts", "specs-M1", "path=specs.md", "source=the invocation")
        text = self.cli("render")
        self.assertIn("| Source |", text)
        self.assertIn("the invocation", text)


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
        StateCliTests.cli(self, "init", "--mode", "project", "--mode-source", "explicit", "--request",
                          "/artifex project T-1")

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
        self.cli("init", "--mode", "project", "--mode-source", "explicit", "--ticket", "T-1",
                 "--request-file", str(request))

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
        text = self.brief("P1")
        self.assertIn("Don't message the umbrella", text)
        self.assertNotIn("send the umbrella", text)

    def test_combined_authorization_covers_creation_and_replacements_once(self):
        self.cli("consent", "--status", "authorized", "--session-creation", "authorized",
                 "--question", "Create phase and replacement sessions and exchange coordination messages?",
                 "--response", "Yes, for this initiative.", "--route", "umbrella")
        self.assertEqual(self.state()["consent"]["session_creation"], "authorized")
        self.cli("set", "consent", "session_creation=authorized", expect=2)
        for phase in ("P1", "P2", "D1"):
            args = (phase, "--milestone", "M1") if phase == "P2" else (phase,)
            text = self.brief(*args)
            self.assertIn("replacement sessions", text)
            self.assertIn("do not ask again", text)
            self.assertIn("Yes, for this initiative.", text)

    def test_coordination_only_update_does_not_keep_stale_creation_permission(self):
        self.cli("consent", "--status", "authorized", "--session-creation", "authorized",
                 "--question", "Create and coordinate?", "--response", "yes")
        self.consent()
        self.assertFalse(self.state()["consent"].get("session_creation"))

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


class ModeTests(unittest.TestCase):
    SPECS = "# Specifications — M1\n\nbody\n"
    CONTRACT = "# Verification contract — M1\n\nbody\n"
    HANDOFF = "---\nbranch: feat/x\nworkdir: D:/w\ntarget: main\n---\n# Implementation handoff\n"
    VERIFICATION = "---\nauto:\n  - V1\nmanual: []\n---\n# Verification handoff\n"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.dir = self.root / "ART-20"
        self.docs = self.root / "My Docs"
        self.docs.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = self.docs / name
        path.write_text(text, encoding="utf-8")
        return path

    def run_cli(self, *args, expect=0):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = st.main(["--dir", str(self.dir), *args])
        self.assertEqual(code, expect, err.getvalue())
        return json.loads(out.getvalue() if expect == 0 else err.getvalue())

    def route(self, request, *args, expect=0):
        file = self.root / "request.txt"
        file.write_text(request, encoding="utf-8")
        return self.run_cli("route", "--request-file", str(file), *args, expect=expect)

    def init(self, request, mode, *args, source="explicit", expect=0):
        file = self.root / "request.txt"
        file.write_text(request, encoding="utf-8")
        return self.run_cli("init", "--mode", mode, "--mode-source", source, "--request-file", str(file), *args,
                            expect=expect)

    def state(self):
        return json.loads((self.dir / "state.json").read_text(encoding="utf-8"))

    def implementation_files(self):
        return {"specs": self.write("specs.md", self.SPECS), "contract": self.write("contract.md", self.CONTRACT),
                "handoff": self.write("handoff.md", self.HANDOFF),
                "verification": self.write("verification.md", self.VERIFICATION)}

    def test_tokenize_keeps_windows_paths_and_quoted_paths_with_spaces(self):
        self.assertEqual(st.tokenize('/artifex "D:\\My Docs\\x.md" D:\\a\\b.md add it'),
                         ["/artifex", "D:\\My Docs\\x.md", "D:\\a\\b.md", "add", "it"])
        self.assertEqual(st.tokenize("add the uploader's retries"), ["add", "the", "uploader's", "retries"])

    def test_an_apostrophe_does_not_break_a_quoted_path(self):
        scope = self.write("scope.md", "scope\n")
        self.assertEqual(st.tokenize(f'milestone "{scope}" the uploader\'s retries'),
                         ["milestone", str(scope), "the", "uploader's", "retries"])
        out = self.route(f'/artifex milestone ART-20 "{scope}" the uploader\'s retries')
        self.assertEqual((out["files"], out["text"]), ([str(scope.resolve())], "the uploader's retries"))
        missing = self.docs / "gone.md"
        out = self.route(f'/artifex milestone ART-20 "{missing}" the uploader\'s retries', expect=2)
        self.assertIn("path not found", out["error"])

    def test_single_quoted_paths_are_found_or_refused(self):
        scope = self.root / "scope.md"
        scope.write_text("scope\n", encoding="utf-8")
        out = self.route(f"/artifex milestone ART-20 '{scope}' add retries")
        self.assertEqual((out["files"], out["text"]), ([str(scope.resolve())], "add retries"))
        out = self.route(f"/artifex milestone ART-20 '{self.root / 'gone.md'}' add retries", expect=2)
        self.assertIn("path not found", out["error"])
        out = self.route(f"/artifex milestone ART-20 '{self.docs / 'my scope.md'}' add retries", expect=2)
        self.assertIn("path not found", out["error"])

    def test_single_quoted_multiword_scope_and_edge_apostrophes_are_kept(self):
        for request in ("/artifex milestone ART-20 --scope 'add upload retries'",
                        "/artifex milestone ART-20 --scope='add upload retries'"):
            self.assertEqual(st.parse_request(request.split(" ", 1)[1])["text"], "add upload retries")
        text = st.parse_request("milestone ART-20 'tis the users' retries")["text"]
        self.assertEqual(text, "'tis the users' retries")

    def test_only_absolute_drive_and_dot_paths_are_refused_when_missing(self):
        out = self.route("/artifex milestone ART-20 skills/artifex/scripts/artifex_flow.py and/or retries")
        self.assertEqual((out["files"], out["text"]),
                         ([], "skills/artifex/scripts/artifex_flow.py and/or retries"))
        for token in ("./gone.md", "../gone.md", ".\\gone.md", "..\\gone.md", "\\\\server\\share\\gone.md",
                      "D:\\nowhere\\gone.md", "/nowhere/gone.md"):
            out = self.route(f"/artifex milestone ART-20 {token}", expect=2)
            self.assertIn("path not found", out["error"])

    def test_exported_headings_are_recognised_without_flags(self):
        files = self.implementation_files()
        files["specs"].write_text("# ART-19 M1 Specifications — modes\n\nbody\n", encoding="utf-8")
        files["contract"].write_text("# ART-19 M1 Verification contract — modes\n\nbody\n", encoding="utf-8")
        request = "/artifex implementation ART-20 " + " ".join(f'"{p}"' for p in files.values())
        out = self.route(request)
        self.assertEqual(out["contract"]["result"], "artifacts ready")

    def test_every_command_init_prints_runs(self):
        import subprocess
        files = self.implementation_files()
        request = "/artifex implementation ART-20 " + " ".join(f'"{p}"' for p in files.values())
        out = self.init(request, "implementation")
        self.assertFalse(any(" init --mode" in step for step in out["next"]))
        self.run_cli("consent", "--status", "authorized", "--question", "q", "--response", "yes")
        self.run_cli("delivery", "--status", "authorized", "--from-request", "--source", "invocation")
        ran = 0
        for step in out["next"]:
            if not step.startswith("python "):
                continue
            argv = st.tokenize(step.replace("<id>", "s1").replace("<ticket>", "ART-20"))
            result = subprocess.run([sys.executable, *argv[1:]], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"{step}\n{result.stderr}")
            ran += 1
        self.assertGreaterEqual(ran, 3)

    def test_route_reads_every_mode_form_and_writes_nothing(self):
        scope = self.write("scope.md", "scope\n")
        forms = [f'/artifex milestone ART-20 "{scope}"', f'/artifex --mode milestone ART-20 "{scope}"',
                 f'artifex --mode=milestone ART-20 "{scope}"', f'/artifex milestone --mode=milestone ART-20 "{scope}"']
        for form in forms:
            out = self.route(form)
            self.assertEqual((out["mode"], out["mode_source"], out["start"], out["ticket"]),
                             ("milestone", "explicit", "P2", "ART-20"), form)
            self.assertEqual(out["files"], [str(scope.resolve())])
            self.assertEqual((out["text"], out["links"], out["contract"]["ok"]), ("", [], True))
            self.assertTrue(any("brief P2 --milestone M1" in step for step in out["next"]))
        text = self.route("/artifex milestone ART-20 add retries to the uploader")
        self.assertEqual((text["text"], text["files"]), ("add retries to the uploader", []))
        self.assertFalse(self.dir.exists())

    def test_bug_is_stored_as_defect(self):
        for request in ("/artifex bug ART-5 crash on save", "/artifex --mode bug ART-5 crash on save"):
            out = self.route(request)
            self.assertEqual((out["mode"], out["start"]), ("defect", "D1"))
        self.init("/artifex bug ART-5 crash on save", "bug")
        self.assertEqual(self.state()["initiative"]["mode"], "defect")

    def test_a_request_without_a_mode_needs_a_recommendation(self):
        doc = self.write("artifex-modes.md", "design\n")
        out = self.route(f'/artifex ART-19 "{doc}"')
        self.assertTrue(out["needs_recommendation"])
        self.assertNotIn("start", out)
        self.assertEqual([m["mode"] for m in out["modes"]], ["project", "milestone", "defect", "implementation"])
        self.assertTrue(all(m["start"] and m["contract"] for m in out["modes"]))

    def test_unknown_conflicting_and_missing_paths_are_refused(self):
        self.assertIn("modes:", self.route("/artifex --mode nope ART-1", expect=2)["error"])
        conflict = self.route("/artifex defect --mode milestone ART-1 text", expect=2)["error"]
        self.assertIn("--mode milestone", conflict)
        self.assertIn("leading word defect", conflict)
        self.assertEqual(self.route("/artifex milestone --mode=milestone ART-1 text")["mode"], "milestone")
        for token in ("Z:\\nowhere\\scope.md", "/nowhere/scope.md"):
            self.assertIn("path not found", self.route(f"/artifex milestone ART-1 {token}", expect=2)["error"])
        self.assertIn("path not found", self.init("/artifex milestone ART-1 /nowhere/scope.md", "milestone",
                                                  expect=2)["error"])
        self.assertFalse(self.dir.exists())

    def test_milestone_needs_a_scope(self):
        out = self.route("/artifex milestone ART-20")
        self.assertFalse(out["contract"]["ok"])
        self.assertEqual(out["next"], [])
        self.assertIn("needs a scope: a file, a link or a description in the request", out["contract"]["problem"])
        self.assertIn("needs a scope", self.init("/artifex milestone ART-20", "milestone", expect=2)["error"])
        self.assertFalse(self.dir.exists())

    def test_milestone_init_registers_the_row_with_link_and_scope(self):
        out = self.init("/artifex milestone ART-20 https://example.com/spec retry the uploader", "milestone",
                        "--milestone", "M2", "--title", "Uploader")
        self.assertEqual(out["mode"], "milestone")
        self.assertTrue(any("brief P2 --milestone M2" in step for step in out["next"]))
        state = self.state()
        self.assertEqual(state["milestones"]["M2"], {"status": "selected", "link": "https://example.com/spec",
                                                     "scope": "retry the uploader"})
        self.assertEqual(state["initiative"]["ticket"], "ART-20")

    def test_milestone_scope_file_is_the_link(self):
        scope = self.write("scope.md", "scope\n")
        self.init(f'/artifex milestone ART-20 "{scope}"', "milestone")
        self.assertEqual(self.state()["milestones"]["M1"], {"status": "selected", "link": str(scope.resolve())})

    def test_project_and_defect_need_only_a_request(self):
        self.assertEqual(self.route("/artifex project ART-1 research it")["start"], "P1")
        self.assertFalse(self.route("/artifex project")["contract"]["ok"])
        self.init("/artifex", "defect", expect=2)
        out = self.init("/artifex defect ART-5", "defect")
        self.assertTrue(out["next"][-1].endswith("brief D1"))

    def test_initiative_holds_mode_and_source_but_no_track(self):
        self.init("/artifex ART-20 something", "project", source="recommended")
        initiative = self.state()["initiative"]
        self.assertEqual((initiative["mode"], initiative["mode_source"]), ("project", "recommended"))
        self.assertNotIn("track", initiative)

    def test_init_needs_a_mode_and_a_mode_source(self):
        for args in (["init", "--mode-source", "explicit", "--request", "/artifex ART-1 x"],
                     ["init", "--mode", "project", "--request", "/artifex ART-1 x"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                st.main(["--dir", str(self.dir), *args])
        self.assertIn("request", self.run_cli("init", "--mode", "project", "--mode-source", "explicit",
                                              expect=2)["error"])
        self.assertIn("no ticket", self.init("/artifex project just words", "project", expect=2)["error"])

    def test_init_refuses_a_mode_that_disagrees_with_the_request(self):
        self.assertIn("conflicting modes", self.init("/artifex defect ART-1 x", "milestone", expect=2)["error"])

    def test_implementation_with_the_four_artifacts_is_ready_and_recorded(self):
        files = self.implementation_files()
        request = "/artifex implementation ART-20 " + " ".join(f'"{p}"' for p in files.values())
        out = self.route(request)
        self.assertEqual((out["start"], out["contract"]["result"]), ("router", "artifacts ready"))
        joined = "\n".join(out["next"])
        self.assertIn("artifex_flow.py", joined)
        self.assertIn("--kind implementation", joined)
        self.assertIn("--kind verification", joined)
        self.init(request, "implementation")
        artifacts = self.state()["artifacts"]
        for name, key in (("specs-M1", "specs"), ("verification-contract-M1", "contract")):
            row = artifacts[name]
            self.assertEqual((row["decision"], row["surface"], row["path"]),
                             ("approved", "invocation", str(files[key].resolve())))
            self.assertEqual(row["sha256"], hashlib.sha256(files[key].read_bytes()).hexdigest())
            self.assertIn("invocation", row["source"])
        self.assertEqual(artifacts["implementation-handoff-M1"]["decision"], "supplied")
        self.assertEqual(artifacts["verification-handoff-M1"]["path"], str(files["verification"].resolve()))
        self.assertEqual(self.state()["milestones"]["M1"]["status"], "selected")

    def test_flags_name_an_artifact_recognition_cannot_identify(self):
        files = self.implementation_files()
        other = self.write("design.md", "# Design notes\n")
        files["specs"].unlink()
        request = f'/artifex implementation ART-20 "{files["contract"]}" "{files["handoff"]}" ' \
                  f'"{files["verification"]}" "{other}"'
        self.assertEqual(self.route(request)["contract"]["result"], "short P2")
        out = self.route(request, "--specs", str(other))
        self.assertEqual(out["contract"]["result"], "artifacts ready")
        self.assertEqual(out["contract"]["artifacts"]["specs"], str(other.resolve()))
        self.assertIn(f'--specs "{other}"', "\n".join(out["next"]))

    def test_implementation_with_missing_artifacts_and_context_is_a_short_p2(self):
        handoff = self.write("handoff.md", self.HANDOFF)
        unknown = self.write("notes.md", "# Notes\n")
        request = f'/artifex implementation ART-20 "{handoff}" "{unknown}" https://example.com/x retry uploads'
        out = self.route(request, "--milestone", "M3")
        self.assertEqual((out["start"], out["contract"]["result"]), ("P2", "short P2"))
        self.assertTrue(any("brief P2 --milestone M3 --short" in step for step in out["next"]))
        self.init(request, "implementation", "--milestone", "M3")
        state = self.state()
        self.assertEqual(state["milestones"]["M3"]["scope"], "retry uploads")
        self.assertEqual(state["milestones"]["M3"]["link"], str(unknown.resolve()))
        self.assertEqual(state["artifacts"]["implementation-handoff-M3"]["decision"], "supplied")
        self.assertNotIn("specs-M3", state["artifacts"])
        self.assertEqual({row.get("path") or row.get("url") for name, row in state["artifacts"].items()
                          if name.startswith("context-M3")}, {str(unknown.resolve()), "https://example.com/x"})

    def test_implementation_with_only_a_context_file_or_an_artifact_is_a_short_p2(self):
        self.assertEqual(self.route(f'/artifex implementation ART-20 "{self.write("a.md", "x")}"')["start"], "P2")
        self.assertEqual(self.route(f'/artifex implementation ART-20 "{self.write("s.md", self.SPECS)}"')["start"],
                         "P2")

    def test_implementation_refusals_name_the_problem_and_never_fall_back(self):
        none = self.route("/artifex implementation ART-20")
        self.assertIn("four artifacts", none["contract"]["problem"])
        self.assertIn("short P2", self.init("/artifex implementation ART-20", "implementation", expect=2)["error"])
        empty = self.write("empty.md", "---\n---\n# Handoff\n")
        partial = self.write("partial.md", "---\nbranch: x\n---\n# Handoff\n")
        one = self.write("one.md", self.SPECS)
        two = self.write("two.md", self.SPECS)
        for files, expected in (([empty], "empty.md: the handoff frontmatter is empty"),
                                ([partial], "partial.md: the implementation handoff frontmatter lacks workdir, target"),
                                ([one, two], "specs recognised twice")):
            request = "/artifex implementation ART-20 retry uploads " + " ".join(f'"{p}"' for p in files)
            self.assertIn(expected, self.route(request)["contract"]["problem"])
            self.assertIn(expected, self.init(request, "implementation", expect=2)["error"])
        self.assertFalse(self.dir.exists())

    def test_a_flagged_handoff_without_its_keys_is_refused(self):
        notes = self.write("notes.md", "---\ntitle: x\n---\n")
        out = self.route(f'/artifex implementation ART-20 "{notes}" retry', "--handoff", str(notes))
        self.assertIn("lacks branch, workdir, target", out["contract"]["problem"])

    def test_a_resumed_initiative_reports_its_stored_mode(self):
        self.init("/artifex defect ART-5 crash", "defect")
        out = self.route("/artifex milestone ART-5 something else")
        self.assertEqual((out["stored"], out["mode"], out["start"]), (True, "defect", "D1"))
        self.run_cli("init", "--mode", "defect", "--mode-source", "explicit", "--request", "/artifex defect ART-5",
                     expect=2)

    def old_state(self, track):
        self.dir.mkdir(parents=True, exist_ok=True)
        state = st.new_state("OLD-1", "Old", "x", "explicit", "/artifex OLD-1")
        state["initiative"] = {"ticket": "OLD-1", "title": "Old", "track": track, "request": "/artifex OLD-1"}
        state["consent"] = {"status": "declined", "question": "q", "response": "no", "date": "2026-01-01"}
        (self.dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    def test_an_old_state_with_track_loads_and_keeps_it(self):
        for track, mode in (("bug", "defect"), ("feature", "project")):
            self.old_state(track)
            self.assertEqual(st.effective_mode(self.state()), mode)
            self.assertEqual(self.route("/artifex x")["mode"], mode)
            self.assertEqual(self.run_cli("show", "--section", "initiative")["track"], track)
            self.run_cli("set", "status", "phase=P2")
            self.assertEqual(self.state()["initiative"]["track"], track)
            self.assertNotIn("mode", self.state()["initiative"])
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(st.main(["--dir", str(self.dir), "render"]), 0, err.getvalue())
                self.assertEqual(st.main(["--dir", str(self.dir), "brief", "P1"]), 0, err.getvalue())
            self.assertIn("# STATE", out.getvalue())
            (self.dir / "state.json").unlink()

    def test_the_mode_and_the_retired_track_cannot_be_set(self):
        self.old_state("bug")
        for pair in ("mode=project", "mode_source=explicit", "track=feature", "track="):
            self.run_cli("set", "initiative", pair, expect=2)
        self.assertEqual(self.state()["initiative"]["track"], "bug")
        self.run_cli("set", "initiative", "title=Renamed")

    def test_short_p2_brief_adds_instructions_and_supplied_paths(self):
        handoff = self.write("handoff.md", self.HANDOFF)
        self.init(f'/artifex implementation ART-20 "{handoff}" https://example.com/x retry uploads', "implementation")
        self.run_cli("consent", "--status", "declined", "--question", "q", "--response", "no")
        plain = st.brief(self.dir, self.state(), "P2", "M1", None)
        self.assertIn("Milestone: M1. Scope: retry uploads. Link: https://example.com/x", plain)
        self.assertNotIn("Short P2", plain)
        short = st.brief(self.dir, self.state(), "P2", "M1", None, short=True)
        self.assertIn("in one document", short)
        self.assertIn("approved first and produces the implementation handoff", short)
        self.assertIn(str(handoff.resolve()), short)
        self.assertIn("https://example.com/x", short)
        with self.assertRaises(st.StateError):
            st.brief(self.dir, self.state(), "P1", None, None, short=True)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(st.main(["--dir", str(self.dir), "brief", "P2", "--milestone", "M1", "--short"]), 0,
                             err.getvalue())
        self.assertIn("Short P2", out.getvalue())


class TrackFlagRemovedTests(unittest.TestCase):
    def refused(self, main, argv):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(argv)
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--track", err.getvalue())

    def test_state_init_no_longer_accepts_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.refused(st.main, ["--dir", tmp, "init", "--mode", "project", "--mode-source", "explicit",
                                   "--request", "/artifex project ART-1 x", "--track", "bug"])

    def test_router_init_no_longer_accepts_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.refused(af.main, ["init", "--dir", tmp, "--milestone", "M1", "--ticket", "T-1", "--track", "bug"])


if __name__ == "__main__":
    unittest.main()
