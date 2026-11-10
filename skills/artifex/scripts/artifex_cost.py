#!/usr/bin/env python3
"""Token cost of an Artifex milestone, from Claude Code and Codex transcripts.

Reads the milestone's run.jsonl (through artifex_flow.run_report) and, when
the initiative has one, state.json; finds each transcript on either host; and
reports tokens for:
    - the umbrella, sliced into windows between router events;
    - each P3-P6 agent run;
    - each phase session (P1, P2, D1) recorded in state.json.

    python artifex_cost.py --dir <milestone folder> [--json]

Token categories are reported raw, per host, because prices differ by model:
    uncached   input tokens read at full price
    cache_read input tokens served from the prompt cache
    cache_write input tokens written to the cache (Claude Code only)
    output     output tokens, reasoning included
Claude Code transcripts report usage per message; Codex rollouts report running
totals, so a Codex turn is the difference between consecutive totals, and its
input_tokens include the cached ones.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifex_flow  # noqa: E402

FIELDS = ("uncached", "cache_read", "cache_write", "output")


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def first_line(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                return json.loads(line)
    return {}


# --------------------------------------------------------------------------
# Transcripts -> turns
# --------------------------------------------------------------------------

def is_codex(path: Path) -> bool:
    return first_line(path).get("type") == "session_meta"


def claude_turns(path: Path) -> list:
    turns, seen = [], set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = m.get("message") or {}
        if m.get("type") != "assistant" or "timestamp" not in m or msg.get("id") in seen:
            continue
        seen.add(msg.get("id"))
        u = msg.get("usage") or {}
        turns.append({"ts": ts(m["timestamp"]), "uncached": u.get("input_tokens", 0),
                      "cache_read": u.get("cache_read_input_tokens", 0),
                      "cache_write": u.get("cache_creation_input_tokens", 0), "output": u.get("output_tokens", 0)})
    return turns


def codex_turns(path: Path) -> list:
    turns, prev = [], {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = m.get("payload") or {}
        info = payload.get("info") or {}
        total = info.get("total_token_usage")
        if payload.get("type") != "token_count" or not total or total == prev:
            continue
        d = {k: total.get(k, 0) - prev.get(k, 0) for k in
             ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens")}
        prev = total
        turns.append({"ts": ts(m["timestamp"]), "uncached": d["input_tokens"] - d["cached_input_tokens"],
                      "cache_read": d["cached_input_tokens"], "cache_write": d["cache_write_input_tokens"],
                      "output": d["output_tokens"]})
    return turns


def turns_of(path: Path) -> list:
    return codex_turns(path) if is_codex(path) else claude_turns(path)


def total(turns) -> dict:
    out = {"turns": len(turns), **{f: sum(t[f] for t in turns) for f in FIELDS}}
    if turns:
        out.update(first=turns[0]["ts"].isoformat(), last=turns[-1]["ts"].isoformat())
    return out


# --------------------------------------------------------------------------
# Finding transcripts
# --------------------------------------------------------------------------

class Hosts:
    def __init__(self, claude_home: Path, codex_home: Path):
        self.projects = claude_home / "projects"
        self.codex_roots = [codex_home / "sessions", codex_home / "archived_sessions"]

    def _rollouts(self, pattern="rollout-*.jsonl"):
        for root in self.codex_roots:
            if root.exists():
                yield from root.rglob(pattern)

    def session(self, sid: str | None, title: str | None = None):
        """(path, how) for an umbrella or phase session id, falling back to its title."""
        if sid:
            bare = sid[len("local_"):] if sid.startswith("local_") else sid
            for candidate in {sid, bare}:
                hits = sorted(self.projects.glob(f"*/{candidate}.jsonl")) if self.projects.exists() else []
                hits += sorted(self._rollouts(f"rollout-*-{candidate}.jsonl"))
                if hits:
                    return hits[0], "id"
        if title and self.projects.exists():
            hits = []
            for meta in self.projects.glob("*/*/custom-title.json"):
                try:
                    if json.loads(meta.read_text(encoding="utf-8")).get("customTitle") == title:
                        transcript = meta.parent.with_suffix(".jsonl")
                        if transcript.exists():
                            hits.append(transcript)
                except (OSError, json.JSONDecodeError):
                    continue
            if len(hits) == 1:
                return hits[0], "title"
            if hits:
                return None, f"title matches {len(hits)} transcripts"
        return None, "not found"

    def agent(self, agent_id: str):
        if self.projects.exists():
            for name in {agent_id, agent_id if agent_id.startswith("agent-") else f"agent-{agent_id}"}:
                hits = sorted(self.projects.glob(f"*/*/subagents/{name}.jsonl"))
                if hits:
                    return hits[0]
        hits = sorted(self._rollouts(f"rollout-*-{agent_id}.jsonl"))
        return hits[0] if hits else None

    def children(self, umbrella: Path) -> list:
        """(path, description, first timestamp) for each sub agent the umbrella started."""
        out = []
        if is_codex(umbrella):
            parent = first_line(umbrella).get("payload", {}).get("id")
            for path in self._rollouts():
                meta = first_line(path).get("payload", {})
                source = meta.get("source") if isinstance(meta.get("source"), dict) else {}
                spawn = (source.get("subagent") or {}).get("thread_spawn") or {}
                if parent and parent in (meta.get("parent_thread_id"), spawn.get("parent_thread_id")):
                    out.append((path, meta.get("agent_nickname") or "", ts(meta["timestamp"])
                                if meta.get("timestamp") else None))
            return out
        folder = umbrella.with_suffix("") / "subagents"
        for path in sorted(folder.glob("agent-*.jsonl")) if folder.exists() else []:
            meta_path = path.with_suffix(".meta.json")
            description = ""
            if meta_path.exists():
                description = json.loads(meta_path.read_text(encoding="utf-8")).get("description") or ""
            turns = claude_turns(path)
            out.append((path, description, turns[0]["ts"] if turns else None))
        return out


def match_child(run: dict, children: list, taken: set):
    """Pick the sub agent of a run logged without an agent id: by session name, else by time window."""
    free = [c for c in children if c[0] not in taken]
    if run.get("session_name"):
        named = [c for c in free if c[1] == run["session_name"]]
        if len(named) == 1:
            return named[0][0], "session name"
    start = ts(run["started"] or run["dispatched"])
    end = ts(run["ended"]) if run.get("ended") else start + timedelta(days=1)
    timed = [c for c in free if c[2] and start <= c[2] <= end]
    if len(timed) == 1:
        return timed[0][0], "time window"
    return None, f"{len(timed)} candidates in its time window" if timed else "no candidate"


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def windows(turns, events) -> list:
    bounds = []
    for ev in events:
        label = f"{ev['seq']}:{ev['type']}"
        if ev.get("run_id"):
            label += f" {ev['run_id']}"
        if ev["type"] in ("result", "complete"):
            label += f" {ev['result']['run_id']}={ev['result']['status']}"
        bounds.append((ts(ev["ts"]), label))
    groups = {}
    for turn in turns:
        label = "before router"
        for start, name in bounds:
            if turn["ts"] >= start:
                label = name
        groups.setdefault(label, []).append(turn)
    order = ["before router"] + [name for _, name in bounds]
    return [{"window": name, **total(groups[name])} for name in order if name in groups]


def report(mdir: Path, hosts: Hosts, initiative: Path | None = None) -> dict:
    events = artifex_flow.read_events(mdir)
    if not events:
        raise artifex_flow.FlowError(f"no run.jsonl in {mdir}")
    runs = artifex_flow.run_report(events)
    out = {"milestone": str(mdir), "umbrella": [], "runs": {}, "phase_sessions": {}, "unresolved": []}
    umbrella_paths = []
    for entry in runs["umbrella"]:
        path, how = hosts.session(entry["session"])
        if path is None:
            out["unresolved"].append(f"umbrella {entry['session']}: {how}")
            continue
        umbrella_paths.append(path)
        turns = turns_of(path)
        lo = ts(entry["from"]) if entry is not runs["umbrella"][0] else None
        hi = ts(entry["to"]) if entry["to"] else None
        turns = [t for t in turns if (lo is None or t["ts"] >= lo) and (hi is None or t["ts"] < hi)]
        out["umbrella"].append({"session": entry["session"], "transcript": str(path),
                                "host": "codex" if is_codex(path) else "claude", "total": total(turns),
                                "windows": windows(turns, events)})
    children = [c for path in umbrella_paths for c in hosts.children(path)]
    taken = set()
    for run_id, run in runs["runs"].items():
        path, how = (hosts.agent(run["agent"]), "agent id") if run["agent"] else (None, "")
        if path is None:
            path, how = match_child(run, children, taken)
        if path is None:
            out["unresolved"].append(f"run {run_id}: {how}")
            continue
        taken.add(path)
        out["runs"][run_id] = {"phase": run["phase"], "outcome": run["outcome"], "transcript": str(path),
                               "matched_by": how, **total(turns_of(path))}
    if initiative and (initiative / "state.json").exists():
        state = json.loads((initiative / "state.json").read_text(encoding="utf-8"))
        for name, row in state.get("sessions", {}).items():
            path, how = hosts.session(row.get("session_id") or row.get("route"), title=name)
            if path is None:
                out["unresolved"].append(f"session {name}: {how}")
                continue
            out["phase_sessions"][name] = {"role": row.get("role"), "transcript": str(path), "matched_by": how,
                                           **total(turns_of(path))}
    out["totals"] = {
        "umbrella": _sum(u["total"] for u in out["umbrella"]),
        "agents": _sum(out["runs"].values()),
        "phase_sessions": _sum(out["phase_sessions"].values()),
    }
    return out


def _sum(items) -> dict:
    items = list(items)
    return {k: sum(i.get(k, 0) for i in items) for k in ("turns", *FIELDS)}


def _row(label, t) -> str:
    return f"{label[:44]:44} {t['turns']:6} {t['uncached']:10} {t['cache_read']:11} {t['cache_write']:11} {t['output']:8}"


def render(rep: dict) -> str:
    head = f"{'':44} {'turns':>6} {'uncached':>10} {'cache_read':>11} {'cache_write':>11} {'output':>8}"
    lines = []
    for u in rep["umbrella"]:
        lines += [f"Umbrella {u['session']} ({u['host']})", head]
        lines += [_row("  " + w["window"], w) for w in u["windows"]]
        lines += [_row("  total", u["total"]), ""]
    if rep["runs"]:
        lines += ["Agent runs", head]
        lines += [_row(f"  {rid} {r['phase']} {r['outcome'] or 'open'} [{r['matched_by']}]", r)
                  for rid, r in rep["runs"].items()]
        lines.append("")
    if rep["phase_sessions"]:
        lines += ["Phase sessions", head]
        lines += [_row(f"  {name} [{s['matched_by']}]", s) for name, s in rep["phase_sessions"].items()]
        lines.append("")
    lines += ["Totals", head] + [_row(f"  {k}", v) for k, v in rep["totals"].items()]
    if rep["unresolved"]:
        lines += ["", "Unresolved:"] + [f"  {u}" for u in rep["unresolved"]]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dir", type=Path, required=True, help="milestone folder")
    parser.add_argument("--initiative", type=Path, help="initiative folder; defaults to two levels up")
    parser.add_argument("--claude-home", type=Path, default=Path.home() / ".claude")
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    initiative = args.initiative or args.dir.resolve().parent.parent
    try:
        rep = report(args.dir, Hosts(args.claude_home, args.codex_home), initiative)
    except artifex_flow.FlowError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(rep, indent=2) if args.json else render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
