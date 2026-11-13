# Router: scripted P3–P6 transitions

`scripts/artifex_flow.py` decides the routine moves of the implementation loop: what starts after an agent finishes, whether a push starts a review round, when a cap is reached, when P5 runs. The umbrella runs it, does what it prints, and spends its own judgment only on what the router hands back as an exception.

Who decides what:

- **Router:** which agent runs next, the review round and rework caps, push classification, retries after a failed run, and checking each agent result against its artifacts and the remote before acting on it.
- **Umbrella:** what the user sees, approvals, design decisions, routes back to P2, P1 or D1, inconclusive results, and every halt.
- **Agents:** their scoped work. Each writes a finalized result file and reports its path through the host completion channel.

The router launches nothing. On Codex it prints `create_session` instructions for independent chats or `manual_session` handoffs after declined consent; on other hosts it retains `spawn`, so a `spawn` action is an instruction for the umbrella to carry out word for word. The umbrella carries out the returned action and records the actual session/agent id. It needs Python 3.10+ and git 2.36+, and nothing else.

## Files

| File | Writer | Holds |
|---|---|---|
| `milestones/<id>/run.jsonl` | Router only | Append-only events: handoffs, dispatches, results, polls, resumes. The state is a fold over this log |
| `milestones/<id>/results/<run id>.json` | The agent of that run | Its result file, and nothing else |
| `milestones/<id>/evidence/<run id>/` | The P5 or P6 agent of that run | Raw verification output |
| `state.json` (initiative folder) | Umbrella, through `scripts/artifex_state.py` | Decisions, approvals, consent, sessions, blockers (`references/state.md`). Nothing the router already holds |

Each file has one writer. Never edit `run.jsonl` by hand; record an event instead. Routine transitions write only `run.jsonl`: the umbrella touches `state.json` for what it decides or posts, not for what the router did.

## Umbrella loop

Run every command with `python <skill>/scripts/artifex_flow.py <command> --dir <milestone folder>`. Every command except `status`/`runs` prints `{"checkpoints": [...], "actions": [...]}`.

1. **Start the milestone:** `init --milestone M1 --ticket PROJ-123 --umbrella-session <id>` once, then `handoff --kind implementation <path>` right after the implementation handoff is written. The first implementation handoff returns a `compact_umbrella` checkpoint: everything P1 and P2 settled is on disk by then, so compact the umbrella if the host lets it, or post the suggestion to the user (`SKILL.md`, Execution efficiency). Record `handoff --kind verification <path>` once the verification handoff exists. For a bug, the diagnosis is recorded as the verification handoff.
2. **Carry out the actions in order:**
   - `create_session` (Codex): call the named `mcp__codex_app__create_thread` with the returned `session_name` as title, the complete `prompt` unchanged and the confirmed project/workspace. The prompt contains the assigned inputs, result/evidence paths, user's verbatim initiative authorization and `report_to` umbrella route. `role_config` is model/effort guidance, not native subagent selection. Record the returned independent thread id with `event started --run-id <id> --agent <thread id>`. Do not spawn a native subagent for the phase. Creation and replacement are covered by the one-time initiative authorization; do not ask before each call. If creation fails, record `event run-failed` with the actual reason.
   - `manual_session` (Codex, declined creation or coordination): this is a registered run, not permission for the umbrella to create or message a chat. Give the user its session name and complete prompt to launch manually. Record `event started --run-id <id> --agent <user-supplied thread id>` when they confirm the session; if no id is available, record the start without it and retain the cost-report limitation. The worker uses human relay rather than a cross-session callback. When the user supplies its finalized result path, run `result <path>` normally. This works for P3, P4, P5 and P6; the latter still needs its explicit trigger. Reprinted unconfirmed handoffs keep the same run id.
   - `spawn` (other hosts): start the returned isolated worker using its role, inputs and workflow, and record `event started --agent <harness id>`. P3/P5/P6 inputs carry the verbatim `delivery_authorization`; creating a session does not add permission to commit or push.
   - An action with `unconfirmed` means an automatic launch or manual handoff was printed but no start was recorded. Check the recorded session name, run id and host inventory. If it exists, record its id; if it never started, perform the returned creation/spawn once; otherwise record the launch failure. Never create a duplicate just because a response or message was lost.
   - `wait`: the reason names a running phase or a prerequisite. On Codex, handle actionable prerequisites and independent work, then end the turn. A phase's authorized cross-session completion message resumes the umbrella. Do not use native agent waits, sleep loops, heartbeat messages or repeated status polling to keep the umbrella active.
   - `idle`: nothing is queued. Wait for a poll result, a user trigger or sign-off.
   - `halted`: handle every listed reason with the user (see Exceptions), then record `event resume`.
   - `done`: the milestone is closed.
