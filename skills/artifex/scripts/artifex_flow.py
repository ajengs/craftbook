#!/usr/bin/env python3
"""Deterministic router for the Artifex P3-P6 loop.

The umbrella calls this script instead of deciding routine transitions itself.
Every input is an event appended to <milestone folder>/run.jsonl, and the
router state is a fold over that log: no hidden memory, replayable, testable.

Commands (each takes --dir <milestone folder>):
    init      start the log for a milestone
    handoff   record an implementation or verification handoff
    result    validate an agent's result file, record it, route
    event     record a poll, failed run, resume, dependency, P6 trigger, close
    next      print the next actions
    status    print the generated status block for STATE.md

Every command except status prints JSON: {"checkpoints": [...], "actions": [...]}.
The umbrella posts checkpoints whose "post" is true, carries out each action
literally and handles "halted" itself. Spawn actions are recorded as
dispatched when printed (unless --dry-run); if a spawn then fails, record
`event run-failed --run-id <id>`.

See references/orchestration.md for the result file and the transition table.
"""

from __future__ import annotations

import argparse
import copy
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REVIEW_CAP = 3
CYCLE_CAPS = {"initial": REVIEW_CAP, "p5_rework": 1, "incremental": 1}
P5_REWORK_CAP = 2
RETRIES = 1
DEFAULT_CODE_PATTERNS = [r"\b(?:SPEC|VER)-\d+\b"]
DEFAULT_DOC_PATTERNS = ["*.md", "*.markdown", "*.rst", "*.txt", "*.adoc", "docs/*", "doc/*"]

PHASES = {
    "P3": {"name": "implementation", "agent": "artifex_worker", "workflow": "workflows/P3-implementation.md"},
    "P4": {"name": "review", "agent": "artifex_reviewer", "workflow": "workflows/P4-review.md"},
    "P5": {"name": "auto verification", "agent": "artifex_verifier", "workflow": "workflows/P5-verification.md"},
    "P6": {"name": "manual verification", "agent": None, "workflow": "workflows/P6-manual-verification.md"},
}
_VERIFY_STATUSES = {"completed", "changes_requested", "inconclusive", "needs_decision", "blocked"}
STATUSES = {
    "P3": {"completed", "needs_decision", "blocked"},
    "P4": set(_VERIFY_STATUSES),
    "P5": set(_VERIFY_STATUSES),
    "P6": set(_VERIFY_STATUSES),
}
ROUTES = {"P3", "P2", "P1", "D1"}
OUTCOMES = {"pass", "fail", "inconclusive", "invalid"}
ORIGINS = {"initial", "p4", "p5", "ci", "threads", "resume"}
ORIGIN_LABELS = {"initial": "", "p4": "review rework", "p5": "P5 rework", "ci": "CI fix",
                 "threads": "PR feedback", "resume": "resumed"}
HANDOFF_FIELDS = {"implementation": ("branch", "workdir", "target"), "verification": ()}
LIST_FIELDS = ("depends_on", "auto", "manual")
SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class FlowError(Exception):
    """Input the router refuses to record."""


class GitError(Exception):
    pass


# --------------------------------------------------------------------------
# State and transitions (pure)
# --------------------------------------------------------------------------

def new_state() -> dict:
    return {
        "milestone": None, "ticket": None, "track": "feature",
        "code_patterns": list(DEFAULT_CODE_PATTERNS), "doc_patterns": list(DEFAULT_DOC_PATTERNS),
        "handoffs": {}, "deps_met": [],
        # "equivalent" holds the heads whose code matches the last code push:
        # docs-only pushes, rebases and clean merges join it, so they carry an
        # earlier review or P5 pass forward instead of forcing a rerun.
        "pr": {"url": None, "head": None, "code_head": None, "equivalent": [], "heads": []},
        "review": {"mode": "initial", "cap": CYCLE_CAPS["initial"], "rounds": 0, "total": 0,
                   "open": True, "passed_head": None, "last_reviewed_head": None, "last_review": []},
        "p5": {"passed_head": None, "reworks": 0, "rework_cap": P5_REWORK_CAP},
        "p6": {"triggered": False, "passed_head": None},
        "requests": {}, "active": {}, "seq": {},
        "handled_threads": [], "pushes": [], "ci": "unknown",
        "halt": [], "closed": False,
    }


def checkpoint(kind: str, message: str, post: bool = True, **extra) -> dict:
    return {"kind": kind, "post": post, "message": message, **extra}


def halt(state: dict, kind: str, message: str, **extra) -> dict:
    state["halt"].append({"kind": kind, "message": message, **extra})
    return checkpoint(kind, message, post=True, halted=True, **extra)


def request(state: dict, phase: str, origin: str, inputs=(), threads=(), attempts: int = 0) -> None:
    req = state["requests"].setdefault(phase, {"origins": [], "inputs": [], "threads": [], "attempts": 0})
    if origin not in req["origins"]:
        req["origins"].append(origin)
    for item in inputs:
        if item not in req["inputs"]:
            req["inputs"].append(item)
    for item in threads:
        if item not in req["threads"]:
            req["threads"].append(item)
    req["attempts"] = max(req["attempts"], attempts)


def start_cycle(state: dict, mode: str) -> None:
    review = state["review"]
    review.update(mode=mode, cap=CYCLE_CAPS[mode], rounds=0, open=True)


