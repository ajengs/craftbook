---
name: artifex
description: Use when the user says "Artifex", is starting or resuming an Artifex initiative (umbrella session, milestones, state.json), or is running an Artifex phase (P1-P6, or D1 of the bug track) as a scoped session. A user-led engineering workflow for research, design, scoped implementation, independent review and contract-based verification, with a bug track that reproduces, diagnoses and fixes a bug ticket or a major P5 finding. Not for a single ticket the user hasn't put under Artifex, a plain "implement this spec", a standalone PR review, or a session handoff.
---

# Artifex

**Intent:** Automate mechanics without delegating engineering judgment. Keep work scoped, traceable, proportionate, and verifiable.

This is an **instructional skill**, not a permissions system or autonomous orchestrator. The routine transitions of the P3–P6 loop are decided by a script, `scripts/artifex_flow.py`, which the umbrella runs and obeys (`references/orchestration.md`). The script decides; it spawns nothing and enforces nothing outside its own log. Never imply approvals, file writes, agent launches, test results, or enforcement happened unless they actually did.

## Start here

1. When the user starts Artifex, this session becomes the **umbrella**. Paths with spaces go in double quotes; single quotes only work around a path without spaces. Resolve the workspace and artifact locations from user memory as described below; ask for materially missing values before creating folders, artifacts, or sessions. Write the user's invocation verbatim to a file and run `artifex_state.py --dir <initiative folder> route --request-file <file>`. `route` reads the mode, the ticket, the files, links and free text the invocation names, checks the mode's entry contract and prints the start and the next commands. It writes nothing, and the umbrella obeys it:
   - **A mode** (`project`, `milestone`, `defect` or `implementation`; `bug` means `defect`): run the printed `init --mode <mode> --mode-source explicit --request-file <file>`, then the printed start. A failed contract is printed, not worked around; tell the user what's missing.
   - **`needs_recommendation`**: recommend one mode from the printed table, with reasons, and start nothing until the user approves it. Then run `init --mode <mode> --mode-source recommended --request-file <file>` and the printed start.
   - **A resumed initiative** (`state.json` exists): `route` reports the stored mode; the request's mode is ignored.
2. Resolve the one-time phase/replacement-session creation and coordination authorization, plus delivery authorization as described below, in one message to the user, and record both verbatim in `state.json`. This happens in every mode, before the first session is created or phase worker started.
3. The printed start is one of: P1 (`project`), P2 (`milestone`, or `implementation` without all four artifacts: a short P2), D1 (`defect`), or the router (`implementation` with specs, verification contract, implementation handoff and verification handoff supplied). The umbrella immediately creates a new top-level chat for a session start, subject to the host's session-creation rules below, and does no phase work itself. Never substitute a subagent for P1, P2 or D1. In any other session, identify the initiative, milestone, phase, and whether you are the umbrella or a scoped child.
4. Read the initiative state (`artifex_state.py show`), current controlling artifacts, and **only** the workflow for the active phase; the umbrella also reads `references/orchestration.md` before the first implementation handoff. Follow its linked standards and template(s), not the whole package. Use the execution efficiency and model allocation guidance below for this role.
5. If an approval, source artifact, or status is missing, say so. Do not infer it from conversational enthusiasm or an older artifact.
6. Perform the work and hand back a concise result: **verdict / findings, artifacts changed, decisions or blockers, next action**. Avoid documenting routine mechanics.

## Workspace and artifact preferences

At every invocation, consult available user memory for four distinct values:

- the implementation working directory, identifying whether it is an ordinary checkout or a worktree;
- the user's main work folder for project documents, artifacts and notes;
- the project folder beneath that work folder;
- the convention that selects the initiative artifact folder within the project folder.

Treat remembered values as preferences, validate that the resolved paths still fit the current initiative, and preserve any path or convention the user states in the current request. If a value is absent or ambiguous, ask one concise question for the missing workspace preferences before creating folders, artifacts, or child sessions.

When the user supplies or changes these preferences, use an explicit memory-write capability if the environment exposes one. Otherwise make the current chat eligible for memory generation when that control is available, explain that Codex memory updates asynchronously, and direct the user to enable memories or use `/memories` if needed. Never hand-edit generated memory files. Record the resolved values in `state.json` so the current run does not depend on future memory generation.

## Session creation and coordination authorization

Before the first phase session, use direct authorization already stated by the user or ask **once per initiative**, in the same message as the delivery question:

> Do you authorize the Artifex umbrella to create the phase and replacement sessions needed for this initiative, and authorize the umbrella and those sessions to exchange coordination messages in both directions, limited to artifact paths and revisions, checkpoints, handoffs, results, blockers, findings and approval requests, for the duration of the initiative?

