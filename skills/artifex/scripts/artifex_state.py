#!/usr/bin/env python3
"""Structured initiative state for Artifex, kept by the umbrella.

<initiative folder>/state.json holds the latest state only: each write
replaces a field or a row, so nothing piles up. Milestone progress through
P3-P6 isn't here; it lives in each milestone's run.jsonl and comes from the
router. STATE.md exists only when the user asks for one: `render` writes it
from this file and the routers.

Commands (each takes --dir <initiative folder>):
    init     create state.json from the invocation: init --mode <m> --mode-source explicit|recommended --request-file <f>
    route    read the invocation and print its mode, start and next commands (no write)
    set      replace fields of a section:      set status phase=P2 "next=Approve the specs"
    upsert   add or update one row of a table: upsert artifacts specs-M1 path=milestones/M1/specs.md sha256=...
    remove   drop a row:                       remove blockers gh-auth
    decide   append a material decision:       decide "Version 1.0.0" --artifact analysis
    show     print the JSON (or one section)
    render   print STATE.md, or write it with --out
    host     print the host and this session's own ids (no write)
    consent  record the consent question and the user's reply, both verbatim
    delivery record whether sub agents may branch, commit, push and open PRs, verbatim
    brief    print the launch prompt for a P1, P2 or D1 session (no write)
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
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifex_flow  # noqa: E402
from artifex_host import detect_host

SCHEMA = 1
SECTIONS = {
    "initiative": ("ticket", "title", "mode", "mode_source", "request"),
    "status": ("phase", "status", "next"),
    "workspace": ("workdir", "workdir_kind", "work_folder", "project_folder", "artifact_folder", "source"),
    "consent": ("status", "question", "response", "date", "source", "scope", "umbrella_route", "session_creation"),
    "delivery": ("status", "question", "response", "date", "source", "scope"),
}
TABLES = {
    "sessions": ("role", "session_id", "route", "model", "effort", "runtime", "status"),
    "milestones": ("scope", "status", "session", "folder", "depends_on", "link"),
    "artifacts": ("path", "revision", "sha256", "decision", "date", "affects", "surface", "url", "host", "fallback",
                  "source"),
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
# What a phase session says in chat while a document is under review.
REVIEW_MESSAGE = ["The document holds every detail. Don't restate any of it in chat: no current or target state, no specs or scenario tables, no behaviors to preserve, no edge cases, no summaries of sections.", "Every question the user must answer goes in the document's blocking questions or open decisions, with the options and your recommendation. Chat only points at it.", "Each review message is: one line with the link and the revision, then one 'Waiting on you' list, numbered, one line per item: the decision or approval needed and your recommendation in a few words. Nothing else.", 'Say each thing once. A later message lists only what is still open, without repeating the earlier one.', 'Exception: when the surface is `chat` (the fallback), paste the document once in that message.']


class StateError(Exception):
    pass


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
    plan = {"document": name, "host": host, "surface": surface or "choose", "path": path, "steps": steps,
            "review_message": REVIEW_MESSAGE}
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


def new_state(ticket: str, title: str | None, mode: str, mode_source: str, request: str | None = None) -> dict:
    initiative = {"ticket": ticket, "title": title, "mode": mode, "mode_source": mode_source}
    if request:
        initiative["request"] = request
    return {"schema": SCHEMA, "revision": 0, "updated": None,
            "initiative": initiative,
            "status": {}, "workspace": {}, "consent": {}, "delivery": {},
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


def effective_mode(state: dict) -> str:
    initiative = state["initiative"]
    return initiative.get("mode") or ("defect" if initiative.get("track") == "bug" else "project")


def cmd_init(store: Store, args):
    if store.path.exists():
        raise StateError(f"{store.path} already exists")
    request = verbatim(args, "request", True)
    parsed = parse_request(request, request_overrides(args))
    mode = parsed["mode"]
    contract = check_contract(mode, parsed)
    if not contract["ok"]:
        raise StateError(contract["problem"])
    if not parsed["ticket"]:
        raise StateError("no ticket in the request; name it like ABC-123 or give --ticket")
    state = new_state(parsed["ticket"], args.title, mode, args.mode_source, request)
    register_scope(state, mode, parsed, contract)
    out = store.save(state)
    return {**out, "mode": mode, "mode_source": args.mode_source, "contract": contract["result"],
            "next": next_commands(store.folder, mode, args.mode_source, parsed, contract, args)[1:]}


def cmd_set(store: Store, args):
    if args.section not in SECTIONS:
        raise StateError(f"unknown section {args.section!r}; sections: {', '.join(SECTIONS)}")
    if args.section == "initiative" and any(p.partition("=")[0].rstrip(":") == "track" for p in args.pairs):
        raise StateError("`track` is retired; an initiative's mode is fixed by `init`")
    fields = parse_pairs(args.pairs, SECTIONS[args.section])
    if args.section in ("consent", "delivery") and {"question", "response", "status", "session_creation"} & set(fields):
        raise StateError(f"record {args.section} with the `{args.section}` command, which keeps the question "
                         "and reply verbatim")
    if args.section == "initiative" and {"mode", "mode_source"} & set(fields):
        raise StateError("an initiative's mode is fixed by `init`; recreate the initiative to change it")
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


SKILL_DIR = Path(__file__).resolve().parent.parent
PHASE_BRIEFS = {
    "P1": ("research", "workflows/P1-research.md", "kickoff"),
    "P2": ("analysis", "workflows/P2-development-analysis.md", "specs"),
    "D1": ("bug investigation", "workflows/D1-bug-investigation.md", "diagnosis"),
}


def verbatim(args, name: str, required: bool = False):
    """Text given inline or, safer for quotes, newlines and shells that rewrite `/...`, from a file."""
    inline, file = getattr(args, name), getattr(args, f"{name}_file")
    if inline is not None and file is not None:
        raise StateError(f"give --{name} or --{name}-file, not both")
    if file is not None:
        return Path(file).read_text(encoding="utf-8").rstrip("\n")
    if inline is None and required:
        raise StateError(f"--{name} or --{name}-file is required")
    return inline


MODES = {
    "project": {"start": "P1", "contract": "a non-empty request"},
    "milestone": {"start": "P2", "contract": "a scope in the request: a file, a link or a description"},
    "defect": {"start": "D1", "contract": "a non-empty request"},
    "implementation": {"start": "router when the four artifacts are supplied, otherwise P2 (short)",
                       "contract": "specs, verification contract, implementation handoff and verification handoff, "
                                   "or any context for a short P2"},
}
MODE_ALIASES = {"bug": "defect"}
ARTIFACT_LABELS = {"specs": "specs", "contract": "verification contract", "handoff": "implementation handoff",
                   "verification_handoff": "verification handoff"}
ARTIFACT_DOCS = {"specs": "specs", "contract": "verification-contract", "handoff": "implementation-handoff",
                 "verification_handoff": "verification-handoff"}
REQUEST_FLAGS = {"--mode": "mode", "--ticket": "ticket", "--milestone": "milestone", "--scope": "scope",
                 "--specs": "specs", "--contract": "contract", "--handoff": "handoff",
                 "--verification-handoff": "verification_handoff"}
TICKET_ID = re.compile(r"^[A-Za-z][A-Za-z0-9]*-\d+$")
WEB_LINK = re.compile(r"^https?://", re.IGNORECASE)
DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
PATH_PREFIX = re.compile(r"^(?:[\\/]|\.{1,2}[\\/])")


def canonical_mode(value: str) -> str:
    mode = MODE_ALIASES.get(value.lower(), value.lower())
    if mode not in MODES:
        raise StateError(f"unknown mode {value!r}; modes: {', '.join(MODES)} (bug is accepted for defect)")
    return mode


def unquote(token: str) -> str:
    """Drop one matching pair of single quotes; an apostrophe on one edge is prose and stays."""
    return token[1:-1] if len(token) >= 2 and token[0] == token[-1] == "'" else token


def tokenize(text: str) -> list:
    lexer = shlex.shlex(text, posix=True)
    lexer.whitespace_split = True
    lexer.quotes = '"'
    lexer.escape = ""
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return text.split()


def parse_request(text: str, overrides: dict | None = None) -> dict:
    """What the invocation says: mode, ticket, existing files, links and the remaining free text."""
    tokens = tokenize(text)
    if tokens and tokens[0].lower() in ("/artifex", "artifex"):
        tokens = tokens[1:]
    leading = tokens[0] if tokens and tokens[0].lower() in (*MODES, *MODE_ALIASES) else None
    flags, rest, i = {}, [], 0
    while i < len(tokens):
        name, eq, value = tokens[i].partition("=")
        if name in REQUEST_FLAGS:
            if not eq:
                i += 1
                if i >= len(tokens):
                    raise StateError(f"{name} needs a value")
                value = tokens[i]
            if value.startswith("'") and unquote(value) == value:
                close = next((j for j in range(i + 1, len(tokens)) if tokens[j].endswith("'")), None)
                if close is not None:
                    value = " ".join([value, *tokens[i + 1:close + 1]])
                    i = close
            flags[REQUEST_FLAGS[name]] = unquote(value)
        else:
            rest.append(tokens[i])
        i += 1
    if leading is not None:
        rest.pop(0)
    flags.update({k: v for k, v in (overrides or {}).items() if v})
    seen = {}
    for label, value in (("--mode", flags.get("mode")), ("the leading word", leading)):
        if value:
            seen.setdefault(canonical_mode(value), []).append(f"{label} {value}")
    if len(seen) > 1:
        raise StateError("conflicting modes: " + " but ".join(v[0] for v in seen.values()))
    ticket = flags.get("ticket")
    if not ticket:
        ticket = next((t for t in rest if TICKET_ID.match(t)), None)
        if ticket:
            rest.remove(ticket)
    files, links, words = [], [], []

    def place(token: str) -> None:
        token = unquote(token)
        if WEB_LINK.match(token):
            links.append(token)
        elif Path(token).is_file():
            files.append(str(Path(token).resolve()))
        elif Path(token).is_dir():
            words.append(token)
        elif DRIVE_PATH.match(token.lstrip("'")) or PATH_PREFIX.match(token.lstrip("'")):
            raise StateError(f"path not found: {token.lstrip(chr(39))}")
        else:
            words.append(token)

    for token in rest:
        place(token)
    if flags.get("scope"):
        words.clear()
        place(flags["scope"])
    named = {}
    for key in ARTIFACT_LABELS:
        if flags.get(key):
            if not Path(flags[key]).is_file():
                raise StateError(f"path not found: {flags[key]}")
            named[key] = str(Path(flags[key]).resolve())
            if named[key] not in files:
                files.append(named[key])
    return {"mode": next(iter(seen), None), "ticket": ticket, "milestone": flags.get("milestone"),
            "files": files, "links": links, "text": " ".join(words), "named": named}


def request_overrides(args) -> dict:
    keys = ("mode", "ticket", "milestone", "scope", "specs", "contract", "handoff", "verification_handoff")
    return {k: getattr(args, k, None) for k in keys}


def recognise(path: str):
    """(artifact kind or None, problem or None) for a file in an implementation request."""
    text = Path(path).read_bytes()[:65536].decode("utf-8-sig", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    first = lines[0] if lines else ""
    if first == "---":
        fields = artifex_flow.parse_frontmatter(text)
        name = Path(path).name
        if {"auto", "manual"} <= set(fields):
            return "verification_handoff", None
        if {"branch", "workdir", "target"} <= set(fields):
            return "handoff", None
        if not fields:
            return None, f"{name}: the handoff frontmatter is empty; it needs branch, workdir and target (TBD allowed)"
        for kind, keys in (("implementation", ("branch", "workdir", "target")), ("verification", ("auto", "manual"))):
            if set(keys) & set(fields):
                return None, f"{name}: the {kind} handoff frontmatter lacks " + ", ".join(
                    k for k in keys if k not in fields)
        return None, None
    if first.startswith("#") and "Specifications" in first:
        return "specs", None
    if first.startswith("#") and "Verification contract" in first:
        return "contract", None
    return None, None


def classify_files(files: list, named: dict):
    claims, others, problems = {k: [] for k in ARTIFACT_LABELS}, [], []
    by_path = {}
    for kind, path in named.items():
        if path in by_path:
            problems.append(f"{Path(path).name} is named as both {ARTIFACT_LABELS[by_path[path]]} "
                            f"and {ARTIFACT_LABELS[kind]}")
        by_path[path] = kind
    for path in files:
        if path in by_path:
            kind, problem = by_path[path], None
            if kind == "handoff":
                fields = artifex_flow.parse_frontmatter(Path(path).read_text(encoding="utf-8", errors="replace"))
                missing = [k for k in ("branch", "workdir", "target") if k not in fields]
                if missing:
                    problem = f"{Path(path).name}: the handoff frontmatter lacks " + ", ".join(missing)
        else:
            kind, problem = recognise(path)
        if problem:
            problems.append(problem)
        elif kind:
            claims[kind].append(path)
        else:
            others.append(path)
    for kind, paths in claims.items():
        if len(paths) > 1:
            problems.append(f"{ARTIFACT_LABELS[kind]} recognised twice: " + " and ".join(Path(p).name for p in paths))
    return claims, others, problems


def check_contract(mode: str, parsed: dict) -> dict:
    """The entry contract of a mode. One function, so `route` and `init` can't disagree."""
    files, links, text = parsed["files"], parsed["links"], parsed["text"]
    out = {"mode": mode, "ok": False, "result": "failed", "problem": None, "artifacts": {}, "context": [],
           "start": MODES[mode]["start"]}
    if mode in ("project", "defect"):
        if parsed["ticket"] or files or links or text:
            out.update(ok=True, result="request given")
        else:
            out["problem"] = f"{mode} mode needs a request: a ticket, a file, a link or a description"
    elif mode == "milestone":
        if files or links or text:
            out.update(ok=True, result="scope given", context=[*files, *links])
        else:
            out["problem"] = "milestone mode needs a scope: a file, a link or a description in the request"
    else:
        claims, others, problems = classify_files(files, parsed["named"])
        out["artifacts"] = {k: v[0] for k, v in claims.items() if v}
        out["context"] = [*others, *links]
        if problems:
            out["problem"] = "; ".join(problems)
        elif len(out["artifacts"]) == len(ARTIFACT_LABELS):
            out.update(ok=True, result="artifacts ready", start="router")
        elif text or links or files:
            out.update(ok=True, result="short P2", start="P2")
        else:
            out["problem"] = ("implementation mode needs the four artifacts (specs, verification contract, "
                              "implementation handoff, verification handoff) or context for a short P2")
    return out


