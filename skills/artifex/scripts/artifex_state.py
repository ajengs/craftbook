#!/usr/bin/env python3
"""Structured initiative state for Artifex, kept by the umbrella.

<initiative folder>/state.json holds the latest state only: each write
replaces a field or a row, so nothing piles up. Milestone progress through
P3-P6 isn't here; it lives in each milestone's run.jsonl and comes from the
router. STATE.md exists only when the user asks for one: `render` writes it
from this file and the routers.

Commands (each takes --dir <initiative folder>):
    init     create state.json
    set      replace fields of a section:      set status phase=P2 "next=Approve the specs"
    upsert   add or update one row of a table: upsert artifacts specs-M1 path=milestones/M1/specs.md sha256=...
    remove   drop a row:                       remove blockers gh-auth
    decide   append a material decision:       decide "Version 1.0.0" --artifact analysis
    show     print the JSON (or one section)
    render   print STATE.md, or write it with --out
    host     print the host and this session's own ids (no write)
    doc surface <doc>   print where a human-targeted document is reviewed on this host (no write)
    doc approve <doc>   record an approval, refusing a surface the host doesn't bind

Values are strings; `key:=<json>` passes JSON (lists, numbers, null) and `key=`
clears a field. Each write bumps `revision`, which is what a coordination
envelope cites.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifex_flow  # noqa: E402

SCHEMA = 1
SECTIONS = {
    "initiative": ("ticket", "title", "track"),
    "status": ("phase", "status", "next"),
    "workspace": ("workdir", "workdir_kind", "work_folder", "project_folder", "artifact_folder", "source"),
    "consent": ("status", "response", "date", "source", "scope", "umbrella_route"),
}
TABLES = {
    "sessions": ("role", "session_id", "route", "model", "effort", "runtime", "status"),
    "milestones": ("scope", "status", "session", "folder", "depends_on", "link"),
    "artifacts": ("path", "revision", "sha256", "decision", "date", "affects", "surface", "url", "host", "fallback"),
    "blockers": ("text", "since", "owner"),
    "polls": ("pr", "ci", "threads", "schedule", "last"),
}
STATUSES = ("draft", "pending approval", "implementing", "in review", "verifying", "ready for acceptance",
            "blocked", "closed")


# Human-targeted documents and where their markdown lives in the initiative folder.
DOCS = {"kickoff": "kickoff.md", "analysis": "analysis.md", "specs": "milestones/{m}/specs.md",
        "verification-contract": "milestones/{m}/verification-contract.md",
        "verification-report": "milestones/{m}/verification-report.md", "diagnosis": "milestones/{m}/diagnosis.md"}
# The review surface each host binds. A local file wins wherever its viewer annotates.
SURFACES = {"codex": "local-file", "claude-code": "claude-docs"}
SURFACE_CHOICES = ("local-file", "claude-docs", "native-doc", "chat")


class StateError(Exception):
    pass


def detect_host(env=None) -> dict:
    """Who is running this, from the environment; `ARTIFEX_HOST` overrides."""
    env = os.environ if env is None else env
    forced = env.get("ARTIFEX_HOST")
    if env.get("CLAUDECODE") == "1" and forced in (None, "claude-code"):
        return {"host": "claude-code", "entrypoint": env.get("CLAUDE_CODE_ENTRYPOINT"),
                "session_id": env.get("CLAUDE_CODE_SESSION_ID"),
                "host_session_id": env.get("CLAUDE_CODE_HOST_SESSION_ID")}
    codex = [k for k in env if k.startswith("CODEX_") and k != "CODEX_HOME"]
    if (codex and forced is None) or forced == "codex":
        return {"host": "codex", "entrypoint": None,
                "session_id": env.get("CODEX_THREAD_ID") or env.get("CODEX_SESSION_ID"), "host_session_id": None}
    return {"host": forced or "unknown", "entrypoint": None, "session_id": None, "host_session_id": None}


def doc_key(doc: str, milestone: str | None) -> tuple[str, str]:
    if doc not in DOCS:
        raise StateError(f"unknown document {doc!r}; documents: {', '.join(DOCS)}")
    if "{m}" in DOCS[doc] and not milestone:
        raise StateError(f"{doc} belongs to a milestone; give --milestone")
    return (f"{doc}-{milestone}" if "{m}" in DOCS[doc] else doc), DOCS[doc].format(m=milestone)


def surface_plan(folder: Path, doc: str, milestone: str | None, host: str) -> dict:
    name, rel = doc_key(doc, milestone)
    path = str((folder / rel).resolve())
    surface = SURFACES.get(host)
    approve = f"artifex_state.py --dir <initiative folder> doc approve {doc}" + (
        f" --milestone {milestone}" if milestone else "")
    if surface == "claude-docs":
        steps = [
            "Load the `docs` skill, then create a Claude Docs document for it with the docs tools. Without docs "
            "tools, publish it with the Artifact tool's `document` intent instead.",
            "Run every review round in that document; apply each comment to its passage.",
            "Don't create a local file for review and don't open one in the file pane: the user can't comment there.",
            f"After the user approves a revision, export it as markdown to {path}.",
            f"Report the document link, its revision if the tool shows one, and {path} to the umbrella, which runs "
            f"`{approve} --surface claude-docs --url <link> --file {path}`.",
        ]
    elif surface == "local-file":
        steps = [
            f"Create {path}.",
            "Open it in Codex's file viewer so the user can annotate passages. Don't create a Pages document.",
            "Run every review round in that file; apply each annotation to its passage.",
            f"Report {path} to the umbrella after approval, which runs `{approve} --surface local-file --file {path}`.",
        ]
    else:
        steps = [
            "Host unknown: use the local file if this host's viewer lets the user annotate a passage and send it to "
            "you; otherwise a native commentable document; otherwise chat comments on the markdown.",
            f"The approved markdown goes to {path}. Rerun with --host if you know the host.",
        ]
    plan = {"document": name, "host": host, "surface": surface or "choose", "path": path, "steps": steps}
    if surface == "local-file":
        plan["session_setup"] = {
            "workspace_folder": str(folder.resolve()),
            "rule": "The session that reviews this document must be created with this folder in its workspace "
                    "(a workspace root or added directory), or the viewer can't open the file. The umbrella sets "
                    "it when it creates P1, P2 or D1; a session already running without it is recreated, not "
                    "worked around.",
        }
    return {**plan,
            "if_it_fails": "Say what failed, take passage comments in chat on the markdown file, and tell the "
                           "umbrella, which approves with --surface chat --fallback \"<what failed>\""}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_state(ticket: str, title: str | None, track: str) -> dict:
    return {"schema": SCHEMA, "revision": 0, "updated": None,
            "initiative": {"ticket": ticket, "title": title, "track": track},
            "status": {}, "workspace": {}, "consent": {},
            **{table: {} for table in TABLES}, "decisions": []}


def parse_pairs(pairs, allowed) -> dict:
    out = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise StateError(f"expected key=value, got {pair!r}")
        as_json = key.endswith(":")
        key = key.rstrip(":")
        if key not in allowed:
            raise StateError(f"unknown field {key!r}; allowed: {', '.join(allowed)}")
        if as_json:
            try:
                out[key] = json.loads(value)
            except json.JSONDecodeError as error:
                raise StateError(f"{key}: not JSON: {error}") from error
        else:
            out[key] = value if value != "" else None
    return out


def merge(target: dict, fields: dict) -> None:
    for key, value in fields.items():
        if value is None:
            target.pop(key, None)
        else:
            target[key] = value


class Store:
    def __init__(self, folder: Path):
        self.folder = folder
        self.path = folder / "state.json"

    def load(self) -> dict:
        if not self.path.exists():
            raise StateError(f"no state.json in {self.folder}; run init first")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, state: dict) -> dict:
        state["revision"] += 1
        state["updated"] = now()
        self.folder.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)
        return {"revision": state["revision"], "path": str(self.path.resolve())}


def cmd_init(store: Store, args):
    if store.path.exists():
        raise StateError(f"{store.path} already exists")
    return store.save(new_state(args.ticket, args.title, args.track))


def cmd_set(store: Store, args):
    if args.section not in SECTIONS:
        raise StateError(f"unknown section {args.section!r}; sections: {', '.join(SECTIONS)}")
    fields = parse_pairs(args.pairs, SECTIONS[args.section])
    if args.section == "status" and fields.get("status") not in (None, *STATUSES):
        raise StateError(f"status must be one of: {', '.join(STATUSES)}")
    state = store.load()
    merge(state[args.section], fields)
    return store.save(state)


def cmd_upsert(store: Store, args):
    if args.table not in TABLES:
        raise StateError(f"unknown table {args.table!r}; tables: {', '.join(TABLES)}")
    fields = parse_pairs(args.pairs, TABLES[args.table])
    if args.table == "artifacts" and fields.get("decision") == "approved":
        raise StateError("record approvals with `doc approve`, which hashes the file and checks the review surface")
    state = store.load()
    if args.table == "milestones" and "status" in fields and fields["status"] is not None:
        folder = (state["milestones"].get(args.name) or {}).get("folder") or fields.get("folder") \
            or f"milestones/{args.name}"
        mdir = Path(folder) if Path(folder).is_absolute() else store.folder / folder
        if (mdir / "run.jsonl").exists():
            raise StateError(f"{args.name} is run by the router; its status comes from run.jsonl, not state.json")
    row = state[args.table].setdefault(args.name, {})
    merge(row, fields)
    return store.save(state)


def cmd_remove(store: Store, args):
    state = store.load()
    if args.table not in TABLES or args.name not in state[args.table]:
        raise StateError(f"no {args.table} row named {args.name!r}")
    del state[args.table][args.name]
    return store.save(state)


def cmd_decide(store: Store, args):
    state = store.load()
    entry = {"date": now()[:10], "text": args.text}
    if args.artifact:
        entry["artifacts"] = args.artifact
    state["decisions"].append(entry)
    return store.save(state)


def cmd_host(store: Store, args):
    return detect_host()


def cmd_doc_surface(store: Store, args):
    return surface_plan(store.folder, args.doc, args.milestone, args.host or detect_host()["host"])


def cmd_doc_approve(store: Store, args):
    name, rel = doc_key(args.doc, args.milestone)
    host = args.host or detect_host()["host"]
    bound = SURFACES.get(host)
    if bound and args.surface != bound and not args.fallback:
        raise StateError(f"{host} reviews documents in {bound}, not {args.surface}; "
                         "give --fallback with what failed if that surface couldn't be used")
    if args.surface in ("claude-docs", "native-doc") and not args.url:
        raise StateError(f"a {args.surface} approval needs --url")
    file = Path(args.file) if args.file else store.folder / rel
    if not file.is_file():
        raise StateError(f"approved markdown not found: {file}")
    state = store.load()
    row = state["artifacts"].setdefault(name, {})
    merge(row, {"path": str(file.resolve()), "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "decision": "approved", "date": now()[:10], "revision": args.revision, "surface": args.surface,
                "url": args.url, "host": host, "fallback": args.fallback})
    out = store.save(state)
    return {**out, "artifact": name, "sha256": row["sha256"]}


def cmd_show(store: Store, args):
    state = store.load()
    return state[args.section] if args.section else state


def _cell(value) -> str:
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value) or "none"
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def _table(rows: dict, columns) -> list:
    if not rows:
        return ["None."]
    lines = ["| Name | " + " | ".join(c.replace("_", " ").capitalize() for c in columns) + " |",
             "|---" * (len(columns) + 1) + "|"]
    for name, row in rows.items():
        lines.append(f"| {_cell(name)} | " + " | ".join(_cell(row.get(c)) for c in columns) + " |")
    return lines


def _fields(section: dict) -> list:
    return [f"- {k.replace('_', ' ').capitalize()}: {_cell(v)}" for k, v in section.items()] or ["Not recorded."]


def render(folder: Path, state: dict) -> str:
    ini = state["initiative"]
    out = [f"# STATE — {ini.get('ticket')}{(' ' + ini['title']) if ini.get('title') else ''}", "",
           f"Rendered from `state.json` revision {state['revision']} ({state['updated']}). "
           "Regenerate rather than edit; the umbrella doesn't read this file.", "",
           "## Status", *_fields(state["status"]), ""]
    milestones, routed = {}, []
    for name, row in state["milestones"].items():
        mdir = folder / (row.get("folder") or f"milestones/{name}")
        if (mdir / "run.jsonl").exists():
            router_state = artifex_flow.fold(artifex_flow.read_events(mdir))
            row = {**row, "status": "router: " + ("closed" if router_state["closed"] else
                                                  "halted" if router_state["halt"] else "running")}
            routed.append((name, artifex_flow.render_status(router_state)))
        milestones[name] = row
    out += ["## Milestones", *_table(milestones, TABLES["milestones"]), ""]
    for name, status in routed:
        out += [f"### Router — {name}", "```text", status, "```", ""]
    if state["blockers"]:
        out += ["## Blockers", *_table(state["blockers"], TABLES["blockers"]), ""]
    out += ["## Approved artifacts", *_table(state["artifacts"], TABLES["artifacts"]), ""]
    out += ["## Decisions"]
    out += [f"- {d['date']}: {d['text']}" + (f" ({', '.join(d['artifacts'])})" if d.get("artifacts") else "")
            for d in state["decisions"]] or ["None."]
    out += ["", "## Sessions", *_table(state["sessions"], TABLES["sessions"]), ""]
    if state["polls"]:
        out += ["## PR polls", *_table(state["polls"], TABLES["polls"]), ""]
    out += ["## Coordination consent", *_fields(state["consent"]), "",
            "## Workspace", *_fields(state["workspace"]), ""]
    return "\n".join(out)


def cmd_render(store: Store, args):
    text = render(store.folder, store.load())
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        return {"written": str(Path(args.out).resolve())}
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dir", type=Path, required=True, help="initiative folder")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("--ticket", required=True)
    p.add_argument("--title")
    p.add_argument("--track", choices=["feature", "bug"], default="feature")
    p.set_defaults(func=cmd_init)
    p = sub.add_parser("set")
    p.add_argument("section")
    p.add_argument("pairs", nargs="+")
    p.set_defaults(func=cmd_set)
    p = sub.add_parser("upsert")
    p.add_argument("table")
    p.add_argument("name")
    p.add_argument("pairs", nargs="*")
    p.set_defaults(func=cmd_upsert)
    p = sub.add_parser("remove")
    p.add_argument("table")
    p.add_argument("name")
    p.set_defaults(func=cmd_remove)
    p = sub.add_parser("decide")
    p.add_argument("text")
    p.add_argument("--artifact", action="append", default=[])
    p.set_defaults(func=cmd_decide)
    p = sub.add_parser("show")
    p.add_argument("--section")
    p.set_defaults(func=cmd_show)
    p = sub.add_parser("render")
    p.add_argument("--out", help="write STATE.md here instead of printing it")
    p.set_defaults(func=cmd_render)
    p = sub.add_parser("host")
    p.set_defaults(func=cmd_host)
    doc = sub.add_parser("doc").add_subparsers(dest="doc_command", required=True)
    for name, func in (("surface", cmd_doc_surface), ("approve", cmd_doc_approve)):
        p = doc.add_parser(name)
        p.add_argument("doc", choices=sorted(DOCS))
        p.add_argument("--milestone")
        p.add_argument("--host", choices=["claude-code", "codex", "other"])
        p.set_defaults(func=func)
        if name == "approve":
            p.add_argument("--surface", choices=SURFACE_CHOICES, required=True)
            p.add_argument("--file", help="the approved markdown; defaults to the document's place in the folder")
            p.add_argument("--url", help="the document link, for claude-docs or native-doc")
            p.add_argument("--revision", help="the provider's revision id, when it shows one")
            p.add_argument("--fallback", help="what failed, when the host's surface couldn't be used")
    return parser


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        output = args.func(Store(args.dir), args)
    except (StateError, artifex_flow.FlowError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(output if isinstance(output, str) else json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