Record the question and reply verbatim with `artifex_state.py consent --status <authorized|declined|manual relay> --session-creation <authorized|declined> --question-file <q> --response-file <r> --source <where> --route <umbrella thread id>`. The same human reply covers creation and messaging; do not ask again before each covered phase, rework or replacement session. The skill's instructions alone are not authorization. Existing coordination-only records lack `session_creation`: obtain the expanded authorization once before automatic Codex creation, rather than interpreting old consent more broadly. A decline selects manual creation/relay: the router registers each P3–P6 run and prints its `manual_session` prompt for the user to launch. The user relays its result path to the umbrella, which submits it normally. Do not repeat the authorization request at every transition. Scope changes and approvals of specs, contracts and milestone closure remain with the user.

P1, P2 and D1 start from the unchanged prompt printed by `artifex_state.py brief`; it quotes the original request and authorization, names the skill/workflow, and gives the initiative state and umbrella route. Register their routes in `state.json`. On Codex, **all phases including P3, P4, P5 and P6 are separate top-level chats**, never native subagents of the umbrella. The router prints `create_session` (or `manual_session` after declined consent) with a complete prompt for each P3–P6 run; pass it unchanged and record the returned thread id with `event started --agent`. Those run routes remain in the router log rather than duplicating routine state in `state.json`.

Every session verifies the human authorization before messaging; the recorded question, answer, date and source travel in its launch prompt. On Codex, authorized sessions report finalized results through `mcp__codex_app__send_message_to_thread`, as P1/P2 report checkpoints; declined coordination uses human relay. The umbrella consumes each result and performs the returned actions in the resumed turn. A send rejection is a blocker: retain the result and use manual relay; do not silently switch to native ancestor messaging or periodic waiting. Host/runtime approval controls still apply and cannot be bypassed by a skill.

## Delivery authorization

Phase workers create the branch, commit, push and open the PR. A user rule such as "prompt before commits, pushes and PRs" would otherwise stop the umbrella at every implementation start, because a handoff is written by P2, not by the user. So ask once, at the start, in the same message as the consent question:

> Do you authorize the implementation and verification phase workers of this initiative to create its branch, commit, push to it and open the pull request? Merging, deploying and backporting stay with you.

Record the reply with `artifex_state.py delivery --status <authorized|declined> --question-file <q> --response-file <r>`. If the user's Artifex invocation already grants it, use `delivery --status authorized --from-request` instead of asking. The router holds every implementation start until a delivery record exists and passes the user's words to each phase worker as `delivery_authorization`, so neither the umbrella nor the agent asks again for what it covers. Ask again only for something outside it, such as a merge, or after the user withdraws it. A decline means the user pushes and opens the PR; the umbrella then records it with `event complete --head <sha> --pr-url <url> --note <n>`, without `--run-id`, which completes the queued implementation.

## Six phases

| Phase | Workflow | Main output | Exit condition |
|---|---|---|---|
| P1 Research & analysis | `workflows/P1-research.md` | Approved kickoff, plus either an approved analysis with direction and milestones or the user's explicit small-task scope confirmation | User approves kickoff and analysis and selects one milestone, or approves kickoff and confirms the scoped task itself as the milestone |
| P2 Development analysis | `workflows/P2-development-analysis.md` | Approved specs, the tradeoffs register and implementation handoff, then approved verification contract and verification handoff | Specs approval produces the implementation handoff and starts P3; P2 remains open to finish verification artifacts and receive later changes |
| P3 Implementation | `workflows/P3-implementation.md` | Changeset, ready PR, CI and PR-thread follow-up | PR open and CI passing; thread polling continues until the PR is completed |
| P4 Review | `workflows/P4-review.md` | Review findings and verdict per round, up to 3 rounds (1 for rework that P5 triggered) | Review passed, or escalation after round 3 |
| P5 Auto verification | `workflows/P5-verification.md` | Results of the contract's auto scenarios. Not applicable when there are none | Results in; sign-off if there is no P6 |
| P6 Manual verification | `workflows/P6-manual-verification.md` | Results of the contract's manual scenarios (functional, benchmark or both). Not applicable when there are none | User explicitly signs off milestone closure |

