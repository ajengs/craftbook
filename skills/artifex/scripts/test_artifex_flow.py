"""Tests for artifex_flow.py. Run: python -m unittest test_artifex_flow -v"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifex_flow as af  # noqa: E402


def sha(n: int) -> str:
    return f"{n:040x}"


class Sim:
    """Drives the pure core: events in, actions out, dispatch recorded."""

    def __init__(self, auto=("V1",), manual=(), depends_on=(), verification=True):
        self.state = af.new_state()
        self.checkpoints = []
        self.apply({"type": "init", "milestone": "M1", "ticket": "T-1"})
        self.apply({"type": "handoff", "kind": "implementation", "path": "implementation-handoff.md",
                    "sha256": "i" * 64, "fields": {"branch": "b", "workdir": "w", "target": "main",
                                                   "depends_on": list(depends_on)}})
        if verification:
            self.verification(auto, manual)

    def verification(self, auto=("V1",), manual=()):
        self.apply({"type": "handoff", "kind": "verification", "path": "verification-handoff.md",
                    "sha256": "v" * 64, "fields": {"auto": list(auto), "manual": list(manual)}})

    def apply(self, ev):
        cps = af.apply(self.state, ev)
        self.checkpoints.extend(cps)
        return cps

    def step(self, siblings=(), hash_of=None):
        actions = af.next_actions(self.state, siblings, hash_of)
        for a in actions:
            if a["action"] == "spawn":
                self.apply({"type": "dispatched", "run_id": a["run_id"], "phase": a["phase"],
                            "round": a.get("round"), "head": a["inputs"].get("head")})
        return actions

    def spawned(self, siblings=()):
        return [a for a in self.step(siblings) if a["action"] == "spawn"]

    def result(self, run_id, status="completed", head=None, push="code", problems=(), override=None, **env):
        phase = self.state["active"][run_id]["phase"] if run_id in self.state["active"] else run_id.split("-")[1]
        envelope = {"run_id": run_id, "phase": phase, "status": status, "head": head, **env}
        if phase == "P3" and status == "completed":
            envelope.setdefault("pr_url", "https://example/pr/1")
        if phase == "P4" and status == "changes_requested":
            envelope.setdefault("findings", 2)
        if phase != "P3":
            envelope.setdefault("artifacts", [f"{run_id}.md"])
        return self.apply({"type": "result", "result": envelope, "problems": list(problems),
                           "override": override, "push": {"class": push} if phase == "P3" else None})

    def kinds(self):
        return [c["kind"] for c in self.checkpoints]

    def to_review_pass(self):
        """Implementation, PR and one passing review on head 1."""
        p3, = self.spawned()
        self.result(p3["run_id"], head=sha(1), push="initial")
        p4, = self.spawned()
        self.result(p4["run_id"], head=sha(1))
        return p4


class HappyPathTests(unittest.TestCase):
    def test_handoff_starts_implementation_with_session_name(self):
        sim = Sim()
        p3, = sim.spawned()
        self.assertEqual(p3["phase"], "P3")
        self.assertEqual(p3["agent"], "artifex_worker")
        self.assertEqual(p3["session_name"], "T-1 P3 implementation M1")
        self.assertEqual(p3["result_path"], "results/M1-P3-1.json")

    def test_pr_open_posts_checkpoint_and_starts_review_round_1(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.result(p3["run_id"], head=sha(1), push="initial")
        self.assertIn("pr_opened", sim.kinds())
        p4, = sim.spawned()
        self.assertEqual((p4["phase"], p4["round"], p4["mode"]), ("P4", 1, "initial"))

    def test_pass_with_auto_scenarios_starts_p5_then_ready_for_acceptance(self):
        sim = Sim(auto=("V1",))
        sim.to_review_pass()
        p5, = sim.spawned()
        self.assertEqual(p5["inputs"]["scenarios"], ["V1"])
        sim.result(p5["run_id"], head=sha(1), scenarios={"V1": "pass"})
        self.assertEqual(sim.kinds()[-1], "ready_for_acceptance")
        self.assertEqual(sim.step()[0]["action"], "idle")

    def test_pass_without_verification_handoff_waits_then_starts_p5_when_it_lands(self):
        sim = Sim(verification=False)
        sim.to_review_pass()
        self.assertIn("awaiting_verification_handoff", sim.kinds())
        self.assertEqual(sim.step()[0]["action"], "idle")
        sim.verification(auto=("V1",))
        self.assertEqual(sim.spawned()[0]["phase"], "P5")

    def test_no_auto_but_manual_scenarios_reports_p6_and_waits_for_trigger(self):
        sim = Sim(auto=(), manual=("M1",))
        sim.to_review_pass()
        self.assertEqual(sim.kinds()[-1], "p6_applies")
        self.assertEqual(sim.spawned(), [])
        sim.apply({"type": "trigger_p6"})
        p6, = sim.spawned()
        self.assertEqual((p6["phase"], p6["agent"]), ("P6", None))

    def test_no_scenarios_at_all_goes_straight_to_sign_off(self):
        sim = Sim(auto=(), manual=())
        sim.to_review_pass()
        self.assertEqual(sim.kinds()[-1], "ready_for_acceptance")


class IdleReasonTests(unittest.TestCase):
    def idle(self, sim):
        action, = sim.step()
        self.assertEqual(action["action"], "idle")
        return action["reason"]

    def test_waits_for_verification_handoff(self):
        sim = Sim(verification=False)
        sim.to_review_pass()
        self.assertIn("waiting for the verification handoff", self.idle(sim))

    def test_waits_for_p6_trigger_after_p5_passes(self):
        sim = Sim(auto=("V1",), manual=("V2",))
        sim.to_review_pass()
        p5, = sim.spawned()
        sim.result(p5["run_id"], head=sha(1), scenarios={"V1": "pass"})
        self.assertIn("P6 trigger", self.idle(sim))

    def test_waits_for_sign_off_and_flags_unconfirmed_ci(self):
        sim = Sim(auto=(), manual=())
        sim.to_review_pass()
        self.assertIn("sign-off", self.idle(sim))
        self.assertIn("CI is unknown", self.idle(sim))
        sim.apply({"type": "poll", "kind": "ci", "outcome": "passing", "head": sha(1)})
        self.assertNotIn("CI is", self.idle(sim))

    def test_status_names_the_next_step(self):
        sim = Sim(auto=(), manual=("V2",))
        sim.to_review_pass()
        self.assertIn("Router: running; next: P5 is done or not applicable; waiting for the user's P6 trigger",
                      af.render_status(sim.state))
        sim.apply({"type": "trigger_p6"})
        self.assertIn("next: spawn M1-P6-1", af.render_status(sim.state))


class UmbrellaSessionTests(unittest.TestCase):
    def test_init_session_and_replacements_are_kept_in_order(self):
        state = af.new_state()
        af.apply(state, {"type": "init", "milestone": "M1", "ticket": "T-1", "umbrella_session": "s1"})
        af.apply(state, {"type": "umbrella", "session": "s1"})
        af.apply(state, {"type": "umbrella", "session": "s2"})
        self.assertEqual(state["umbrella_sessions"], ["s1", "s2"])
        self.assertIn("Umbrella session: s2 (2 in total)", af.render_status(state))

    def test_status_says_when_no_session_was_recorded(self):
        self.assertIn("Umbrella session: not recorded", af.render_status(Sim().state))


class ReviewLoopTests(unittest.TestCase):
    def test_changes_requested_reworks_with_findings_then_next_round(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.result(p3["run_id"], head=sha(1), push="initial")
        p4, = sim.spawned()
        sim.result(p4["run_id"], "changes_requested", head=sha(1), artifacts=["review-r1.md"])
        rework, = sim.spawned()
        self.assertEqual(rework["inputs"]["findings"], ["review-r1.md"])
        self.assertIn("review rework", rework["session_name"])
        sim.result(rework["run_id"], head=sha(2))
        p4b, = sim.spawned()
        self.assertEqual(p4b["round"], 2)
        self.assertEqual(p4b["inputs"]["previous_review"], ["review-r1.md"])
        self.assertEqual(p4b["inputs"]["last_reviewed_head"], sha(1))

    def test_third_failed_round_halts_and_no_fourth_starts(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.result(p3["run_id"], head=sha(1), push="initial")
        for n in range(1, 4):
            p4, = sim.spawned()
            sim.result(p4["run_id"], "changes_requested", head=sha(n))
            if n < 3:
                rework, = sim.spawned()
                sim.result(rework["run_id"], head=sha(n + 1))
        self.assertEqual(sim.kinds()[-1], "review_cap")
        self.assertEqual(sim.step()[0]["action"], "halted")

    def test_grant_extends_the_cap_by_one_round(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.result(p3["run_id"], head=sha(1), push="initial")
        for n in range(1, 4):
            p4, = sim.spawned()
            sim.result(p4["run_id"], "changes_requested", head=sha(n))
            if n < 3:
                sim.result(sim.spawned()[0]["run_id"], head=sha(n + 1))
        sim.apply({"type": "resume", "note": "user allows one more", "grants": ["review"],
                   "request": "P3", "origin": "p4", "inputs": ["review-r3.md"]})
        sim.result(sim.spawned()[0]["run_id"], head=sha(4))
        p4, = sim.spawned()
        self.assertEqual(p4["round"], 4)

    def test_ci_fix_before_pass_starts_no_round(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.result(p3["run_id"], head=sha(1), push="initial")
        p4, = sim.spawned()
        sim.apply({"type": "poll", "kind": "ci", "outcome": "failing", "head": sha(1)})
        fix, = sim.spawned()
        self.assertIn("CI fix", fix["session_name"])
        sim.result(fix["run_id"], head=sha(2))
        self.assertEqual(sim.spawned(), [])

    def test_pass_on_older_head_than_a_ci_fix_runs_one_incremental_round(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.result(p3["run_id"], head=sha(1), push="initial")
        p4, = sim.spawned()
        sim.apply({"type": "poll", "kind": "ci", "outcome": "failing", "head": sha(1)})
        sim.result(sim.spawned()[0]["run_id"], head=sha(2))
        sim.result(p4["run_id"], head=sha(1))
        self.assertIn("review_gap", sim.kinds())
        gap, = sim.spawned()
        self.assertEqual(gap["mode"], "incremental")

    def test_incremental_round_that_fails_escalates(self):
        sim = Sim()
        sim.to_review_pass()
        sim.apply({"type": "poll", "kind": "threads", "ids": ["t1:c1"]})
        spawned = sim.spawned()
        p3 = next(a for a in spawned if a["phase"] == "P3")
        sim.result(p3["run_id"], head=sha(2), push="code")
        p4, = sim.spawned()
        sim.result(p4["run_id"], "changes_requested", head=sha(2))
        self.assertEqual(sim.kinds()[-1], "review_cap")

    def test_inconclusive_review_halts_for_the_umbrella(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.result(p3["run_id"], head=sha(1), push="initial")
        p4, = sim.spawned()
        sim.result(p4["run_id"], "inconclusive", head=sha(1), summary="diff truncated")
        self.assertEqual(sim.step()[0]["reasons"][0]["message"], "diff truncated")


class PushAfterPassTests(unittest.TestCase):
    def setUp(self):
        self.sim = Sim()
        self.sim.to_review_pass()
        p5, = self.sim.spawned()
        self.sim.result(p5["run_id"], head=sha(1), scenarios={"V1": "pass"})
        self.sim.apply({"type": "poll", "kind": "threads", "ids": ["t1:c1"]})
        self.p3, = self.sim.spawned()

    def test_docs_only_push_keeps_review_and_p5(self):
        self.sim.result(self.p3["run_id"], head=sha(2), push="docs")
        self.assertEqual(self.sim.step()[0]["action"], "idle")

    def test_rebase_keeps_review_and_p5(self):
        self.sim.result(self.p3["run_id"], head=sha(2), push="rebase")
        self.assertEqual(self.sim.step()[0]["action"], "idle")

    def test_code_push_runs_incremental_review_then_reruns_p5(self):
        self.sim.result(self.p3["run_id"], head=sha(2), push="code")
        self.assertIn("p5_stale", self.sim.kinds())
        p4, = self.sim.spawned()
        self.assertEqual(p4["mode"], "incremental")
        self.sim.result(p4["run_id"], head=sha(2))
        p5, = self.sim.spawned()
        self.assertEqual(p5["inputs"]["head"], sha(2))

    def test_same_thread_version_is_not_dispatched_twice(self):
        self.sim.apply({"type": "poll", "kind": "threads", "ids": ["t1:c1"]})
        self.assertEqual(self.sim.kinds()[-1], "threads_none")
        self.sim.apply({"type": "poll", "kind": "threads", "ids": ["t1:c1", "t1:c2"]})
        self.assertEqual(self.sim.kinds()[-1], "threads_new")


class VerificationLoopTests(unittest.TestCase):
    def fail_p5(self, sim, head):
        p5, = sim.spawned()
        sim.result(p5["run_id"], "changes_requested", head=head, scenarios={"V1": "fail"}, route="P3")

    def test_p5_fail_reworks_then_one_review_round_then_p5_reruns(self):
        sim = Sim()
        sim.to_review_pass()
        self.fail_p5(sim, sha(1))
        rework, = sim.spawned()
        self.assertIn("P5 rework", rework["session_name"])
        sim.result(rework["run_id"], head=sha(2))
        p4, = sim.spawned()
        self.assertEqual(p4["mode"], "p5_rework")
        sim.result(p4["run_id"], head=sha(2))
        self.assertEqual(sim.spawned()[0]["phase"], "P5")

    def test_p5_rework_review_gets_only_one_round(self):
        sim = Sim()
        sim.to_review_pass()
        self.fail_p5(sim, sha(1))
        sim.result(sim.spawned()[0]["run_id"], head=sha(2))
        p4, = sim.spawned()
        sim.result(p4["run_id"], "changes_requested", head=sha(2))
        self.assertEqual(sim.kinds()[-1], "review_cap")

    def test_third_p5_fail_halts_at_the_rework_cap(self):
        sim = Sim()
        sim.to_review_pass()
        head = 1
        for _ in range(2):
            self.fail_p5(sim, sha(head))
            head += 1
            sim.result(sim.spawned()[0]["run_id"], head=sha(head))
            sim.result(sim.spawned()[0]["run_id"], head=sha(head))
        self.fail_p5(sim, sha(head))
        self.assertEqual(sim.kinds()[-1], "p5_rework_cap")

    def test_routes_other_than_p3_halt(self):
        for route, kind in (("P2", "route"), ("P1", "route"), ("D1", "major_finding")):
            sim = Sim()
            sim.to_review_pass()
            p5, = sim.spawned()
            sim.result(p5["run_id"], "changes_requested", head=sha(1), scenarios={"V1": "fail"}, route=route)
            self.assertEqual(sim.kinds()[-1], kind, route)

    def test_p5_test_push_carries_review_forward(self):
        sim = Sim()
        sim.to_review_pass()
        p5, = sim.spawned()
        sim.result(p5["run_id"], head=sha(1), pushed_head=sha(9), scenarios={"V1": "pass"})
        self.assertEqual(sim.state["pr"]["head"], sha(9))
        self.assertEqual(sim.step()[0]["action"], "idle")

    def test_p3_waits_while_p5_is_active(self):
        sim = Sim()
        sim.to_review_pass()
        sim.spawned()
        sim.apply({"type": "poll", "kind": "ci", "outcome": "failing", "head": sha(1)})
        wait, = sim.step()
        self.assertEqual((wait["action"], wait["phase"]), ("wait", "P3"))


class ExceptionTests(unittest.TestCase):
    def test_needs_decision_halts_with_the_question_and_resume_respawns(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.result(p3["run_id"], "needs_decision", question="Cache or batch?")
        self.assertEqual(sim.step()[0]["reasons"][0]["message"], "Cache or batch?")
        sim.apply({"type": "resume", "note": "user chose batch", "request": "P3", "inputs": ["decision.md"]})
        again, = sim.spawned()
        self.assertEqual(again["inputs"]["findings"], ["decision.md"])
        sim.result(again["run_id"], head=sha(1), push="initial")
        self.assertEqual(sim.spawned()[0]["phase"], "P4")

    def test_validation_problems_halt_and_keep_the_run_for_resubmission(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.result(p3["run_id"], head=sha(1), push="initial", problems=["internal codes: SPEC-1"])
        self.assertEqual(sim.kinds()[-1], "result_rejected")
        self.assertIn(p3["run_id"], sim.state["active"])
        with self.assertRaises(af.FlowError):
            sim.apply({"type": "resume", "note": "x"})
        sim.result(p3["run_id"], head=sha(1), push="initial", problems=["internal codes: SPEC-1"],
                   override="false positive")
        self.assertEqual(sim.state["halt"], [])
        self.assertEqual(sim.spawned()[0]["phase"], "P4")

    def test_failed_run_retries_once_then_halts(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.apply({"type": "run_failed", "run_id": p3["run_id"], "reason": "timeout"})
        retry, = sim.spawned()
        self.assertEqual(retry["run_id"], "M1-P3-2")
        sim.apply({"type": "run_failed", "run_id": retry["run_id"], "reason": "timeout"})
        self.assertEqual(sim.kinds()[-1], "run_failed")

    def test_failed_review_run_does_not_consume_a_round(self):
        sim = Sim()
        p3, = sim.spawned()
        sim.result(p3["run_id"], head=sha(1), push="initial")
        p4, = sim.spawned()
        sim.apply({"type": "run_failed", "run_id": p4["run_id"]})
        retry, = sim.spawned()
        self.assertEqual(retry["round"], 1)

    def test_unknown_run_is_refused(self):
        sim = Sim()
        with self.assertRaises(af.FlowError):
            sim.result("M1-P3-9", head=sha(1))

    def test_dependencies_hold_implementation_until_met(self):
        sim = Sim(depends_on=("M0 merged",))
        wait, = sim.step()
        self.assertIn("M0 merged", wait["reason"])
        sim.apply({"type": "dependency_met", "name": "M0 merged"})
        self.assertEqual(sim.spawned()[0]["phase"], "P3")

    def test_sibling_on_same_branch_holds_implementation(self):
        other = Sim()
        other.spawned()
        sim = Sim()
        wait, = sim.step(siblings=[("M0", other.state)])
        self.assertIn("milestone M0", wait["reason"])

    def test_changed_handoff_blocks_dispatch(self):
        sim = Sim()
        wait, = sim.step(hash_of=lambda path: "changed")
        self.assertIn("record it again", wait["reason"])

    def test_closed_milestone_refuses_events(self):
        sim = Sim()
        sim.apply({"type": "close", "note": "signed off"})
        with self.assertRaises(af.FlowError):
            sim.apply({"type": "poll", "kind": "threads", "ids": []})


class ShapeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mdir = Path(self.tmp.name)
        (self.mdir / "report.md").write_text("ok", encoding="utf-8")
        self.sim = Sim()
        self.sim.to_review_pass()
        self.run, = self.sim.spawned()
        self.active = self.sim.state["active"][self.run["run_id"]]

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, **env):
        envelope = {"run_id": self.run["run_id"], "phase": "P5", "head": sha(1), "artifacts": ["report.md"], **env}
        return af.check_shape(self.sim.state, self.active, envelope, self.mdir)

    def test_completed_with_a_failing_scenario_is_rejected(self):
        problems = self.check(status="completed", scenarios={"V1": "fail"})
        self.assertTrue(any("derive fail" in p for p in problems), problems)

    def test_missing_scenario_is_rejected(self):
        problems = self.check(status="completed", scenarios={})
        self.assertTrue(any("V1" in p for p in problems), problems)

    def test_fail_without_route_is_rejected(self):
        problems = self.check(status="changes_requested", scenarios={"V1": "fail"})
        self.assertTrue(any("route" in p for p in problems), problems)

    def test_unknown_head_and_missing_artifact_are_rejected(self):
        problems = self.check(status="completed", scenarios={"V1": "pass"}, head=sha(7), artifacts=["nope.md"])
        self.assertTrue(any("not a head" in p for p in problems), problems)
        self.assertTrue(any("nope.md" in p for p in problems), problems)

    def test_valid_pass_has_no_problems(self):
        self.assertEqual(self.check(status="completed", scenarios={"V1": "pass"}), [])


class FrontmatterTests(unittest.TestCase):
    def test_scalars_inline_and_block_lists(self):
        text = "---\nbranch: dev/x\nworkdir: D:\\repo\\wt\ndepends_on: none\nauto: [V1, V2]\nmanual:\n  - V3\n---\n# Body"
        data = af.parse_frontmatter(text)
        self.assertEqual(data["branch"], "dev/x")
        self.assertEqual(data["workdir"], "D:\\repo\\wt")
        self.assertEqual(data["depends_on"], [])
        self.assertEqual(data["auto"], ["V1", "V2"])
        self.assertEqual(data["manual"], ["V3"])


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


class GitRepo:
    def __init__(self, root: Path):
        self.origin = root / "origin.git"
        self.work = root / "work"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.work)], check=True, capture_output=True)
        git(self.work, "config", "user.email", "t@example.com")
        git(self.work, "config", "user.name", "t")
        git(self.work, "checkout", "-q", "-b", "main")
        self.commit("app.py", "a = 1\n", "base")
        git(self.work, "push", "-q", "origin", "main")
        git(self.work, "checkout", "-q", "-b", "feature")

    def commit(self, path, text, message):
        target = self.work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        git(self.work, "add", path)
        git(self.work, "commit", "-q", "-m", message)
        return git(self.work, "rev-parse", "HEAD")


class GitClassifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = GitRepo(Path(self.tmp.name))
        self.git = af.Git(self.repo.work)
        self.old = self.repo.commit("feature.py", "x = 1\n", "feature")

    def tearDown(self):
        self.tmp.cleanup()

    def classify(self, new):
        return af.classify_push(self.git, self.old, new, "main", af.DEFAULT_DOC_PATTERNS)["class"]

    def test_docs_only(self):
        self.assertEqual(self.classify(self.repo.commit("docs/guide.md", "hi\n", "docs")), "docs")

    def test_code(self):
        self.assertEqual(self.classify(self.repo.commit("feature.py", "x = 2\n", "fix")), "code")

    def test_no_new_commits(self):
        self.assertEqual(self.classify(self.old), "none")

    def test_rebase_with_unchanged_patches(self):
        git(self.repo.work, "checkout", "-q", "main")
        self.repo.commit("other.py", "y = 1\n", "unrelated")
        git(self.repo.work, "checkout", "-q", "feature")
        git(self.repo.work, "rebase", "-q", "main")
        self.assertEqual(self.classify(git(self.repo.work, "rev-parse", "HEAD")), "rebase")

    def test_clean_merge_of_target(self):
        git(self.repo.work, "checkout", "-q", "main")
        self.repo.commit("other.py", "y = 1\n", "unrelated")
        git(self.repo.work, "checkout", "-q", "feature")
        git(self.repo.work, "merge", "-q", "--no-edit", "main")
        self.assertEqual(self.classify(git(self.repo.work, "rev-parse", "HEAD")), "merge")

    def test_merge_with_conflict_resolution_is_code(self):
        git(self.repo.work, "checkout", "-q", "main")
        self.repo.commit("feature.py", "x = 'main'\n", "conflicting")
        git(self.repo.work, "checkout", "-q", "feature")
        subprocess.run(["git", "-C", str(self.repo.work), "merge", "-q", "main"], capture_output=True)
        (self.repo.work / "feature.py").write_text("x = 'resolved'\n", encoding="utf-8")
        git(self.repo.work, "add", "feature.py")
        git(self.repo.work, "commit", "-q", "--no-edit")
        self.assertEqual(self.classify(git(self.repo.work, "rev-parse", "HEAD")), "code")

    def test_internal_code_hits_in_message_and_added_lines(self):
        new = self.repo.commit("feature.py", "x = 1  # covers VER-12\n", "implement SPEC-3")
        self.assertEqual(af.internal_code_hits(self.git, self.old, new, af.DEFAULT_CODE_PATTERNS),
                         ["SPEC-3", "VER-12"])


class CliTests(unittest.TestCase):
    """End to end through main(), with a real repo as the implementation workdir."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = GitRepo(root)
        self.mdir = root / "initiative" / "milestones" / "M1"
        self.mdir.mkdir(parents=True)
        (self.mdir / "implementation-handoff.md").write_text(
            f"---\nbranch: feature\nworkdir: {self.repo.work}\ntarget: main\ndepends_on: none\n---\n# Handoff\n",
            encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, expect=0):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = af.main([*args[:1], "--dir", str(self.mdir), *args[1:]])
        self.assertEqual(code, expect, err.getvalue())
        return json.loads(out.getvalue()) if expect == 0 and args[0] != "status" else out.getvalue()

    def result_file(self, run_id, **env):
        path = self.mdir / "results" / f"{run_id}.json"
        path.write_text(json.dumps({"run_id": run_id, **env}), encoding="utf-8")
        return str(path)

    def test_init_handoff_result_routes_to_review(self):
        self.cli("init", "--milestone", "M1", "--ticket", "T-1")
        out = self.cli("handoff", "--kind", "implementation", str(self.mdir / "implementation-handoff.md"))
        p3 = out["actions"][0]
        self.assertEqual(p3["action"], "spawn")
        self.assertTrue(Path(p3["result_path"]).is_absolute())

        head = self.repo.commit("feature.py", "x = 1\n", "feature")
        git(self.repo.work, "push", "-q", "origin", "feature")
        out = self.cli("result", self.result_file(p3["run_id"], phase="P3", status="completed", head=head,
                                               pr_url="https://example/pr/1"))
        self.assertEqual([c["kind"] for c in out["checkpoints"]], ["pr_opened"])
        self.assertEqual(out["actions"][0]["phase"], "P4")
        self.assertIn("Active runs: M1-P4-1 (P4)", self.cli("status"))

    def test_unpushed_head_and_internal_codes_are_rejected(self):
        self.cli("init", "--milestone", "M1", "--ticket", "T-1")
        p3 = self.cli("handoff", "--kind", "implementation",
                      str(self.mdir / "implementation-handoff.md"))["actions"][0]
        git(self.repo.work, "push", "-q", "origin", "feature")
        head = self.repo.commit("feature.py", "x = 1\n", "implement SPEC-3")
        out = self.cli("result", self.result_file(p3["run_id"], phase="P3", status="completed", head=head,
                                               pr_url="https://example/pr/1"))
        problems = out["checkpoints"][0]["problems"]
        self.assertTrue(any("not the reported" in p for p in problems), problems)
        self.assertTrue(any("SPEC-3" in p for p in problems), problems)
        self.assertEqual(out["actions"][0]["action"], "halted")

    def test_modified_handoff_blocks_dispatch_until_recorded_again(self):
        self.cli("init", "--milestone", "M1", "--ticket", "T-1")
        handoff = self.mdir / "implementation-handoff.md"
        self.cli("handoff", "--kind", "implementation", str(handoff), "--dry-run")
        handoff.write_text(handoff.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
        self.assertEqual(self.cli("next")["actions"][0]["action"], "wait")
        out = self.cli("handoff", "--kind", "implementation", str(handoff))
        self.assertEqual(out["actions"][0]["action"], "spawn")

    def test_umbrella_session_is_logged_with_a_timestamp(self):
        self.cli("init", "--milestone", "M1", "--ticket", "T-1", "--umbrella-session", "s1")
        self.cli("event", "umbrella", "--session", "s2")
        events = af.read_events(self.mdir)
        self.assertEqual(events[0]["umbrella_session"], "s1")
        self.assertEqual((events[1]["type"], events[1]["session"]), ("umbrella", "s2"))
        self.assertTrue(events[1]["ts"])

    def test_errors_exit_2_without_recording(self):
        self.cli("init", "--milestone", "M1", "--ticket", "T-1")
        before = (self.mdir / "run.jsonl").read_text(encoding="utf-8")
        self.cli("event", "resume", "--note", "x", expect=2)
        self.assertEqual((self.mdir / "run.jsonl").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