def milestone_id(parsed: dict) -> str:
    return parsed["milestone"] or "M1"


def register_scope(state: dict, mode: str, parsed: dict, contract: dict) -> None:
    if mode not in ("milestone", "implementation"):
        return
    mid, day = milestone_id(parsed), now()[:10]
    context = contract["context"]
    link = context[0] if context else None
    row = {"status": "selected", "link": link, "scope": parsed["text"] or None}
    state["milestones"][mid] = {k: v for k, v in row.items() if v}
    if mode == "milestone":
        return
    ready = contract["result"] == "artifacts ready"
    for kind, path in contract["artifacts"].items():
        entry = {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                 "decision": "supplied", "date": day}
        if ready and kind in ("specs", "contract"):
            entry.update(decision="approved", surface="invocation",
                         source="the user's Artifex invocation, which supplied it (recorded in initiative.request)")
        state["artifacts"][f"{ARTIFACT_DOCS[kind]}-{mid}"] = entry
    for n, item in enumerate(context, 1):
        state["artifacts"][f"context-{mid}-{n}"] = {("path" if item in parsed["files"] else "url"): item,
                                                      "decision": "supplied", "date": day}


def next_commands(folder: Path, mode: str, source: str, parsed: dict, contract: dict, args) -> list:
    script = SKILL_DIR / "scripts" / "artifex_state.py"
    cmd = f'python "{script}" --dir "{folder.resolve()}"'
    mid = milestone_id(parsed)
    request = getattr(args, "request_file", None)
    init = f"{cmd} init --mode {mode} --mode-source {source}" + (
        f' --request-file "{request}"' if request else " --request <the invocation>")
    for key, value in request_overrides(args).items():
        if value and key != "mode":
            init += f' --{key.replace("_", "-")} "{value}"'
    steps = [init, "Ask once for phase/replacement-session creation and bidirectional coordination, plus delivery authorization; record the verbatim replies with `consent --session-creation` and `delivery`."]
    if contract["result"] == "artifacts ready":
        flow = f'python "{SKILL_DIR / "scripts" / "artifex_flow.py"}"'
        mdir = (folder / "milestones" / mid).resolve()
        arts = contract["artifacts"]
        steps += [f'{flow} init --dir "{mdir}" --milestone {mid} --ticket {parsed["ticket"] or "<ticket>"} '
                  "--umbrella-session <id>",
                  f'{flow} handoff --dir "{mdir}" --kind implementation "{arts["handoff"]}"',
                  f'{flow} handoff --dir "{mdir}" --kind verification "{arts["verification_handoff"]}"']
    elif mode == "project":
        steps.append(f"{cmd} brief P1")
    elif mode == "defect":
        steps.append(f"{cmd} brief D1")
    else:
        steps.append(f"{cmd} brief P2 --milestone {mid}" + (" --short" if mode == "implementation" else ""))
    return steps