def is_current(state: dict, head) -> bool:
    return head is not None and head in state["pr"]["equivalent"]


def record_push(state: dict, head: str, push: dict) -> None:
    pr = state["pr"]
    pr["head"] = head
    if head not in pr["heads"]:
        pr["heads"].append(head)
    if push["class"] in ("initial", "code", "tests"):
        pr["code_head"] = head
        pr["equivalent"] = [head]
    elif head not in pr["equivalent"]:
        pr["equivalent"].append(head)
    if push["class"] != "none":
        state["pushes"].append(dict(push, to=head))
        state["ci"] = "unknown"


def review_settled(state: dict) -> bool:
    return not state["review"]["open"] and is_current(state, state["review"]["passed_head"])


def after_review(state: dict, from_pass: bool) -> list:
    if not review_settled(state):
        return []
    ver = state["handoffs"].get("verification")
    if ver is None:
        if from_pass:
            return [checkpoint("awaiting_verification_handoff",
                               "Review passed; P5 waits for the verification handoff", post=False)]
        return []
    fields = ver["fields"]
    if fields.get("auto"):
        return []
    if fields.get("manual"):
        return [checkpoint("p6_applies", "No auto scenarios; P6 manual verification applies on the user's trigger")]
    return [checkpoint("ready_for_acceptance",
                       "Review passed and the contract has no scenarios to run; needs the user's sign-off")]


def on_init(state, ev):
    if state["milestone"] is not None:
        raise FlowError("milestone already initialized")
    state.update(milestone=ev["milestone"], ticket=ev["ticket"], track=ev.get("track", "feature"))
    state["code_patterns"] = DEFAULT_CODE_PATTERNS + list(ev.get("code_patterns", []))
    state["doc_patterns"] = DEFAULT_DOC_PATTERNS + list(ev.get("doc_patterns", []))
    return [checkpoint("initialized", f"Router started for {ev['milestone']}", post=False)]


def on_handoff(state, ev):
    kind = ev["kind"]
    previous = state["handoffs"].get(kind)
    state["handoffs"][kind] = {"path": ev["path"], "sha256": ev["sha256"], "fields": ev["fields"]}
    out = []
    if previous is None:
        out.append(checkpoint("handoff_recorded", f"{kind} handoff recorded: {ev['path']}", post=False))
    elif previous["sha256"] != ev["sha256"]:
        out.append(checkpoint("handoff_modified", f"{kind} handoff changed: {ev['path']}", post=False))
    if kind == "implementation" and previous is None and state["pr"]["url"] is None:
        request(state, "P3", "initial")
    if kind == "verification":
        out.extend(after_review(state, from_pass=False))
    return out


def on_dispatched(state, ev):
    phase = ev["phase"]
    req = state["requests"].pop(phase, {"origins": [], "inputs": [], "threads": [], "attempts": 0})
    state["active"][ev["run_id"]] = {
        "phase": phase, "origins": req["origins"], "inputs": req["inputs"], "threads": req["threads"],
        "attempts": req["attempts"], "round": ev.get("round"), "head": ev.get("head"),
    }
    state["seq"][phase] = state["seq"].get(phase, 0) + 1
    state["handled_threads"].extend(t for t in req["threads"] if t not in state["handled_threads"])
    if phase == "P4":
        state["review"]["rounds"] += 1
        state["review"]["total"] += 1
    if phase == "P6":
        state["p6"]["triggered"] = False
    return []


def _clear_rejection(state, run_id):
    state["halt"] = [h for h in state["halt"]
                     if not (h["kind"] == "result_rejected" and h.get("run_id") == run_id)]


def on_run_failed(state, ev):
    run_id = ev["run_id"]
    run = state["active"].pop(run_id, None)
    if run is None:
        raise FlowError(f"{run_id} is not an active run")
    _clear_rejection(state, run_id)
    phase = run["phase"]
    if phase == "P4":
        state["review"]["rounds"] -= 1
        state["review"]["total"] -= 1
    if phase == "P6":
        state["p6"]["triggered"] = True
    state["handled_threads"] = [t for t in state["handled_threads"] if t not in run["threads"]]
    reason = ev.get("reason") or "no reason given"
    if run["attempts"] < RETRIES:
        for origin in run["origins"] or ["resume"]:
            request(state, phase, origin, run["inputs"], run["threads"], attempts=run["attempts"] + 1)
        return [checkpoint("retry", f"{run_id} failed ({reason}); retrying once", post=False)]
    return [halt(state, "run_failed", f"{run_id} failed again: {reason}", run_id=run_id)]


def on_result(state, ev):
    env = ev["result"]
    run_id = env["run_id"]
    run = state["active"].get(run_id)
    if run is None:
        raise FlowError(f"{run_id} is not an active run")
    problems = ev.get("problems") or []
    if problems and not ev.get("override"):
        run["rejected"] = problems
        return [halt(state, "result_rejected", f"{run_id} result failed validation",
                     run_id=run_id, problems=problems)]
    del state["active"][run_id]
    _clear_rejection(state, run_id)
    out = []
    if problems:
        out.append(checkpoint("override", f"{run_id} accepted despite validation problems: {ev['override']}",
                              post=False, problems=problems))
    out.extend(RESULT_HANDLERS[run["phase"]](state, run, env, ev))
    return out


def _stop(state, run, env, default):
    status = env["status"]
    message = env.get("question") if status == "needs_decision" else None
    return [halt(state, status, message or env.get("summary") or default, run_id=env["run_id"],
                 artifacts=env.get("artifacts", []))]