3. **When an agent returns a path:** run `result <path>`, post its `post: true` checkpoints (including verdict and report links), then carry out its actions in the same turn. Agent execution completing does not mean review passed. P3 completion starts P4 without waiting for CI or the verification handoff; P4 findings start the returned rework. Apply the host completion rule below when more work remains; ending the umbrella turn while phase sessions run is not workflow completion.
4. **Post** each checkpoint with `post: true`, as one line or as the results it points to. Checkpoints with `post: false` are already in `run.jsonl`: don't post them and don't copy them into `state.json` (`SKILL.md`, Reporting to the user).
5. **After each poll:** `event poll --kind ci --outcome passing|failing|pending|none --head <sha>` (`none`: the repository has no CI at all, so the router stops waiting on it), or `event poll --kind threads --ids <thread>:<last comment id> ...` with every unresolved thread. The router queues a fix only for threads it hasn't dispatched in that version. The umbrella still schedules and runs the polls (`SKILL.md`, Polling belongs to the umbrella).
6. **On user decisions the router can't see:**
   - `event dependency-met --name <dependency as written in the handoff>`
   - `event trigger-p6` when the user asks for P6
   - `event close --note <sign-off>` after the user signs off
7. **When the umbrella is resumed or replaced:** run `event umbrella --session <id>` first, on every open milestone. Each recorded session id, together with the timestamps in `run.jsonl`, lets the umbrella's tokens be sliced per transition later. `<id>` is the umbrella's own session or thread id: in Claude Code the transcript file name under `~/.claude/projects/`, in Codex the thread id. If it isn't known, leave it out and note that with `artifex_state.py decide`. Recording the same id twice in a row is a no-op. `runs` lists every umbrella session and run with its window and agent id, and names any run recorded without an agent id.

**Completion evidence.** When investigating a missed handoff, capture the host's completion and delivery timestamps and the umbrella turn/wake time when available, alongside the router result and started events. Record unavailable timestamps as unknown. The router cannot measure delivery or wake-up, and this loop is not a background scheduler.

**Measuring cost.** `python <skill>/scripts/artifex_cost.py --dir <milestone folder> [--json]` reads `runs`, finds each transcript on Claude Code (`~/.claude/projects/`) or Codex (`~/.codex/sessions/`, `~/.codex/archived_sessions/`), and reports turns and tokens (uncached input, cache read, cache write, output) for the umbrella per window between router events, for each agent run, and for each phase session in `state.json`. A legacy native run logged without an agent id may be matched among the umbrella's subagents by name or time window; an independent phase chat needs its actual thread id recorded, and missing identities remain explicit measurement gaps; the report says which match it used and lists whatever it couldn't find. Codex totals are running sums, so the script turns them into per-turn differences; its input counts include cached tokens, which the script separates out.
8. **Reconcile on every wake:** consume cross-session checkpoints/results before unrelated coordination or a status answer. On resume, read `runs` for run ids with `ended: null`, their recorded thread ids and start confirmations, even during a halt. Use `next` for routing and unconfirmed creations; a halt suppresses all new launches but does not prevent accepting an existing worker's result. A finalized result message is the publication boundary, even if the sender is still finishing its reporting call: no further code/artifact writes are allowed after publication. If recovering a file without a completion message, confirm with the owning session that it is finalized, or that the session ended, before consuming it. A failed/ended session with no usable result uses `event run-failed`; a rejected result remains an explicit blocker. Do not infer readiness merely from a file appearing. If the cross-session send fails, retain the result and report manual relay as the blocker. An identical accepted envelope can be replayed safely; a changed result for a closed run is refused. Check inventory before acting on an unconfirmed launch returned by replay. Recover an unreported verdict from the accepted result/artifacts in the log; replay does not repost old checkpoints.
9. **When the user asks where things stand:** `status` covers one milestone; `artifex_state.py render` covers the initiative with every milestone's router status, and `render --out <initiative folder>/STATE.md` writes it as a file.