def cmd_route(store: Store, args):
    if store.path.exists():
        state = store.load()
        mode = effective_mode(state)
        return {"stored": True, "mode": mode, "mode_source": state["initiative"].get("mode_source"),
                "start": MODES[mode]["start"] if mode in MODES else None,
                "note": "this initiative already exists; its stored mode applies and the request is not read"}
    parsed = parse_request(verbatim(args, "request", True), request_overrides(args))
    found = {"ticket": parsed["ticket"], "files": parsed["files"], "links": parsed["links"], "text": parsed["text"]}
    if not parsed["mode"]:
        return {"needs_recommendation": True, **found,
                "modes": [{"mode": m, "start": v["start"], "contract": v["contract"]} for m, v in MODES.items()],
                "next": ["Recommend one mode with reasons; start nothing until the user approves it, then run "
                         "`init --mode <mode> --mode-source recommended --request-file <f>` and the printed start."]}
    mode = parsed["mode"]
    contract = check_contract(mode, parsed)
    out = {"mode": mode, "mode_source": "explicit", "start": contract["start"], **found,
           "milestone": milestone_id(parsed) if mode in ("milestone", "implementation") else None,
           "contract": {"ok": contract["ok"], "result": contract["result"], "problem": contract["problem"],
                        "artifacts": contract["artifacts"], "context": contract["context"]}}
    out["next"] = next_commands(store.folder, mode, "explicit", parsed, contract, args) if contract["ok"] else []
    return out