def p3_result(state, run, env, ev):
    if env["status"] != "completed":
        return _stop(state, run, env, f"Implementation is {env['status']}")
    pr = state["pr"]
    first = pr["url"] is None
    out = []
    if first:
        pr["url"] = env["pr_url"]
        out.append(checkpoint("pr_opened", f"PR opened: {env['pr_url']}"))
    push = ev.get("push") or {"class": "initial"}
    record_push(state, env["head"], push)
    origins = set(run["origins"])
    if first or "initial" in origins:
        request(state, "P4", "initial")
        return out
    if push["class"] == "none":
        out.append(checkpoint("no_push", f"{env['run_id']} completed without new commits", post=False))
        return out
    if "p5" in origins:
        start_cycle(state, "p5_rework")
        request(state, "P4", "p5")
        return out
    if "p4" in origins:
        request(state, "P4", "p4")
        return out
    review = state["review"]
    if review["open"]:
        out.append(checkpoint("push_recorded", f"{push['class']} push recorded; it goes into the next review round",
                              post=False))
    elif push["class"] == "code":
        start_cycle(state, "incremental")
        request(state, "P4", "incremental")
        out.append(checkpoint("incremental_review", "Code changed after the review passed; one incremental round",
                              post=False))
        if state["p5"]["passed_head"] or any(r["phase"] == "P5" for r in state["active"].values()):
            out.append(checkpoint("p5_stale", "P5 reruns on the new head after the incremental round", post=False))
    else:
        out.append(checkpoint("push_recorded", f"{push['class']} push; no review round", post=False))
    return out


def p4_result(state, run, env, ev):
    review = state["review"]
    status = env["status"]
    artifacts = env.get("artifacts", [])
    label = f"Review round {run.get('round') or review['rounds']}"
    if review["mode"] != "initial":
        label += f" ({review['mode'].replace('_', ' ')})"
    if status in ("completed", "changes_requested"):
        review["last_reviewed_head"] = env["head"]
        review["last_review"] = artifacts
    if status == "completed":
        review["open"] = False
        review["passed_head"] = env["head"]
        out = [checkpoint("review_passed", f"{label} passed", artifacts=artifacts)]
        if not is_current(state, env["head"]):
            start_cycle(state, "incremental")
            request(state, "P4", "incremental")
            out.append(checkpoint("review_gap", "Code was pushed after the reviewed head; one incremental round",
                                  post=False))
            return out
        out.extend(after_review(state, from_pass=True))
        return out
    if status == "changes_requested":
        if review["rounds"] >= review["cap"]:
            return [halt(state, "review_cap",
                         f"{label} requested changes and the {review['mode'].replace('_', ' ')} cap of "
                         f"{review['cap']} round(s) is reached", run_id=env["run_id"], artifacts=artifacts)]
        request(state, "P3", "p4", artifacts)
        return [checkpoint("changes_requested", f"{label}: {env['findings']} finding(s); rework queued",
                           artifacts=artifacts)]
    return _stop(state, run, env, f"{label} is {status}")


def _verification_tests_pushed(state, env):
    pushed = env.get("pushed_head")
    if not pushed:
        return
    carried = is_current(state, state["review"]["passed_head"])
    record_push(state, pushed, {"class": "tests", "from": state["pr"]["head"]})
    if carried:
        state["review"]["passed_head"] = pushed


def p5_result(state, run, env, ev):
    status = env["status"]
    artifacts = env.get("artifacts", [])
    stale = not is_current(state, env["head"])
    if not stale:
        _verification_tests_pushed(state, env)
    p5 = state["p5"]
    if status == "completed":
        if stale:
            p5["passed_head"] = env["head"]
            return [checkpoint("p5_stale", "P5 passed on an older head; it reruns after review", post=False)]
        p5["passed_head"] = state["pr"]["head"]
        if state["handoffs"]["verification"]["fields"].get("manual"):
            return [checkpoint("p5_passed", "P5 passed; P6 manual verification applies on the user's trigger",
                               artifacts=artifacts)]
        return [checkpoint("ready_for_acceptance", "P5 passed; ready for acceptance, needs the user's sign-off",
                           artifacts=artifacts)]
    if status == "changes_requested":
        route = env["route"]
        if route == "D1":
            return [halt(state, "major_finding", "P5 found a major finding; ask the user whether to start D1",
                         run_id=env["run_id"], artifacts=artifacts)]
        if route != "P3":
            return [halt(state, "route", f"P5 failed and routes to {route}; that needs the user",
                         run_id=env["run_id"], artifacts=artifacts)]
        if p5["reworks"] >= p5["rework_cap"]:
            return [halt(state, "p5_rework_cap",
                         f"P5 failed again after {p5['reworks']} rework(s); the cap is reached",
                         run_id=env["run_id"], artifacts=artifacts)]
        p5["reworks"] += 1
        request(state, "P3", "p5", artifacts)
        return [checkpoint("p5_failed", f"P5 failed; rework {p5['reworks']} of {p5['rework_cap']} queued",
                           artifacts=artifacts)]
    return _stop(state, run, env, f"P5 is {status}")


