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

Values are strings; `key:=<json>` passes JSON (lists, numbers, null) and `key=`
clears a field. Each write bumps `revision`, which is what a coordination
envelope cites.
"""

from __future__ import annotations

import argparse
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
    "sessions": ("role", "route", "model", "effort", "runtime", "status"),
    "milestones": ("scope", "status", "session", "folder", "depends_on", "link"),
    "artifacts": ("path", "revision", "sha256", "decision", "date", "affects"),
    "blockers": ("text", "since", "owner"),
    "polls": ("pr", "ci", "threads", "schedule", "last"),
}
STATUSES = ("draft", "pending approval", "implementing", "in review", "verifying", "ready for acceptance",
            "blocked", "closed")


class StateError(Exception):
    pass


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
    state = store.load()
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
    milestones = state["milestones"]
    out += ["## Milestones", *_table(milestones, TABLES["milestones"]), ""]
    for name, row in milestones.items():
        mdir = folder / (row.get("folder") or f"milestones/{name}")
        if (mdir / "run.jsonl").exists():
            status = artifex_flow.render_status(artifex_flow.fold(artifex_flow.read_events(mdir)))
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