def cmd_consent(store: Store, args):
    args.question, args.response = verbatim(args, "question", True), verbatim(args, "response", True)
    state = store.load()
    host = detect_host()
    merge(state["consent"], {
        "status": args.status, "session_creation": args.session_creation,
        "question": args.question, "response": args.response, "date": now()[:10],
        "source": args.source, "scope": args.scope or state["consent"].get("scope"),
        "umbrella_route": args.route or host["host_session_id"] or host["session_id"]
        or state["consent"].get("umbrella_route"),
    })
    return store.save(state)


DELIVERY_SCOPE = ("implementation and verification phase workers may create the branch, commit, push to it and open "
                  "the pull request; merging, deploying and backporting are not included")


def cmd_delivery(store: Store, args):
    state = store.load()
    if args.from_request:
        if not state["initiative"].get("request"):
            raise StateError("no request recorded; init with --request-file first")
        question, response = "(stated in the user's Artifex invocation)", state["initiative"]["request"]
    else:
        question, response = verbatim(args, "question", True), verbatim(args, "response", True)
    state.setdefault("delivery", {})
    merge(state["delivery"], {"status": args.status, "question": question, "response": response,
                              "date": now()[:10], "source": args.source, "scope": args.scope or DELIVERY_SCOPE})
    return store.save(state)