def p6_result(state, run, env, ev):
    if env["status"] == "completed" and is_current(state, env["head"]):
        _verification_tests_pushed(state, env)
        state["p6"]["passed_head"] = state["pr"]["head"]
        return [checkpoint("ready_for_acceptance", "P6 passed; ready for acceptance, needs the user's sign-off",
                           artifacts=env.get("artifacts", []))]
    if env["status"] == "completed":
        return [halt(state, "p6_stale", "P6 passed on an older head; ask the user whether to rerun it",
                     run_id=env["run_id"])]
    return _stop(state, run, env, f"P6 is {env['status']}")


RESULT_HANDLERS = {"P3": p3_result, "P4": p4_result, "P5": p5_result, "P6": p6_result}


def on_poll(state, ev):
    if ev["kind"] == "ci":
        head = ev.get("head")
        if head and head != state["pr"]["head"]:
            return [checkpoint("stale_poll", f"CI poll for {head[:12]} ignored; PR head moved", post=False)]
        was = state["ci"]
        state["ci"] = ev["outcome"]
        if ev["outcome"] == "passing":
            return [checkpoint("ci_passing", "CI passing", post=was != "passing")]
        if ev["outcome"] != "failing":
            return [checkpoint("ci_" + ev["outcome"], f"CI {ev['outcome']}", post=False)]
        if any(r["phase"] == "P3" for r in state["active"].values()):
            return [checkpoint("ci_failing", "CI failing; rechecked after the active implementation run",
                               post=False)]
        request(state, "P3", "ci")
        return [checkpoint("ci_failing", "CI failing; fix queued", post=False)]
    queued = state["requests"].get("P3", {}).get("threads", [])
    new = [t for t in ev.get("ids", []) if t not in state["handled_threads"] and t not in queued]
    if not new:
        return [checkpoint("threads_none", "No new PR feedback", post=False)]
    request(state, "P3", "threads", threads=new)
    return [checkpoint("threads_new", f"{len(new)} new PR thread update(s); fix queued", post=False)]


def on_resume(state, ev):
    if not state["halt"]:
        raise FlowError("the router is not halted")
    rejected = [rid for rid, run in state["active"].items() if run.get("rejected")]
    if rejected:
        raise FlowError(f"resubmit or fail the rejected run(s) first: {', '.join(rejected)}")
    for grant in ev.get("grants", []):
        if grant == "review":
            state["review"]["cap"] += 1
        elif grant == "p5_rework":
            state["p5"]["rework_cap"] += 1
        else:
            raise FlowError(f"unknown grant {grant}")
    state["halt"] = []
    if ev.get("request"):
        request(state, ev["request"], ev.get("origin") or "resume", ev.get("inputs", []))
    return [checkpoint("resumed", ev.get("note") or "Resumed", post=False)]


def on_dependency_met(state, ev):
    if ev["name"] not in state["deps_met"]:
        state["deps_met"].append(ev["name"])
    return [checkpoint("dependency_met", f"Dependency met: {ev['name']}", post=False)]


def on_trigger_p6(state, ev):
    ver = state["handoffs"].get("verification")
    if ver is None or not ver["fields"].get("manual"):
        raise FlowError("the verification handoff has no manual scenarios")
    state["p6"]["triggered"] = True
    return [checkpoint("p6_triggered", "P6 requested by the user", post=False)]


def on_close(state, ev):
    state["closed"] = True
    return [checkpoint("closed", ev.get("note") or "Milestone closed", post=False)]


HANDLERS = {
    "init": on_init, "handoff": on_handoff, "dispatched": on_dispatched, "run_failed": on_run_failed,
    "result": on_result, "poll": on_poll, "resume": on_resume, "dependency_met": on_dependency_met,
    "trigger_p6": on_trigger_p6, "close": on_close,
}


def apply(state: dict, ev: dict) -> list:
    handler = HANDLERS.get(ev.get("type"))
    if handler is None:
        raise FlowError(f"unknown event type {ev.get('type')}")
    if state["milestone"] is None and ev["type"] != "init":
        raise FlowError("run init first")
    if state["closed"]:
        raise FlowError("the milestone is closed")
    return handler(state, ev) or []


def fold(events) -> dict:
    state = new_state()
    for ev in events:
        apply(state, ev)
    return state


# --------------------------------------------------------------------------
# Next actions (pure, with an injected hash lookup)
# --------------------------------------------------------------------------

def _ref(handoff) -> str:
    return f"{handoff['path']}@{handoff['sha256'][:12]}"


def spawn_action(state: dict, phase: str) -> dict:
    seq = state["seq"].get(phase, 0) + 1
    run_id = f"{state['milestone']}-{phase}-{seq}"
    req = state["requests"].get(phase, {"origins": [], "inputs": [], "threads": []})
    impl = state["handoffs"]["implementation"]
    ver = state["handoffs"].get("verification")
    pr = state["pr"]
    inputs = {"implementation_handoff": _ref(impl), "pr": pr["url"], "head": pr["head"]}
    extra = [state["milestone"]]
    action = {"action": "spawn", "run_id": run_id, "phase": phase, "agent": PHASES[phase]["agent"],
              "workflow": PHASES[phase]["workflow"]}
    if phase == "P3":
        inputs["origins"] = req["origins"]
        if req["inputs"]:
            inputs["findings"] = req["inputs"]
        if req["threads"]:
            inputs["pr_threads"] = req["threads"]
        extra += [ORIGIN_LABELS[o] for o in req["origins"] if ORIGIN_LABELS.get(o)]
    else:
        if ver is not None:
            inputs["verification_handoff"] = _ref(ver)
        inputs["last_reviewed_head"] = state["review"]["last_reviewed_head"]
    if phase == "P4":
        review = state["review"]
        action.update(round=review["rounds"] + 1, mode=review["mode"])
        inputs["previous_review"] = review["last_review"]
        extra.append(f"round {review['rounds'] + 1}")
        if review["mode"] != "initial":
            extra.append(review["mode"].replace("_", " "))
    if phase in ("P5", "P6"):
        inputs["scenarios"] = ver["fields"].get("auto" if phase == "P5" else "manual", [])
    action["session_name"] = " ".join([state["ticket"], phase, PHASES[phase]["name"], *extra])
    action["inputs"] = inputs
    action["result_path"] = f"results/{run_id}.json"
    return action