**Order in P2:** approved specs immediately produce the tradeoffs register (`standards/design.md`), then the implementation handoff and the first checkpoint, which starts P3 automatically. The register keeps the limitations and tradeoffs the user accepted or deferred; it is updated through P6 and is not an approval gate. P2 remains open and then drafts the verification contract; its approval immediately produces the verification handoff. The contract does not gate P3. It lists high-level scenarios that go beyond routine test and CI runs, prefers extended integration tests that run without the app, and marks each scenario **auto** (run in P5 right after P4 passes) or **manual** (run in P6 on the user's trigger). P5 and P6 require a passing review, the approved contract and the verification handoff. Approval is needed again only if the specs or the contract change.

**Bug track.** A bug (a ticket the user starts Artifex on in `defect` mode, or a major P5 finding that needs its own analysis) runs D1 (`workflows/D1-bug-investigation.md`) in place of P1 and P2: reproduce, find the root cause, then fix directly or after the user approves the cause and the fix, depending on the path D1 sets. Its diagnosis replaces the specs, the verification contract and the verification handoff. From the implementation handoff on, P3 to P6 run as above.

## Boundaries

Read `policies/core.md`. In particular:
- The user owns framing, new design decisions, approvals of specs and the verification contract, and final milestone closure. A handoff has no approval of its own: specs approval authorizes the implementation handoff, and contract approval authorizes the verification handoff. Write each immediately after its controlling approval.
- Any **new design decision discovered during P3** must be escalated before affected work continues. P2 is the collaborative design phase, not an escalation ceremony.
- Edge cases are findings, not automatically requirements. Do not grow scope or complexity without a justified, approved reason.
- Internal codes (Artifex ids like SPEC-, VER- and LIM-, phase codes, any code coined in a session) stay in notes. Never put them in code, tests, commits, PRs or ticket comments, in any phase. Describe the behavior in words.
- Approved artifacts are version-specific. A material revision invalidates affected downstream approval(s) until reconciled.
- Starting Artifex authorizes the start `route` prints for the invocation's mode (P1, P2, D1 or the router) and, in `project` mode, the P2 for the milestone selected in P1, and the implementation and review that follow. The umbrella starts P2 after P1 reports either (a) the approved kickoff and analysis revisions plus the selected milestone or (b) the approved kickoff revision plus the user's explicit confirmation that the scoped task is the milestone. More P2 sessions, one per further milestone or for an ad hoc analysis, start when the user asks the umbrella. Whenever a P2 session reports an approved specs revision, a completed implementation handoff and no blocker, the umbrella starts an isolated implementation worker from that handoff itself; the verification contract is not a prerequisite. P4 and the verification run start from the umbrella's checkpoints (see Session triggers). When P4 findings, P5 failures or PR feedback call for a rework, the umbrella starts a new implementation worker once the previous run has finalized its result, up to the caps (3 review rounds, 2 reworks after P5 failures). A later route back to P2 or P1 always needs the user.
- The umbrella creates the D1 session when the user starts Artifex in `defect` mode, or after the user agrees to investigate a major P5 finding. On the direct and reproduced paths, D1's report starts the implementation worker with no approval step, and the umbrella tells the user in one line; on the confirm path it waits for the user's approvals of the root cause and of the fix approach. The user can move a bug between paths at any time.

## Coordination and working state

One **umbrella session per initiative** coordinates milestones, scoped child sessions and isolated phase workers, dependencies, approvals, and artifact versions. Several P2 sessions can be active at once, one per milestone or ad hoc analysis. Each sends its handoffs to the umbrella, which starts the implementation and verification phase workers for them and tracks each with the router. The user confirms the branch and the working directory for each implementation handoff, by default the current checkout and a worktree only on request. This happens in P2, or later with the umbrella when the handoff left them `TBD`; the umbrella then records them with the router (`event context`) without going back to P2. The handoff names its dependencies. When a handoff arrives while another implementation worker is active, the umbrella checks whether the two can run in parallel: different branch and working directory, and no dependency on each other's changes. If they can, it starts the new one at once. If not, the router holds it and says why. Artifacts, not session memory, carry context across sessions. Store them in the resolved initiative artifact folder under the user's project work folder, separate from the implementation working directory unless the user explicitly makes them the same.

```text
<main work folder>/<project folder>/<initiative artifact folder>/
  state.json                       # Umbrella-owned initiative state (scripts/artifex_state.py)
  STATE.md                         # Only when the user asks: rendered from state.json, never edited
  kickoff.md
  analysis.md
  milestones/<id>/
    run.jsonl                      # Router-owned event log for P3–P6
    results/                       # One result file per agent run, nothing else
    evidence/<run id>/             # Raw P5/P6 output
    specs.md
    tradeoffs.md                   # Living register of accepted and deferred tradeoffs and limitations: P2 creates it, later decisions add to it
    diagnosis.md                   # Bug track: replaces specs, contract and verification handoff
    implementation-handoff.md
    verification-contract.md
    verification-handoff.md
    review.md                      # Optional; may be a concise handoff report
    verification-report.md
```

The umbrella's state is `state.json`, written only through `scripts/artifex_state.py` (`references/state.md`). It's for agents, so it is structured and holds the latest state only; a `STATE.md` is rendered from it only when the user asks to see it. The **umbrella is the single writer** of `state.json` and approval records, and the **router is the single writer** of each milestone's `run.jsonl`; child sessions and phase workers write only their assigned deliverables and result files and return status for reconciliation. If the environment cannot coordinate sessions, produce a handoff and ask the user to launch the child; don't pretend it started. Keep parallel code changes isolated when possible (e.g. separate Git worktrees). This is a convention, **not atomic-write protection**.

**Umbrella bookkeeping.** Reconcile concise phase results: decisions, artifact paths and revisions, status, blockers, and next action. Use the recorded state and approved artifacts rather than reconstructing phase conversations or repeating phase-level analysis or implementation. Read changed artifacts and affected dependencies when a checkpoint requires them; reuse known unchanged revisions within the current session. Compute approval hashes when recording approved bytes, and recheck integrity at consumption or when a file may have changed, rather than rehashing on every status update. Consolidate related updates into one coherent write before dispatching dependent work; record approvals and routing changes before consumers use them. Review rounds, rework counts, heads, pushes, poll results and active runs live in the router's log and nowhere else: routine router transitions write nothing to `state.json`. Write `state.json` for what the umbrella decides or posts: approvals, decisions, sessions, blockers, phase changes. Prefer the router and existing deterministic file/hash operations to ad hoc bookkeeping scripts. Retain enough state for a fresh session to recover; the single-writer convention remains the available mechanism, without atomic-write protection.

**Session names:** name every new Artifex session or phase worker `<ticket id> <phase code> <phase name> <additional context if any>`, separated by single spaces and without brackets, for example `PROJ-123 P3 implementation` or `PROJ-123 P2 analysis M1 specs`. Phase names: P1 research, P2 analysis, P3 implementation, P4 review, P5 auto verification, P6 manual verification, D1 bug investigation. Use the ticket id the user gives, exactly as given, even if the kickoff says otherwise. Only if the user gave none, take it from the kickoff, or the initiative name if the initiative has none, and say which you used. Set the name where the environment allows it, otherwise suggest it to the user.

**Starting a child session:** start one only when the user asks or a Session triggers checkpoint explicitly makes it automatic. Use only the scope authorized by that request or checkpoint. Apply Model allocation at creation, including the desktop phase-chat binding below. For P1, P2 and D1, also apply the `session_setup` from `doc surface` when it has one (Documents).
- **Codex desktop:** every phase (P1–P6 and D1), rework and replacement is an independent top-level chat. Create it with `mcp__codex_app__create_thread` under the initiative's one-time session-creation and coordination authorization; never use `spawn_agent` or a native subagent tool for a phase. Reuse that recorded human request at every covered creation. If it is missing, ask the combined question in Session creation and coordination authorization once. If declined, give the user the generated brief or `manual_session` prompt to launch and relay manually. If host creation is unavailable or rejected, report the blocker and retain the handoff; do not substitute a native subagent or record one as a phase chat.
- Run code-oriented sessions against the resolved implementation working directory. Point every session at the resolved initiative artifact folder for Artifex documents and shared state.
- Ask the new session to run `artifex_state.py host` first and report its `session_id` through the authorized channel or manual relay. Record P1/P2/D1 routes in the `sessions` table and P3–P6 routes with router `event started --agent`. In Codex, the returned thread id is the session/transcript id; do not duplicate router-owned runs in `state.json`.
- For P1, P2 and D1, the coordination envelope is the `brief` output (Session creation and coordination authorization). For Codex P3–P6, use the complete router-generated `create_session` or `manual_session` prompt unchanged; it includes the state path, assigned inputs, result/evidence paths and recorded consent. Automatic launches also carry the current umbrella report route. For other-host workers, attach that state/route metadata to the router's native spawn inputs. Transport metadata does not extend the handoff's work scope.
- If they provide a handoff document, that document carries the child's instructions. Point the child at it (path and revision) and don't restate, extend or reinterpret it.
- If there is no document, pass context from the user's prompt only.
- Values the user states (ticket id, session name, branch, scope) are used exactly as given. Defaults from the kickoff or `state.json` apply only to what the user left unsaid, and are never swapped in for a value the user stated.
- Some hosts start a session only on the user's own words. Claude Code refuses `start_session` on a turn that another session's message started, which is exactly how P1's checkpoint arrives. When a checkpoint that should start P2 or D1 arrives that way, don't attempt the start: propose the session (a card the user starts with one click) and post one line saying it waits for that click. Start it directly only on a turn the user began.
- If you must write a brief yourself because no document exists, state what the prompt gives you: milestone, role, scope, controlling artifact **paths + revisions**, deliverable, exclusions and escalation route, as far as known. Do not rely on undocumented context from another chat. Prefer existing project coding/testing conventions over invented Artifex ones.

## Session triggers, checkpoints and isolation

On Codex every phase below is an independent chat, including reworks and replacements; other hosts keep their scoped-worker transport. Declined creation or coordination uses the generated manual handoff and human result relay.

| Phase | How it runs |
|---|---|
| P1 | A new session, created by the umbrella when `route` prints P1 as the start (`project` mode, or a mode the user approved after a recommendation) |
| P2 | A new session, created and started by the umbrella when `route` prints P2 as the start (`milestone` mode, or `implementation` mode without all four artifacts, a short P2), or after P1 reports either the approved kickoff and analysis revisions plus the selected milestone, or the approved kickoff revision plus the user's explicit confirmation that the scoped task is the milestone. Further P2 sessions (another milestone, an ad hoc analysis) start on the user's request to the umbrella |
| D1 | A new session, created by the umbrella in place of P1 and P2 when `route` prints D1 as the start (`defect` mode), or after the user agrees to investigate a major P5 finding. On the confirm path, D1 can propose a P2 design session; once the user approves it, the umbrella starts P2 with the diagnosis as the milestone's scope link. On the direct and reproduced paths its report starts the implementation worker; on the confirm path the implementation starts after the user approves the root cause and then the fix approach |
| P3 | An isolated implementation worker of the umbrella, started automatically after any P2 session reports the approved specs revision, completed implementation handoff, and no blocker. It reports its checkpoints, findings, blockers, and results straight to the umbrella. A rework starts a new phase worker once the previous run has finalized its result. The verification contract is not required to start P3. |
| P4 | An isolated phase worker of the umbrella, started automatically when P3 reports the PR is open, and again for each later round (see Which pushes start a review round). The umbrella does not wait for CI |
| P5 auto verification | An isolated phase worker of the umbrella, started automatically once P4 has passed and the verification handoff is ready with no blocker or dependency, whichever comes last. Not applicable when the contract has no auto scenario |
| P6 manual verification | An isolated phase worker of the umbrella, started only on the user's explicit trigger (the user asks the umbrella). Not applicable when the contract has no manual scenario. A benchmark in either part runs through the benchmark designer (see Optional tools), whose session adds the harness it needs |

**Routing P3–P6.** From the implementation handoff on, the umbrella doesn't decide routine transitions itself. It records the handoff with the router, carries out the actions the router prints, and passes every agent result to it (`references/orchestration.md`). The router applies the rules below (automatic starts, which pushes start a review round, the caps, retries) and checks each result against its artifacts and the remote. Anything that needs judgment comes back as a halt for the umbrella and the user: a design decision, a blocker, an inconclusive result, a cap reached, a route to P2, P1 or D1, or a result that fails a check. The rules below remain the specification the router implements. Where the router is unavailable, say so and apply them by hand.

**Completion handling.** Codex uses event-driven cross-session messages, not native waiting. After dispatching authorized sessions and doing independent coordination, end the umbrella turn; the session's completion message starts a later turn. Reconcile on each checkpoint, completion, user message or resume, submit finalized results, surface verdicts/reports and execute returned actions. Do not keep the turn alive with native waits, sleeps, heartbeat messages or repeated status checks. On resume, use recorded run ids and routes to recover lost messages without starting duplicate sessions. Other hosts retain their native completion mechanism (`references/orchestration.md`).

**Checkpoints.** A phase notifies the umbrella, through whatever channel the environment gives and within the recorded coordination consent, when it: creates or modifies a handoff (P2, D1); reports a diagnosis, its path and what the user must approve (D1); opens the PR, and pushes new commits after it is open (P3); finishes a review round (P4); has verification or benchmark results (P5, P6). P3–P6 workers write a finalized result file and, on Codex, message its path to the umbrella; the umbrella passes the path to the router rather than reading the report. Findings and change requests travel through the umbrella, not directly between phase sessions or their phase workers. When the implementation worker needs the user's input, for example on a PR thread, it reports to the umbrella, which asks the user.

**Which pushes start a review round.** A push is new commits from P3.
- Before P4 has passed, only a push that answers the findings the umbrella relayed starts the next round. CI fixes and PR-thread fixes pushed in the meantime are recorded by the router and go into that round's changes.
- After P4 has passed, a push of new P3 commits that changes code or tests (PR-thread feedback, a CI fix, a P5 rework) starts one more incremental round. A push that changes only documentation, comments or formatting starts none; the router records it. The round doesn't count toward the 3, and if it doesn't end in `pass` the umbrella escalates as in `workflows/P4-review.md`. If a code or test change landed after P5 had started or passed, P5 reruns on the new head before sign-off.
- A rebase, or a merge of the target branch, starts no round and no P5 rerun. If it needed conflict resolution, the resolution is new code and counts as a push.
- The router records the last reviewed head and every other push beside it, and classifies each push from git; `status` shows them.

**Rework cap.** The router counts the P3 reworks that P5 failures trigger. After 2, a further P5 `fail` that points to P3 stops and goes to the user with each cycle's findings and options; no third rework starts on its own. A fail routed to P2 or P1 doesn't count, because those always need the user. A fix from a D1 that a P5 finding started counts when it lands on the milestone's PR. P4 keeps its own cap of 3 rounds.

**Reporting to the user.** The umbrella receives every checkpoint but posts only the major ones: approvals (needed or recorded), phase exits, blockers, decisions the user needs to make, PRs, and review or verification results. Routine checkpoints, such as a handoff touched, a push, a round starting, or a poll that found nothing, are not posted and aren't written anywhere by the umbrella: the router already logged them.

**At sign-off,** when the umbrella asks the user to close a milestone, it adds the `accepted` and `deferred` rows of `tradeoffs.md` (title, severity, boundary) and names any `deferred` row whose References has no follow-up. The user then signs off knowing what was accepted. A one-line "none registered" is enough when the register is empty.

**Polling belongs to the umbrella.** An implementation worker doesn't outlive its work. For each open PR the umbrella schedules CI polls until CI passes, or confirms once that the repository has no CI and records `event poll --kind ci --outcome none`, then PR-thread polls every 3 hours until the PR is completed, with whatever scheduling the environment offers (say so if it offers none). Poll schedules end when the umbrella session or app closes, so `state.json` records each open PR and its poll schedule (`polls` table). A resumed or replacement umbrella records its own session id with the router on every open milestone (`event umbrella`) and re-arms the polls for every open PR before anything else; its first poll covers the gap. The umbrella records every poll result with the router (`event poll`), which queues a new implementation worker for a CI failure or for thread updates it hasn't dispatched, once the previous run has finalized its result. A poll that finds nothing isn't posted. That phase worker verifies, fixes, pushes and replies per `standards/pr-feedback.md`. The umbrella does not fix or reply itself.

**Isolation.** A session works from its own inputs and does not track other sessions' context or progress unprompted. A P2 session doesn't follow P5's results. If P5 finds that P2's artifacts must change, it notifies the umbrella, and the umbrella sends P2 the request. P2 processes that request only and does not monitor P5 afterwards.

## Model allocation

The native files linked below are the authoritative default model and effort settings. Handoffs reference the relevant file and record only the resolved selection and any override for their run.

| Role | Native configuration |
|---|---|
| Umbrella | [Umbrella profile](profiles/artifex-umbrella.config.toml) |
| P1 research | [Planning profile](profiles/artifex-planning.config.toml) |
| P2 analysis | [Planning profile](profiles/artifex-planning.config.toml) |
| D1 bug investigation | [Planning profile](profiles/artifex-planning.config.toml) |
| P3 implementation workers | [`artifex_worker`](agents/artifex-worker.toml) |
| P4 independent review | [`artifex_reviewer`](agents/artifex-reviewer.toml) |
| P5 auto verification | [`artifex_verifier`](agents/artifex-verifier.toml) |

Use the user's override first. For P6, preserve the user's or handoff's selection; this policy assigns no new default. Complexity or evidence of model failure can justify higher effort or a stronger available model; record the reason and selection in the handoff or checkpoint. For an optional full PR review in P5, apply the P4 allocation to the reviewer while retaining the P5 allocation for scenario execution.

For optional native helper agents, not Codex phase sessions, prefer existing custom-agent configuration (`model` and `model_reasoning_effort`) when selecting a suitable agent type. Otherwise pass explicit model and effort through supported native spawn/session-creation options. Custom-agent settings can override spawn values: check that the selected role matches the intended allocation. Where the spawn API requires a fresh context to set these options, supply the controlling handoff and coordination envelope rather than full conversation history. Select a restricted tool surface when supported and adequate for the work.

**Separate top-level sessions on Codex:** the umbrella and every phase (P1–P6 and D1), including each rework or replacement, are independent chats. Use `mcp__codex_app__create_thread` under the initiative's recorded creation authorization. P1/P2/D1 use the planning profile; P3, P4 and P5 use their worker/reviewer/verifier role files as model/effort guidance; P6 preserves the user's or handoff's selection. An agent TOML file does not configure a new chat automatically. Apply model/effort selections through supported creation arguments only where the host permits them and the user has authorized the selection; otherwise preserve the host's configured default and record the limitation. Do not introduce another creation-approval prompt for an already covered session. Keep the confirmed project/workspace and handoff; a different checkout or worktree still needs the user's instruction.

P1/P2/D1 use `artifex_state.py brief` unchanged; P3–P6 use the router's `prompt` unchanged, together with its session name and result path. Check returned routes/settings rather than claiming that a profile or prompt selected the model. Register planning-session settings in `state.json`; record P3–P6 thread ids through `event started --agent` so cost reporting still finds them. On resume/replacement, update the umbrella route and notify active sessions within the standing coordination authorization. Never recreate a session merely because its creation response or completion message was delayed; reconcile its existing thread first.

**Claude Code.** The model ids in the Codex files don't exist there. `profiles/claude-code.toml` maps each role to a Claude model and effort: the planning tier and the reviewer go to Opus, the umbrella, worker and verifier to Sonnet, efforts unchanged. Pass its `alias` as `model` and its `effort` as `effort` on the Agent tool, and its `alias` as `model` on `start_session`, which has no effort control: request the effort in the brief and record it as unconfirmed. Claude Code starts sessions only on the caller's model tier or a cheaper one, so an umbrella running on Sonnet can't start an Opus P1, P2 or D1. When that refusal comes, record the model the session actually got and tell the user once; starting the umbrella itself on Opus avoids it. Update the mapping file, not the handoffs, when model names change.

**Configuration activation:** keep the bundled agent and profile files as the source of truth. Expose `agents/artifex-*.toml` through symlinks in `$CODEX_HOME/agents/` (normally `~/.codex/agents/`), or the implementation project's `.codex/agents/`. Expose `profiles/artifex-*.config.toml` through symlinks directly under `$CODEX_HOME/`. These links are installation steps, not something skill invocation performs. Check for existing entries before installing; preserve unrelated configuration. An agent file stored only inside this skill is not automatically active.

For optional native helpers or other-host phase workers, select the named agent when the spawn capability exposes agent types. If it exposes only model/effort options, read those settings from the relevant native file and pass them explicitly; instructions alone do not select a configured role. User overrides may require a different role or explicit spawn options because custom-agent file settings take precedence. Reload agent discovery or start a fresh Codex session after installation as needed, and verify runtime role/settings when evidence is available. Report installed files separately from successful runtime selection; do not claim that an existing chat switched models.

For an already-running umbrella or a top-level session without native selection controls, these settings are recommendations: state the requested selection and any mismatch; instructions cannot change the running model. If a model or control is unavailable, report the limitation and use a user-approved or available fallback without claiming enforcement. Do not create a launcher or model-switching layer. Model identifiers are supported by the current runtime; recheck availability only when the target environment differs or rejects one. Native configuration behavior is described in [Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Execution efficiency

- **Context:** load phase-relevant instructions and controlling approved artifacts, using the handoff instead of reconstructing prior conversations. Read an unchanged file again only for a concrete reason, such as a new question, suspected mutation or recovery after lost context. Reference artifact paths and revisions instead of copying their contents.
- **Tool output:** use targeted excerpts, search results, quiet build output and filtered checks. Save full build/test logs and diagnostic evidence to files when needed, then inspect relevant failures and summaries. Read a diff's stat before its relevant hunks; keep generated files out of conversational output. Preserve and inspect all evidence needed to diagnose a failure or verify a result; output reduction must not hide missing coverage or weaken checks.
- **Umbrella compaction at phase boundaries:** the umbrella re-reads its whole context on every turn, so context it no longer needs costs on every later turn. Once a phase's outcome is on disk, the conversation that produced it is dead weight. Compact at these points: after the implementation handoff is recorded with the router (P1 and P2 coordination is then in artifacts, `state.json` and `run.jsonl`), and after a milestone closes when others remain open. The router posts a `compact_umbrella` checkpoint at the first of these. If the host lets the umbrella compact itself, do it; otherwise end the checkpoint with one line suggesting the user compact now. Don't compact mid-loop on a turn count: the router makes recovery cheap at any point, but a boundary is where the most context is safely disposable.
- **Lifecycle:** when accumulated context obscures the active task or carries substantial obsolete discussion, evaluate native compaction or a fresh-session handoff. Preserve approved decisions and revisions, acceptance criteria, work in progress, evidence paths, blockers, ownership and coordination routes. Transition only when useful; avoid automatic thresholds or routine restarts. Recover from artifacts and update session routes through the umbrella when a replacement is necessary.

## Documents

Documents the user reads or approves are **human-targeted**: kickoff, analysis, specs, verification contract, verification report, and the diagnosis when it needs approval. The user reviews each by commenting on specific passages before approving a revision. Where that happens depends on the host, and the script decides it, not the agent:

- **Before drafting**, run `python <skill>/scripts/artifex_state.py --dir <initiative folder> doc surface <doc> [--milestone <id>]` and do what it prints. It detects the host (`CLAUDECODE=1` for Claude Code, a `CODEX_*` variable for Codex, `ARTIFEX_HOST` or `--host` to override) and returns the surface, the markdown path and the steps. Codex desktop gets the local file in its annotating viewer and no Pages document; Claude Code gets a Claude Docs document, because its file pane can't take comments; an unknown host gets the capability rule.
- **Session setup.** When the surface is `local-file`, the output carries `session_setup.workspace_folder`. The umbrella runs `doc surface kickoff` before creating P1 (and the matching document before P2 or D1) and creates the session with that folder in its workspace, as a workspace root or added directory. A session started without it can't open the file in its viewer; recreate it rather than falling back to chat.
- **Approval.** The umbrella records every approval with `doc approve <doc> --surface <surface> [--url <link>] [--revision <id>] [--file <md>]`. It hashes the approved markdown and refuses a surface the host doesn't bind unless `--fallback "<what failed>"` says why. `upsert artifacts` refuses `decision=approved`, so there is no other way to record one.
- **Review rounds.** Apply each comment to its passage and keep the rest as it is. Keep every round in the same document or file. Ask for explicit approval of the current revision.
- **What goes in chat.** The document is what the user reviews, so the chat message doesn't repeat it. Put every question the user must answer into the document's blocking questions or open decisions, with options and a recommendation. Then the message is one line with the link and revision, plus a single numbered **Waiting on you** list: one line per decision or approval, with your recommendation. No current or target state, specs or scenarios, preserved behaviors, edge cases or section summaries in chat. Say each thing once; a later message lists only what is still open. The only exception is the `chat` fallback, which pastes the document once. `doc surface` prints these rules as `review_message`.
- **If the surface fails**, say what failed, take passage comments in chat on the markdown file, and approve with `--surface chat --fallback "<what failed>"`.

Agent-facing documents (`review.md`, handoffs, `tradeoffs.md`, execution summaries, runbooks) are written directly as markdown. The user decides the register's rows through the specs review and later change requests, and reads it at sign-off; agent state is `state.json` and `run.jsonl`, never markdown. The user can override the default for any document.

**Status tracker.** Create a remote status page, a document artifact, **only when the user asks for one**. Follow `references/status-page.md`.

## Optional tools

Workflows name tools by capability. Bind each one here:

| Capability | Used by | Default | Fallback |
|---|---|---|---|
| Benchmark designer: drafts a benchmark contract and runbook, and runs an approved one | P2 contract, P5, P6 | `benchmark-scenario` | `benchmark-designer`, when `benchmark-scenario` isn't installed. If neither exists, write the benchmark part of the contract by hand and say so |
| Handoff writer: turns a session's context into a document another session can execute | P2 | `handoff` | Write the document yourself: what the future session is for, decisions made, constraints, references to artifacts instead of copies, suggested skills. Redact secrets and personal data |
| PR reviewer: reviews a PR and returns findings, action classes and a verdict | P4 | `pr-review-pipeline` | Review by hand as P4 describes: coverage against the approved spec IDs, correctness, unjustified complexity and scope expansion, reported as concrete findings with evidence and a verdict |
| PR feedback handler | P3 | See `standards/pr-feedback.md` | Follow that standard directly |
| Evidence collector: gathers metrics, traces, logs, debug recordings and profiler captures for the bug | D1 | The environment's observability and debugging tools, scoped to the reported instance and time window | Ask the user for the artifacts and say which were unavailable |
| Debug loop: builds the reproduction and finds the cause | D1 | `diagnosing-bugs`, phases 1 to 4 | Follow steps 2 and 3 of `workflows/D1-bug-investigation.md` directly |

## Reading map

- `policies/core.md`: authority, scope, approval/version and evidence constraints.
- `standards/design.md`: current/target models, meaningful edge cases, design decisions, and the tradeoffs and limitations register.
- `standards/specifications.md`: Given/When/Then, handoff and contract quality.
- `standards/evidence.md`: verification rigor, reporting and limitations.
- `standards/pr-feedback.md`: verifying, answering and escalating PR feedback; the PR feedback handler is an optional tool.
- `workflows/`: procedures, entry/exit and routing.
- `templates/`: minimal artifact starting points; omit irrelevant optional sections.
- `references/status-page.md`: the optional remote status page, only when the user asks.
- `references/state.md`: `state.json`, the umbrella's structured state, its commands and when to write it; rendering `STATE.md` on request.
- `references/orchestration.md`: the P3–P6 router, its commands, the result file, handoff frontmatter, transitions and halts. Read by the umbrella; phase workers need only its Result file section.

**Deferred:** detailed code-review policy; delivery (merging, deployment, backports); routing tiers; mandatory claim-by-claim evidence tags; automated approval gates and locking; a headless driver that launches agents itself, and routing for P1, P2 and D1. Do not operationalize deferred items without user agreement.