def _quote(text: str) -> str:
    return "\n".join("> " + line for line in str(text).splitlines() or [""])


def brief(folder: Path, state: dict, phase: str, milestone: str | None, name: str | None,
          short: bool = False) -> str:
    """The launch prompt, built only from recorded state so nothing is paraphrased on the way."""
    title, workflow, first_doc = PHASE_BRIEFS[phase]
    ini, consent = state["initiative"], state["consent"]
    if phase == "P2" and not milestone:
        raise StateError("a P2 brief needs --milestone")
    if short and phase != "P2":
        raise StateError("--short applies to a P2 brief only")
    if not consent.get("status"):
        raise StateError("no consent recorded; ask the consent question and record it with `consent` first")
    if consent["status"] == "authorized" and not (consent.get("question") and consent.get("response")):
        raise StateError("consent lacks the verbatim question or reply; record it again with `consent`")
    ticket = ini["ticket"]
    name = name or " ".join(x for x in (ticket, phase, title, milestone) if x)
    script = SKILL_DIR / "scripts" / "artifex_state.py"
    cmd = f'python "{script}" --dir "{folder.resolve()}"'
    doc_arg = first_doc + (f" --milestone {milestone}" if milestone and first_doc != "kickoff" else "")
    lines = [
        f"You are the Artifex {phase} {title} session for {ticket}, named \"{name}\". You are not the umbrella.",
        "",
        f"Skill: {SKILL_DIR / 'SKILL.md'}. Workflow: {SKILL_DIR / workflow}. Read those and what they link, "
        "nothing else of the package.",
        f"Initiative folder: {folder.resolve()}. State: state.json revision {state['revision']}; read it with "
        f"`{cmd} show`.",
        "",
        "First steps:",
        f"1. Run `{cmd} host` and report its `session_id` through the authorized channel or human relay.",
        f"2. Before drafting the {first_doc}, run `{cmd} doc surface {doc_arg}` and follow what it prints.",
    ]
    if milestone:
        row = state["milestones"].get(milestone) or {}
        lines += ["", f"Milestone: {milestone}" + (f". Scope: {row['scope']}" if row.get("scope") else "")
                  + (f". Link: {row['link']}" if row.get("link") else "")]
        if short:
            lines += ["", "## Short P2",
                      "This is a short P2: the user supplied no kickoff or analysis, and the invocation may already "
                      "hold some of the artifacts below.",
                      "- Draft the specs and the verification contract in one document on the specs surface.",
                      "- The specs part is approved first and produces the implementation handoff and its "
                      "checkpoint at once.",
                      "- The contract part follows: once approved, it produces the verification handoff.",
                      "- Export each approved part to specs.md and verification-contract.md."]
            supplied = {k: v for k, v in state["artifacts"].items()
                        if v.get("decision") == "supplied" and k.endswith(f"-{milestone}")
                        or k.startswith(f"context-{milestone}-")}
            if supplied:
                lines += ["", "Supplied artifacts and context:"]
                lines += [f"- {k}: {v.get('path') or v.get('url')}" for k, v in supplied.items()]
    approved = {k: v for k, v in state["artifacts"].items() if v.get("decision") == "approved"}
    if approved:
        lines += ["", "Approved artifacts (path, SHA-256):"]
        lines += [f"- {k}: {v.get('path')} ({v.get('sha256')})" for k, v in approved.items()]
    if ini.get("request"):
        lines += ["", "The user's request, verbatim:", _quote(ini["request"])]
    lines += ["", "## Coordination authorization"]
    if consent.get("session_creation") == "authorized":
        lines += ["The recorded authorization also covers creating phase and replacement sessions for this "
                  "initiative; do not ask again before each creation. New scope still needs the user."]
    else:
        lines += ["Automatic session creation is not authorized by this record. Do not infer creation permission "
                  "from coordination-only consent; use manual creation or obtain the expanded authorization once."]
    if consent["status"] == "authorized":
        lines += [
            f"On {consent.get('date')}, in {consent.get('source') or 'the umbrella chat'}, the umbrella asked the "
            "user:", _quote(consent["question"]), "", "The user replied, verbatim:", _quote(consent["response"]), "",
            "That reply is the user's direct authorization for the umbrella and every phase session it creates "
            f"for {ticket} to message each other in both directions, within the scope asked about"
            + (f": {consent['scope']}" if consent.get("scope") else "") + ".",
            f"Umbrella route: {consent.get('umbrella_route') or 'not recorded'}.",
        ]
    else:
        lines += [f"Not authorized (status: {consent['status']}). Don't message the umbrella; give every "
                  "checkpoint to the user to relay."]
    delivery = state.get("delivery") or {}
    if delivery.get("status"):
        lines += ["", "## Delivery authorization",
                  f"On {delivery.get('date')}, the user was asked:", _quote(delivery["question"]), "",
                  "and replied, verbatim:", _quote(delivery["response"]), "",
                  f"Status: {delivery['status']}. Scope: {delivery.get('scope')}. Handoffs you write rely on this "
                  "record; don't ask the user again for what it covers."]
    return "\n".join(lines) + "\n"


