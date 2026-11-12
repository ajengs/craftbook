# Initiative state: `state.json`

The umbrella's working state for an initiative is one JSON file, `<initiative folder>/state.json`, written only through `scripts/artifex_state.py`. It's for agents, not people, so it holds the latest state and nothing else: each write replaces a field or a row in place. There's no history to scroll past and no stale "Next" line left behind.

P3–P6 progress isn't in it. Review rounds, heads, pushes, CI, active runs and halts live in each milestone's `run.jsonl` and come from the router (`references/orchestration.md`). Routine router transitions therefore write nothing here.

**STATE.md** exists only when the user asks to see the state. `render --out <initiative folder>/STATE.md` writes it from `state.json` plus each milestone's router status. Nobody edits or reads it back; render it again when asked again.

## Commands

Run `python <skill>/scripts/artifex_state.py --dir <initiative folder> <command>`. Each write prints `{"revision": n, "path": ...}`.

| Command | Use |
|---|---|
| `route --request-file <f> [--mode <m>] [override flags]` | First, when the umbrella starts: reads the mode, ticket, files, links and free text from the invocation, checks the mode's entry contract and prints the start and the next commands. Writes nothing; with no mode it prints `needs_recommendation` and the mode table. For an initiative that already has a `state.json` it reports the stored mode |
| `init --mode <project\|milestone\|defect\|implementation> --mode-source <explicit\|recommended> --request-file <f> [--title <t>] [--ticket <id>] [--milestone <id>] [--scope <s>] [--specs <f>] [--contract <f>] [--handoff <f>] [--verification-handoff <f>]` | Once, after `route`. It parses the same request, runs the same contract check and refuses on failure. `bug` is stored as `defect`. Milestone and implementation modes register the milestone row; implementation with all four artifacts also records the supplied specs and contract as approved with `surface: invocation` |
| `consent --status <s> --question-file <f> --response-file <f> [--source <where>] [--scope <s>]` | The user answers the consent question. Both texts are stored verbatim; `--question`/`--response` work too, but files survive quotes, newlines and shells that rewrite `/...` |
| `delivery --status <authorized\|declined> (--question-file <f> --response-file <f> \| --from-request) [--source <where>]` | The user answers the delivery question, or granted it in the invocation. Stored verbatim; the router holds P3 until it exists and passes it to every P3, P5 and P6 spawn |
| `brief <P1\|P2\|D1> [--milestone <id>] [--name <n>] [--short]` | Creating a phase session: prints its launch prompt from state, quoting the request and the consent question and reply verbatim. Pass it unchanged. `--short` (P2) adds the short-P2 instructions and the supplied artifact paths |
| `set <section> key=value ...` | Replace fields of `status`, `workspace`, `consent` or `initiative` |
| `upsert <table> <name> key=value ...` | Add or update one row of `sessions`, `milestones`, `artifacts`, `blockers` or `polls` |
| `remove <table> <name>` | Drop a row, such as a resolved blocker |
| `decide "<text>" [--artifact <name>]` | Append a material decision with its rationale |
| `show [--section <name>]` | Print the JSON, when recovering or answering a question |
| `render [--out <path>]` | Produce `STATE.md` for the user |
| `host` | Print the host and this session's own ids; a new phase session reports its `session_id` from this |
| `doc surface <doc> [--milestone <id>] [--host <h>]` | Before drafting a human-targeted document: where to review it on this host, the markdown path, the steps and any `session_setup` |
| `doc approve <doc> --surface <s> [--url] [--revision] [--file] [--fallback]` | The only way to record an approval: hashes the markdown and checks the surface against the host |

`key=value` stores a string, `key:=<json>` stores JSON (lists, numbers), and `key=` removes the field. Unknown sections, tables or fields are refused, which keeps the file in one shape across sessions. Chain several commands in one shell call with `&&` when one checkpoint changes several things.

## Shape

| Part | Fields | Written when |
|---|---|---|
| `initiative` | ticket, title, mode, mode_source, request | `init`; `request` is the user's invocation verbatim; `mode` is fixed at `init` and `set` refuses it. An older file that carries `track` and no `mode` loads as it is: its effective mode is `defect` for `bug`, otherwise `project` |
| `status` | phase, status, next | A phase starts or ends, or a posted checkpoint changes the next step. Status is one of draft, pending approval, implementing, in review, verifying, ready for acceptance, blocked, closed |
| `delivery` | status, question, response, date, source, scope | Once, at the start, through `delivery` only |
| `workspace` | workdir, workdir_kind, work_folder, project_folder, artifact_folder, source | Resolved at the start (`SKILL.md`, Workspace) |
| `consent` | status, question, response, date, source, scope, umbrella_route | The user answers the consent question, through `consent` only |
| `sessions` row per session name | role, session_id, route, model, effort, runtime, status | A phase session (P1, P2, D1) is created or finishes. `session_id` is the host's own id for it (the thread id in Codex; in Claude Code the transcript name if known, otherwise the `local_…` id the app returns), recorded at creation so its whole transcript can be costed later. A Claude Code `local_…` id doesn't name its transcript, so `artifex_cost.py` falls back to the session's title, which is why the row name must be the exact session name; P3–P6 agents are recorded by the router instead (`event started --agent`). `runtime` says what the host confirmed, or `unconfirmed` |
| `milestones` row per id | scope, status, session, folder, depends_on, link | `init` in milestone or implementation mode, P1 selects it, or P2 starts. `status` is for before the router takes over; once the milestone has a `run.jsonl`, setting it is refused and `render` shows the router's state instead. `link` ties a D1 folder to its milestone and finding |
| `artifacts` row per name | path, revision, sha256, decision, date, affects, surface, url, host, fallback, source | An approval is recorded, or an approved artifact changes; `init` in implementation mode records the artifacts the invocation supplied |
| `blockers` row per id | text, since, owner | A blocker appears; `remove` it when resolved |
| `polls` row per PR | pr, ci, threads, schedule, last | A poll schedule is armed or changes, so a resumed umbrella can re-arm it |
| `decisions` list | date, text, artifacts | A material decision, once |

`revision` goes up by one on every write. A coordination envelope cites `state.json` by path and revision.