def _wait(phase, reason) -> dict:
    return {"action": "wait", "phase": phase, "reason": reason}


def _changed(state, kinds, hash_of):
    if hash_of is None:
        return None
    for kind in kinds:
        handoff = state["handoffs"].get(kind)
        if handoff and hash_of(handoff["path"]) != handoff["sha256"]:
            return f"the {kind} handoff changed since it was recorded; record it again with `handoff`"
    return None


def _p3_blocker(state, siblings, active_phases):
    if "P3" in active_phases:
        return "an implementation sub agent is already active"
    if "P5" in active_phases:
        return "P5 may be committing tests on the branch"
    if "P6" in active_phases:
        return "P6 may be committing tests on the branch"
    fields = state["handoffs"]["implementation"]["fields"]
    missing = [d for d in fields.get("depends_on", []) if d not in state["deps_met"]]
    if missing:
        return f"waiting on dependencies: {', '.join(missing)}"
    for name, other in siblings:
        other_impl = other["handoffs"].get("implementation")
        if not other_impl:
            continue
        busy = any(r["phase"] == "P3" for r in other["active"].values())
        same = (other_impl["fields"].get("branch") == fields.get("branch")
                or other_impl["fields"].get("workdir") == fields.get("workdir"))
        if busy and same:
            return f"milestone {name} has an implementation sub agent on the same branch or working directory"
    return None


def _verification_blocker(state, active_phases):
    queued = set(state["requests"])
    if "P3" in active_phases or "P3" in queued:
        return "waits for the implementation sub agent"
    if "P4" in active_phases or "P4" in queued:
        return "waits for the review round"
    return None


def next_actions(state: dict, siblings=(), hash_of=None) -> list:
    if state["closed"]:
        return [{"action": "done", "reason": "milestone closed"}]
    if state["halt"]:
        return [{"action": "halted", "reasons": state["halt"]}]
    if "implementation" not in state["handoffs"]:
        return [_wait(None, "no implementation handoff recorded")]
    actions = []
    active_phases = {run["phase"] for run in state["active"].values()}
    ver = state["handoffs"].get("verification")

    if "P3" in state["requests"]:
        reason = _p3_blocker(state, siblings, active_phases) or _changed(state, ["implementation"], hash_of)
        actions.append(_wait("P3", reason) if reason else spawn_action(state, "P3"))

    if "P4" in state["requests"]:
        reason = ("a review round is already running" if "P4" in active_phases else None) \
            or _changed(state, ["implementation"], hash_of)
        actions.append(_wait("P4", reason) if reason else spawn_action(state, "P4"))

    settled = review_settled(state) and "P4" not in state["requests"]
    auto = bool(ver and ver["fields"].get("auto"))
    if settled and auto and not is_current(state, state["p5"]["passed_head"]) and "P5" not in active_phases:
        reason = _verification_blocker(state, active_phases) \
            or _changed(state, ["implementation", "verification"], hash_of)
        actions.append(_wait("P5", reason) if reason else spawn_action(state, "P5"))

    if state["p6"]["triggered"] and "P6" not in active_phases:
        reason = None
        if not settled:
            reason = "P6 waits for a passing review on the current head"
        elif auto and not is_current(state, state["p5"]["passed_head"]):
            reason = "P6 waits for P5 to pass on the current head"
        reason = reason or _verification_blocker(state, active_phases) \
            or _changed(state, ["implementation", "verification"], hash_of)
        actions.append(_wait("P6", reason) if reason else spawn_action(state, "P6"))

    if not actions:
        if state["active"]:
            actions.append({"action": "wait", "phase": None,
                            "reason": "running: " + ", ".join(sorted(state["active"]))})
        else:
            actions.append({"action": "idle",
                            "reason": "nothing to dispatch; waiting for a poll, a user trigger or sign-off"})
    return actions


# --------------------------------------------------------------------------
# Validation (I/O)
# --------------------------------------------------------------------------