def cmd_brief(store: Store, args):
    return brief(store.folder, store.load(), args.phase, args.milestone, args.name, args.short)


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
    artifact_columns = tuple(c for c in TABLES["artifacts"]
                             if c != "source" or any(r.get("source") for r in state["artifacts"].values()))
    out += ["## Approved artifacts", *_table(state["artifacts"], artifact_columns), ""]
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


def request_options(p) -> None:
    p.add_argument("--request", help="the user's Artifex invocation, verbatim")
    p.add_argument("--request-file", help="a file holding the invocation verbatim; prefer it over --request")
    p.add_argument("--ticket", help="override the ticket the request names")
    p.add_argument("--milestone", help="the milestone id; defaults to M1")
    p.add_argument("--scope", help="override the scope: a file, a link or a description")
    p.add_argument("--specs", help="the specs file, when it isn't recognised")
    p.add_argument("--contract", help="the verification contract file, when it isn't recognised")
    p.add_argument("--handoff", help="the implementation handoff file, when it isn't recognised")
    p.add_argument("--verification-handoff", help="the verification handoff file, when it isn't recognised")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dir", type=Path, required=True, help="initiative folder")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("--mode", required=True, help="project, milestone, defect (or bug) or implementation")
    p.add_argument("--mode-source", choices=["explicit", "recommended"], required=True)
    p.add_argument("--title")
    request_options(p)
    p.set_defaults(func=cmd_init)
    p = sub.add_parser("route")
    p.add_argument("--mode", help="override the mode the request states")
    request_options(p)
    p.set_defaults(func=cmd_route)
    p = sub.add_parser("consent")
    p.add_argument("--status", choices=["authorized", "declined", "manual relay"], required=True)
    p.add_argument("--session-creation", choices=["authorized", "declined"],
                   help="the same reply explicitly covers creating phase and replacement sessions")
    p.add_argument("--question", help="the question exactly as asked")
    p.add_argument("--question-file", help="a file holding the question verbatim")
    p.add_argument("--response", help="the user's reply exactly as written")
    p.add_argument("--response-file", help="a file holding the reply verbatim")
    p.add_argument("--source", help="where it was asked, such as the umbrella chat")
    p.add_argument("--scope")
    p.add_argument("--route", help="the umbrella's route; defaults to this session's own id")
    p.set_defaults(func=cmd_consent)
    p = sub.add_parser("delivery")
    p.add_argument("--status", choices=["authorized", "declined"], required=True)
    p.add_argument("--question")
    p.add_argument("--question-file")
    p.add_argument("--response")
    p.add_argument("--response-file")
    p.add_argument("--from-request", action="store_true",
                   help="the user granted it in the Artifex invocation itself; quote that")
    p.add_argument("--source")
    p.add_argument("--scope")
    p.set_defaults(func=cmd_delivery)
    p = sub.add_parser("brief")
    p.add_argument("phase", choices=sorted(PHASE_BRIEFS))
    p.add_argument("--milestone")
    p.add_argument("--name", help="the session name, if not the conventional one")
    p.add_argument("--short", action="store_true", help="a short P2: specs and contract drafted in one document")
    p.set_defaults(func=cmd_brief)
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