`--dry-run` prints actions without recording dispatches. Use it for a look ahead.

## Host completion rules

- **Codex:** all phases are independent top-level chats. `create_session` is printed only when the initiative's verbatim consent record authorizes both phase/replacement-session creation (`session_creation: authorized`) and coordination (`status: authorized`). A missing/old record asks for the expanded authorization once; a declined record selects a registered `manual_session` handoff and human result relay. End the umbrella turn after its current coordination work. Phase sessions publish finalized results through `mcp__codex_app__send_message_to_thread`, which resumes an idle umbrella. This uses independent-session communication; native child-to-ancestor messaging is not an alternative.
- **Claude Code:** preserve foreground Agent completion and background completion notifications; the latter arrive in a later turn. Separate planning sessions keep their existing cross-session channel. No Codex-style native-wait loop is required. See [Claude Code completion notifications](https://code.claude.com/docs/en/sub-agents#tools-permissions-and-results-of-background-subagents).
- **Other hosts:** retain their scoped workers and actual completion channel; if it is unavailable, report the limitation and use manual relay.

When upgrading an existing Codex initiative, obtain the expanded creation/coordination authorization once and reconcile any already-active native runs through their existing result/recovery channel. Do not convert an active native run into a second chat or claim it can send to its native ancestor. New dispatches use independent sessions.

Codex dispatch requires an initiative `state.json`; router-only Codex operation is unsupported because phase creation/coordination must be tied to the recorded human decision. If it is absent, initialize the initiative with `artifex_state.py init` before recording consent and starting phases. Other-host router-only behavior is unchanged.

`--host codex|claude-code|other` overrides host detection for testing or a host without detectable environment variables. It changes dispatch transport, not phase gates. A returned action is not evidence that its session was created or a message delivered. Exercise the actual phase chain and failure recovery on the target host; neither the script nor cross-session messaging guarantees continuation after the app/session closes.

## Command cheat sheet

Prefix: `python <skill>/scripts/artifex_flow.py <command> --dir <milestone folder>`. For `event`, `--dir` may also come after the event name (`event started --run-id … --dir …`). Arguments in `[]` are optional.

| Command | When |
|---|---|
| `init --milestone <id> --ticket <id> --umbrella-session <id> [--code-pattern <regex>] [--doc-pattern <glob>]` | Once per milestone |
| `handoff --kind implementation\|verification <path>` | A handoff (or diagnosis) is written or changed |
| `result <path> [--override "<reason>"]` | An agent returned its result file path; identical accepted envelopes are safe to replay |
| `next [--dry-run]` | Nothing new happened and you want the actions again |
| `status` | The user asks about one milestone |
| `runs` | Recovering session routes, or measuring cost: every run with its agent id and time window, and each umbrella session with its window |
| `event started --run-id <id> [--agent <harness id>]` | An automatic or manual phase session/worker is confirmed running |
| `event run-failed --run-id <id> [--reason "<why>"]` | A spawn failed, or an agent ended without a result file |
| `event poll --kind ci --outcome passing\|failing\|pending\|none [--head <sha>]` | After a CI poll |
| `event poll --kind threads [--ids <thread>:<comment> ...]` | After a PR-thread poll, with every unresolved thread |
| `event context [--branch <b>] [--workdir <path>] [--target <b>] [--note "<source>"]` | The user settles a `TBD` in the implementation handoff |
| `event complete --run-id <id> --head <sha> [--pr-url <url>] --note "<what the user did>" [--override "<reason>"]` | A halted P3 run needs no more agent work after the user's answer |
| `event complete --head <sha> --pr-url <url> --note "<what the user did>"` (no `--run-id`) | Delivery is declined and the user did the queued implementation by hand |
| `event resume --note "<decision>" [--request P3\|P4\|P5\|P6] [--origin p4\|p5\|ci\|threads\|resume] [--input "<text>" ...] [--grant review\|p5_rework]` | Any other halt, once handled |
| `event dependency-met --name <dependency>` | A `depends_on` item landed |
| `event trigger-p6` | The user asks for P6 |
| `event close --note "<sign-off>"` | The user signs off |
| `event umbrella --session <id>` | A resumed or replacement umbrella, first thing |

## Handoff frontmatter

The router reads only the frontmatter, not the body. Keep the values literal.

```yaml
---
branch: dev/proj-123-batch-lookup    # implementation handoff
workdir: D:\src\proj                 # the checkout or worktree the user confirmed
target: main                         # the PR's target branch
depends_on: none                     # or a list; each item is released by dependency-met
---
```

`branch`, `workdir` and `target` may be `TBD` when the user hasn't settled them by the time the specs are approved. The router records the handoff, posts which values are open and holds P3 until the umbrella records the user's answer with `event context`. It then passes those values to the implementation agent as `handoff_context`, which replaces the placeholders. The handoff file isn't rewritten for this and P2 isn't involved. Once P3 has started or a PR exists, these values are fixed.

```yaml
---
auto: [V1, V2]                       # verification handoff or diagnosis: scenario ids P5 runs
manual: [V3]                         # scenario ids P6 runs; [] when none
---
```

When a recorded handoff file changes, the router stops dispatching anything that reads it until `handoff` records it again. That way a stale handoff can't reach an agent unnoticed.

## Result file

Every P3–P6 worker writes this JSON to its assigned `result_path`. On Codex, it then reports the finalized path by cross-session message; other hosts return it through their completion channel:

```json
{
  "run_id": "M1-P4-2",
  "phase": "P4",
  "status": "changes_requested",
  "head": "<full 40-character commit SHA>",
  "artifacts": ["review-r2.md"],
  "findings": 3,
  "summary": "Two missing null checks; one spec partly covered."
}
```

| Field | When | Meaning |
|---|---|---|
| `run_id`, `phase` | Always | As given in the spawn |
| `status` | Always | `completed`, `changes_requested`, `blocked`, `needs_decision` or `inconclusive` (P3 has only the first, third and fourth) |
| `head` | `completed`, `changes_requested` | The full SHA that was pushed (P3), reviewed (P4) or tested (P5, P6) |
| `pr_url` | P3 `completed` | The PR |
| `artifacts` | P4–P6 with a verdict | Paths to the review or report, relative to the milestone folder |
| `findings` | P4 `changes_requested` | Number of blocks-merge findings, at least 1 |
| `scenarios` | P5, P6 with a verdict | `{"V1": "pass" \| "fail" \| "inconclusive" \| "invalid"}`, every assigned scenario |
| `route` | P5 `changes_requested` | `P3`, `P2`, `P1`, or `D1` for a major finding (`workflows/P5-verification.md`) |
| `pushed_head` | P5, P6, when tests were pushed | The new branch head after the test commits |
| `question` | `needs_decision` | The decision, with options and a recommendation, as the workflow describes |
| `summary` | Optional | Up to three lines for the umbrella |

Phase verdicts map to statuses like this:

- **P4:** `pass` → `completed`; `blocked` → `changes_requested`; `inconclusive` → `inconclusive`.
- **P5, P6:** `pass` → `completed`; `fail` → `changes_requested`.

In a result file, `blocked` means the agent couldn't make progress, not that review findings block the merge.

## Result delivery

On Codex, finish all changes and evidence first, write the complete result file, and make no further code or artifact writes after publishing it. For `manual_session`, give the user the finalized path to relay; do not send coordination messages. The umbrella records the relayed result with the same `result` command and validation as automatic completion. For authorized automatic sessions, follow the message protocol below. Send the umbrella a single completion/checkpoint containing `run_id`, `phase` and the absolute finalized result path with `mcp__codex_app__send_message_to_thread`. Use the direct human authorization carried in the prompt, and refresh the latest umbrella route from `runs` before sending. The sender does not submit the result or edit shared state. The umbrella runs `result <path>`, posts the verdict/report and performs the returned actions. Report blocked/needs-decision outcomes too. Retain the result and record the exact blocker if the send is rejected; do not switch tools or poll to bypass it. End the phase session with the result path. A duplicate message is reconciled through the existing replay checks, not by launching another worker.

## What the router checks before acting

A result that fails any check halts the router as `result_rejected`, and the run stays open. Fix the result file and run `result` again; or use `result <path> --override "<reason>"` when the user accepts the problem; or record `run-failed` to retry it. Nothing is retried on its own when a check fails.

- **Every result:**
  - the run is active;
  - phase and status are valid;
  - the fields its status requires are present;
  - the artifacts exist;
  - the head is one this PR has had.
- **P3 `completed`, and P5 or P6 with `pushed_head`:**
  - `origin/<branch>` points at the reported commit;
  - the pushed commits' messages and added lines contain no internal codes (`SPEC-n`, `VER-n` and any `--code-pattern` from `init`);
  - a rework that answers findings actually added commits.
- **P5 and P6:**
  - every assigned scenario has an outcome;
  - the status agrees with the outcomes. `completed` needs all of them to pass; `changes_requested` needs at least one fail and, for P5, a route.

## Routine transitions

| Event | Condition | Router does |
|---|---|---|
| Implementation handoff recorded | No PR yet | Starts P3 once `state.json` has a delivery record; until then it waits and says so |
| P3 `completed`, first PR | — | Posts the PR, starts review round 1 |
| P4 `changes_requested` | Rounds left in the cycle | Starts a P3 rework with the review artifacts |
| P3 rework answering P4 | — | Starts the next round, giving it the previous review and the last reviewed head |
| P4 `completed` | Reviewed head is the current code | Posts the pass. P5 starts once the verification handoff has auto scenarios; otherwise posts that P6 applies, or that sign-off is needed |
| P4 `completed` | Code was pushed after the reviewed head | One incremental round for the gap |
| P5 `changes_requested`, route P3 | Fewer than 2 reworks | Starts a P3 rework, then a one-round review, then P5 again |
| P5 or P6 `completed` | Tested head is current | Posts the result, and P6 or sign-off |
| CI poll failing, or new thread versions | — | Queues a P3 fix (one implementer at a time) |
| P3 fix pushed before the review first passed | — | Records it; the next round covers it |
| P3 push after the review passed | Code or test change | One incremental round. P5 reruns after it if it had run |
| P3 push after the review passed | Docs only, a rebase with unchanged patches, or a clean merge of the target | Records it; the review and P5 carry forward |
| Spawn failed, or the agent ended without a result | First failure of that work | Retries once. A failed review run doesn't use a round |
| Spawn printed but never confirmed | — | Prints the same spawn again on every call until `started` or `run-failed` |
| CI poll `none` | — | Stops waiting on CI; sign-off no longer says to keep polling |

Push classes come from git, and the classification leans toward `code`:

- `docs`: every changed path matches the doc globs (`*.md`, `*.rst`, `*.txt`, `docs/*`, plus any `--doc-pattern`).
- `rebase`: same patch ids after a history rewrite.
- `merge`: only clean merges of the target branch.
- `code`: anything else, including a merge with conflict resolution. A wrong `code` costs one review round; a wrong `docs` would let unreviewed code through.

Concurrency rules:

- One P3 at a time per milestone.
- P3 doesn't start while P5 or P6 may be committing tests on the branch.
- P3 doesn't start while another milestone has an implementer on the same branch or working directory.
- P5 waits for any queued or running P3 or P4.

## Exceptions: the router halts and the umbrella decides

| Halt | Typical umbrella move |
|---|---|
| `needs_decision` | Ask the user. If the answer leaves P3 nothing to do, finish it with `event complete` (below). Otherwise `event resume --note <decision> --request P3 --input <decision note>`, adding `--origin p4` or `--origin p5` if the run was a rework, so its push starts the right round |
| `blocked`, `inconclusive` | Get what is missing. If the user supplied it and P3 has no work left (they opened the PR, or the branch already holds the commit), finish it with `event complete`. Otherwise resume with `--request` for the phase to rerun |
| `review_cap`, `p5_rework_cap` | Escalate with each round's findings (`workflows/P4-review.md`, `SKILL.md`, Rework cap). If the user allows another attempt: `--grant review` or `--grant p5_rework`, plus `--request P3 --origin p4\|p5 --input <findings>` |
| `route` (P2 or P1), `major_finding` (D1) | Needs the user, as the workflows describe. After a changed handoff, record it again, then resume |
| `result_rejected` | See What the router checks |
| `target_unpushed` | Raised when the implementation handoff (or `event context`) names a target whose local branch is ahead of `origin/<target>`, before any P3 starts: a branch cut from it would carry those commits into the PR unreviewed. Ask the user whether to push the target, base the branch on `origin/<target>`, or accept the extra commits in this PR. Then `event resume --note <their choice>`; if the base changes, update the handoff's branch or workdir first |
| `run_failed` | The retry failed too. Look at why before resuming |

`resume` clears every halt reason at once, and it refuses while a rejected run is still open.

**Finishing a halted P3 run without an agent.** Starting a sub agent only to write down what the user just did costs a spawn and several umbrella turns. `event complete --run-id <the halted run> --head <sha> --pr-url <url> --note "<what the user did>"` records the run as completed by the umbrella instead. It applies only to a P3 run halted as `blocked` or `needs_decision`. The router runs the same checks as for an agent's result (`origin/<branch>` at that head, no internal codes, new commits for a rework) and refuses on a problem unless `--override` gives the user's reason. Then it routes exactly as a completed P3 result would: the first PR starts review round 1, a rework starts its round. If any code change is still needed, this isn't the tool: resume and let an agent do it.

Without `--run-id`, `event complete` finishes the queued P3 instead, the one a declined delivery authorization holds back: the user pushes the branch and opens the PR, and the umbrella records it with the same checks.

## Limits

- **Not a lock.** The single umbrella is the only caller, and two router processes on one milestone at once are not protected against.
- **Polls are the umbrella's job.** The router doesn't fetch CI or PR threads, so it stays provider-neutral.
- **Approvals stay in `state.json`.** The router trusts that a handoff is recorded only after its controlling approval (`policies/core.md`). It gates on the handoff being recorded and unchanged, not on the approval itself.
- **Bug track with P5 not applicable.** When the diagnosis has no auto scenario because CI runs the regression test, the router posts sign-off once the review passes. The umbrella still confirms CI is passing (`CI:` in `status`, or `none` when the repository has no CI) before asking (`workflows/D1-bug-investigation.md`, Verification).