class Git:
    def __init__(self, workdir):
        self.workdir = str(workdir)

    def run(self, *args, stdin=None, check=True):
        proc = subprocess.run(["git", "-C", self.workdir, *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", input=stdin)
        if check and proc.returncode:
            raise GitError(f"git {' '.join(args)}: {proc.stderr.strip()}")
        return proc

    def out(self, *args) -> str:
        return self.run(*args).stdout.strip()

    def is_ancestor(self, older, newer) -> bool:
        return self.run("merge-base", "--is-ancestor", older, newer, check=False).returncode == 0

    def commit_exists(self, sha) -> bool:
        return self.run("cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0

    def patch_ids(self, base, tip) -> list:
        log = self.out("log", "-p", "--no-merges", "--no-color", "--no-decorate", f"{base}..{tip}")
        if not log:
            return []
        ids = self.run("patch-id", "--stable", stdin=log + "\n").stdout.split()
        return sorted(ids[0::2])

    def paths(self, commit) -> list:
        return self.out("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines()


def is_doc(path: str, patterns) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def classify_push(git: Git, old: str, new: str, target_ref: str, doc_patterns) -> dict:
    """Decide whether a push changes code. Errs toward "code": a wrong "code"
    costs one extra review round, a wrong "docs" ships unreviewed code."""
    push = {"from": old}
    if old == new:
        return dict(push, **{"class": "none"})
    if git.is_ancestor(old, new):
        merges = git.out("rev-list", "--merges", f"{old}..{new}").split()
        for merge in merges:
            # A remerge diff is empty for a clean merge and shows the
            # conflict resolution otherwise, which is new code.
            if git.out("show", "--remerge-diff", "--no-color", "--format=", merge):
                return dict(push, **{"class": "code", "reason": f"conflict resolution in {merge[:12]}"})
        own = git.out("rev-list", "--no-merges", f"{old}..{new}", "--not", target_ref).split()
        if not own:
            return dict(push, **{"class": "merge" if merges else "none"})
        paths = sorted({p for commit in own for p in git.paths(commit)})
        if paths and all(is_doc(p, doc_patterns) for p in paths):
            return dict(push, **{"class": "docs", "paths": paths})
        return dict(push, **{"class": "code", "paths": paths})
    old_base = git.out("merge-base", old, target_ref)
    new_base = git.out("merge-base", new, target_ref)
    if git.patch_ids(old_base, old) == git.patch_ids(new_base, new):
        return dict(push, **{"class": "rebase"})
    return dict(push, **{"class": "code", "reason": "history rewritten with changed patches"})


def internal_code_hits(git: Git, base: str, tip: str, patterns) -> list:
    messages = git.out("log", "--format=%B", f"{base}..{tip}")
    diff = git.out("diff", "--no-color", "-U0", base, tip)
    added = "\n".join(line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    hits = set()
    for pattern in patterns:
        hits.update(m.group(0) for m in re.finditer(pattern, messages + "\n" + added))
    return sorted(hits)[:10]


def check_shape(state: dict, run: dict, env: dict, mdir: Path) -> list:
    problems = []
    phase = run["phase"]
    status = env.get("status")
    if env.get("phase") != phase:
        problems.append(f"phase is {env.get('phase')!r}, expected {phase}")
    if status not in STATUSES[phase]:
        return problems + [f"status {status!r} is not valid for {phase}"]
    worked = status in ("completed", "changes_requested")
    head = env.get("head")
    if worked and not (isinstance(head, str) and SHA_RE.match(head)):
        problems.append("head must be the full commit SHA")
    if status == "needs_decision" and not env.get("question"):
        problems.append("needs_decision requires a question")
    if phase == "P3" and status == "completed" and not env.get("pr_url"):
        problems.append("completed implementation requires pr_url")
    if phase != "P3" and worked:
        if isinstance(head, str) and head not in state["pr"]["heads"]:
            problems.append(f"head {head[:12]} is not a head this PR has had")
        artifacts = env.get("artifacts") or []
        if not artifacts:
            problems.append("at least one artifact path is required")
        for item in artifacts:
            if not resolve(mdir, item).exists():
                problems.append(f"artifact not found: {item}")
    if phase == "P4" and status == "changes_requested":
        findings = env.get("findings")
        if not isinstance(findings, int) or findings < 1:
            problems.append("changes_requested requires findings >= 1")
    if phase in ("P5", "P6") and worked:
        problems.extend(_check_scenarios(state, phase, status, env))
    pushed = env.get("pushed_head")
    if pushed is not None and not (phase in ("P5", "P6") and isinstance(pushed, str) and SHA_RE.match(pushed)):
        problems.append("pushed_head is only for P5 or P6 test commits, as a full SHA")
    return problems


def _check_scenarios(state, phase, status, env) -> list:
    problems = []
    expected = state["handoffs"]["verification"]["fields"].get("auto" if phase == "P5" else "manual", [])
    scenarios = env.get("scenarios")
    if not isinstance(scenarios, dict):
        return ["scenarios must map each scenario id to pass, fail, inconclusive or invalid"]
    missing = [s for s in expected if s not in scenarios]
    if missing:
        problems.append(f"no result for scenario(s): {', '.join(missing)}")
    bad = [f"{k}={v}" for k, v in scenarios.items() if v not in OUTCOMES]
    if bad:
        problems.append(f"unknown outcome(s): {', '.join(bad)}")
    outcomes = set(scenarios.values())
    derived = "fail" if "fail" in outcomes else ("pass" if outcomes <= {"pass"} and not missing else "inconclusive")
    if status == "completed" and derived != "pass":
        problems.append(f"status is completed but the scenario results derive {derived}")
    if status == "changes_requested":
        if derived != "fail":
            problems.append(f"status is changes_requested but the scenario results derive {derived}")
        if phase == "P5" and env.get("route") not in ROUTES:
            problems.append("a P5 fail requires route: P3, P2, P1 or D1")
    return problems


def check_git(state: dict, run: dict, env: dict) -> tuple[list, dict | None]:
    """Check pushed commits against the remote and the internal-codes rule."""
    fields = state["handoffs"]["implementation"]["fields"]
    git = Git(fields["workdir"])
    branch, target_ref = fields["branch"], f"origin/{fields['target']}"
    phase = run["phase"]
    tip = env["head"] if phase == "P3" else env.get("pushed_head")
    if not tip:
        return [], None
    try:
        git.run("fetch", "--quiet", "origin", branch, fields["target"])
        if not git.commit_exists(tip):
            return [f"commit {tip[:12]} not found in {fields['workdir']}"], None
        problems = []
        remote = git.out("rev-parse", f"origin/{branch}")
        if remote != tip:
            problems.append(f"origin/{branch} is at {remote[:12]}, not the reported {tip[:12]}")
        prev = state["pr"]["head"] if phase == "P3" else env["head"]
        if phase != "P3" and not git.is_ancestor(env["head"], tip):
            problems.append("pushed_head does not descend from the head under test")
        base = prev if prev and git.is_ancestor(prev, tip) else git.out("merge-base", target_ref, tip)
        hits = internal_code_hits(git, base, tip, state["code_patterns"])
        if hits:
            problems.append(f"internal codes in commits or added lines: {', '.join(hits)}")
        push = None
        if phase == "P3":
            push = classify_push(git, prev, tip, target_ref, state["doc_patterns"]) if prev else {"class": "initial"}
            if prev and push["class"] == "none" and set(run["origins"]) & {"p4", "p5"}:
                problems.append("no new commits answer the findings")
        return problems, push
    except GitError as error:
        return [str(error)], None


# --------------------------------------------------------------------------
# Files and CLI
# --------------------------------------------------------------------------

def resolve(mdir: Path, path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else mdir / p


def relative(mdir: Path, path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(mdir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def file_sha(path: Path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict:
    """Flat `key: value` and `key: [a, b]` or `- item` lists; enough for handoffs."""
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data, key = {}, None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and key is not None:
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(_unquote(stripped[2:]))
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            data[key] = [_unquote(v) for v in value[1:-1].split(",") if v.strip()]
        elif value == "":
            data[key] = []
        else:
            data[key] = _unquote(value)
    for name in LIST_FIELDS:
        if isinstance(data.get(name), str):
            data[name] = [data[name]] if data[name] and data[name].lower() != "none" else []
    return data


def read_events(mdir: Path) -> list:
    path = mdir / "run.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_siblings(mdir: Path) -> list:
    out = []
    for other in sorted(mdir.resolve().parent.iterdir()):
        if other.is_dir() and other.resolve() != mdir.resolve() and (other / "run.jsonl").exists():
            out.append((other.name, fold(read_events(other))))
    return out


class Session:
    def __init__(self, mdir: Path, must_exist: bool = True):
        self.mdir = mdir
        self.events = read_events(mdir)
        if must_exist and not self.events:
            raise FlowError(f"no run.jsonl in {mdir}; run init first")
        self.state = fold(self.events)
        self.checkpoints = []

    def record(self, ev: dict) -> list:
        trial = copy.deepcopy(self.state)
        cps = apply(trial, ev)
        stamped = {"seq": len(self.events) + 1, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **ev}
        self.mdir.mkdir(parents=True, exist_ok=True)
        with (self.mdir / "run.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(stamped, sort_keys=True) + "\n")
        self.events.append(stamped)
        self.state = trial
        self.checkpoints.extend(cps)
        return cps

    def respond(self, dispatch: bool = True) -> dict:
        actions = next_actions(self.state, load_siblings(self.mdir),
                               hash_of=lambda p: file_sha(resolve(self.mdir, p)))
        for action in actions:
            if action["action"] == "spawn" and dispatch:
                self.record({"type": "dispatched", "run_id": action["run_id"], "phase": action["phase"],
                             "round": action.get("round"), "head": action["inputs"].get("head")})
            if "result_path" in action:
                action["result_path"] = str((self.mdir / action["result_path"]).resolve())
        return {"checkpoints": self.checkpoints, "actions": actions}


def load_result_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    try:
        env = json.loads(fence.group(1) if fence else text)
    except json.JSONDecodeError as error:
        raise FlowError(f"{path} is not JSON: {error}") from error
    if not isinstance(env, dict) or not env.get("run_id"):
        raise FlowError(f"{path} has no run_id")
    return env


def cmd_init(args):
    session = Session(args.dir, must_exist=False)
    if session.events:
        raise FlowError(f"{args.dir / 'run.jsonl'} already exists")
    (args.dir / "results").mkdir(parents=True, exist_ok=True)
    session.record({"type": "init", "milestone": args.milestone, "ticket": args.ticket, "track": args.track,
                    "code_patterns": args.code_pattern, "doc_patterns": args.doc_pattern})
    return session.respond(dispatch=not args.dry_run)


def cmd_handoff(args):
    session = Session(args.dir)
    path = Path(args.path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        raise FlowError(f"{path} not found")
    fields = parse_frontmatter(path.read_text(encoding="utf-8"))
    missing = [f for f in HANDOFF_FIELDS[args.kind] if not fields.get(f)]
    if missing:
        raise FlowError(f"{path.name} frontmatter is missing: {', '.join(missing)}")
    session.record({"type": "handoff", "kind": args.kind, "path": relative(args.dir, path),
                    "sha256": file_sha(path), "fields": fields})
    return session.respond(dispatch=not args.dry_run)


def cmd_result(args):
    session = Session(args.dir)
    env = load_result_file(Path(args.path))
    run = session.state["active"].get(env["run_id"])
    if run is None:
        raise FlowError(f"{env['run_id']} is not an active run")
    problems = check_shape(session.state, run, env, args.dir)
    push = None
    if not problems and env["status"] == "completed":
        git_problems, push = check_git(session.state, run, env)
        problems += git_problems
    session.record({"type": "result", "result": env, "problems": problems, "override": args.override,
                    "push": push})
    return session.respond(dispatch=not args.dry_run)


def cmd_event(args):
    session = Session(args.dir)
    kind = args.event
    if kind == "poll":
        if args.kind == "ci" and not args.outcome:
            raise FlowError("a CI poll needs --outcome")
        ev = {"type": "poll", "kind": args.kind, "outcome": args.outcome, "head": args.head, "ids": args.ids}
    elif kind == "run-failed":
        ev = {"type": "run_failed", "run_id": args.run_id, "reason": args.reason}
    elif kind == "resume":
        ev = {"type": "resume", "note": args.note, "grants": args.grant, "request": args.request,
              "origin": args.origin, "inputs": args.input}
    elif kind == "dependency-met":
        ev = {"type": "dependency_met", "name": args.name}
    elif kind == "trigger-p6":
        ev = {"type": "trigger_p6"}
    else:
        ev = {"type": "close", "note": args.note}
    session.record(ev)
    return session.respond(dispatch=not args.dry_run)


def cmd_next(args):
    return Session(args.dir).respond(dispatch=not args.dry_run)


def render_status(state: dict) -> str:
    review, p5, pr = state["review"], state["p5"], state["pr"]
    if state["closed"]:
        router = "closed"
    elif state["halt"]:
        router = "halted: " + "; ".join(h["message"] for h in state["halt"])
    else:
        router = "running"
    active = ", ".join(f"{rid} ({run['phase']})" for rid, run in state["active"].items()) or "none"
    queued = ", ".join(sorted(state["requests"])) or "none"
    cycle = "passed" if not review["open"] else "open"
    pushes = ", ".join(f"{(p.get('to') or '')[:12]} {p['class']}" for p in state["pushes"][-5:]) or "none"
    return "\n".join([
        "<!-- generated by scripts/artifex_flow.py status; regenerate, don't edit -->",
        f"Router: {router}",
        f"Review: {review['mode'].replace('_', ' ')} cycle {cycle}, round {review['rounds']} of {review['cap']}; "
        f"{review['total']} round(s) in total. CI: {state['ci']}",
        f"P5 reworks: {p5['reworks']} of {p5['rework_cap']}. Last reviewed head: "
        f"{(review['last_reviewed_head'] or 'none')[:12]}",
        f"PR: {pr['url'] or 'none'}. Head: {(pr['head'] or 'none')[:12]}. Recent pushes: {pushes}",
        f"Active runs: {active}. Queued: {queued}",
    ])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name, **kw):
        p = sub.add_parser(name, **kw)
        p.add_argument("--dir", type=Path, required=True, help="milestone folder")
        if name != "status":
            p.add_argument("--dry-run", action="store_true", help="print actions without recording dispatch")
        return p

    p = command("init")
    p.add_argument("--milestone", required=True)
    p.add_argument("--ticket", required=True)
    p.add_argument("--track", choices=["feature", "bug"], default="feature")
    p.add_argument("--code-pattern", action="append", default=[], help="extra internal-code regex")
    p.add_argument("--doc-pattern", action="append", default=[], help="extra docs-only glob")
    p.set_defaults(func=cmd_init)

    p = command("handoff")
    p.add_argument("--kind", choices=sorted(HANDOFF_FIELDS), required=True)
    p.add_argument("path")
    p.set_defaults(func=cmd_handoff)

    p = command("result")
    p.add_argument("path", help="result file (JSON)")
    p.add_argument("--override", help="accept despite validation problems, with the reason")
    p.set_defaults(func=cmd_result)

    p = command("event")
    events = p.add_subparsers(dest="event", required=True)
    poll = events.add_parser("poll")
    poll.add_argument("--kind", choices=["ci", "threads"], required=True)
    poll.add_argument("--outcome", choices=["passing", "failing", "pending"])
    poll.add_argument("--head")
    poll.add_argument("--ids", nargs="*", default=[], help="unresolved threads as <thread id>:<last comment id>")
    failed = events.add_parser("run-failed")
    failed.add_argument("--run-id", required=True)
    failed.add_argument("--reason")
    resume = events.add_parser("resume")
    resume.add_argument("--note", required=True)
    resume.add_argument("--grant", action="append", default=[], choices=["review", "p5_rework"])
    resume.add_argument("--request", choices=sorted(PHASES))
    resume.add_argument("--origin", choices=sorted(ORIGINS))
    resume.add_argument("--input", action="append", default=[])
    dep = events.add_parser("dependency-met")
    dep.add_argument("--name", required=True)
    events.add_parser("trigger-p6")
    close = events.add_parser("close")
    close.add_argument("--note", required=True)
    p.set_defaults(func=cmd_event)

    p = command("next")
    p.set_defaults(func=cmd_next)

    p = command("status")
    p.set_defaults(func=lambda args: render_status(Session(args.dir).state))
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output = args.func(args)
    except FlowError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(output if isinstance(output, str) else json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
