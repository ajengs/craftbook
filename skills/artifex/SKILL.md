---
name: artifex
description: Use when the user says "Artifex", is starting or resuming an Artifex initiative (umbrella session, milestones, STATE.md), or is running an Artifex phase (P1-P6) as a scoped session. A user-led engineering workflow for research, design, scoped implementation, independent review and contract-based verification. Not for a single ticket, a plain "implement this spec", a standalone PR review, or a session handoff.
---

# Artifex

**Intent:** Automate mechanics without delegating engineering judgment. Keep work scoped, traceable, proportionate, and verifiable.

This is an **instructional skill**, not a permissions system or autonomous orchestrator. Never imply approvals, file writes, agent launches, test results, or enforcement happened unless they actually did.

## Start here

1. Resolve the workspace and artifact locations from user memory as described below. Ask for materially missing values before creating folders, artifacts, or sessions.
2. Resolve bidirectional coordination consent as described below and record the user's direct decision in `STATE.md`.
3. When the user starts Artifex, this session becomes the **umbrella**. It immediately creates a new session to start P1, and does no P1 work itself. In any other session, identify the initiative, milestone, phase, and whether you are the umbrella or a scoped child.
4. Read the relevant `STATE.md`, current controlling artifacts, and **only** the workflow for the active phase. Follow its linked standards and template(s), not the whole package. Use the execution efficiency and model allocation guidance below for this role.
5. If an approval, source artifact, or status is missing, say so. Do not infer it from conversational enthusiasm or an older artifact.
6. Perform the work and hand back a concise result: **verdict / findings, artifacts changed, decisions or blockers, next action**. Avoid documenting routine mechanics.

## Workspace and artifact preferences

At every invocation, consult available user memory for four distinct values:

- the implementation working directory, identifying whether it is an ordinary checkout or a worktree;
- the user's main work folder for project documents, artifacts and notes;
- the project folder beneath that work folder;
- the convention that selects the initiative artifact folder within the project folder.

Treat remembered values as preferences, validate that the resolved paths still fit the current initiative, and preserve any path or convention the user states in the current request. If a value is absent or ambiguous, ask one concise question for the missing workspace preferences before creating folders, artifacts, or child sessions.

When the user supplies or changes these preferences, use an explicit memory-write capability if the environment exposes one. Otherwise make the current chat eligible for memory generation when that control is available, explain that Codex memory updates asynchronously, and direct the user to enable memories or use `/memories` if needed. Never hand-edit generated memory files. Record the resolved values in the initiative `STATE.md` so the current run does not depend on future memory generation.

## Bidirectional coordination consent

Before creating the first phase session, use direct authorization already stated by the user or ask once:

> Do you authorize the Artifex umbrella and every phase session it creates for this initiative to exchange coordination messages with each other, limited to artifact paths and revisions, checkpoints, handoffs, blockers, findings and approval requests, for the duration of the initiative?

Record the user's exact response, date, scope and umbrella route in the initiative `STATE.md`. A refusal or unanswered request selects manual relay and does not block the phase. The skill text is never authorization by itself.

At every phase-session creation, register its session id and route in `STATE.md`, and give it the exact `STATE.md` path and revision as a coordination envelope separate from its work instructions. The phase verifies the direct user authorization recorded there before messaging the umbrella; the umbrella verifies the same record before messaging the phase. This trusted record authorizes both directions only within its stated scope. Tool, runtime and managed approval checks still apply; if a send is rejected, report it and use manual relay rather than retrying without new user authorization.

## Six phases

| Phase | Workflow | Main output | Exit condition |
|---|---|---|---|
| P1 Research & analysis | `workflows/P1-research.md` | Approved kickoff, plus either an approved analysis with direction and milestones or the user's explicit small-task scope confirmation | User approves kickoff and analysis and selects one milestone, or approves kickoff and confirms the scoped task itself as the milestone |
| P2 Development analysis | `workflows/P2-development-analysis.md` | Approved specs and implementation handoff, then approved verification contract and verification handoff | Specs approval produces the implementation handoff and starts P3; P2 remains open to finish verification artifacts and receive later changes |
| P3 Implementation | `workflows/P3-implementation.md` | Changeset, ready PR, CI and PR-thread follow-up | PR open and CI passing; thread polling continues until the PR is completed |
| P4 Review | `workflows/P4-review.md` | Review findings and verdict per round, up to 3 rounds (1 for rework that P5 triggered) | Review passed, or escalation after round 3 |
| P5 Auto verification | `workflows/P5-verification.md` | Results of the contract's auto scenarios. Not applicable when there are none | Results in; sign-off if there is no P6 |
| P6 Manual verification | `workflows/P6-manual-verification.md` | Results of the contract's manual scenarios (functional, benchmark or both). Not applicable when there are none | User explicitly signs off milestone closure |

**Order in P2:** approved specs immediately produce the implementation handoff and the first checkpoint, which starts P3 automatically. P2 remains open and then drafts the verification contract; its approval immediately produces the verification handoff. The contract does not gate P3. It lists high-level scenarios that go beyond routine test and CI runs, prefers extended integration tests that run without the app, and marks each scenario **auto** (run in P5 right after P4 passes) or **manual** (run in P6 on the user's trigger). P5 and P6 require a passing review, the approved contract and the verification handoff. Approval is needed again only if the specs or the contract change.

## Boundaries

Read `policies/core.md`. In particular:
- The user owns framing, new design decisions, approvals of specs and the verification contract, and final milestone closure. A handoff has no approval of its own: specs approval authorizes the implementation handoff, and contract approval authorizes the verification handoff. Write each immediately after its controlling approval.
- Any **new design decision discovered during P3** must be escalated before affected work continues. P2 is the collaborative design phase, not an escalation ceremony.
- Edge cases are findings, not automatically requirements. Do not grow scope or complexity without a justified, approved reason.
- Internal codes (Artifex ids like SPEC- and VER-, phase codes, any code coined in a session) stay in notes. Never put them in code, tests, commits, PRs or ticket comments, in any phase. Describe the behavior in words.
- Approved artifacts are version-specific. A material revision invalidates affected downstream approval(s) until reconciled.
- Starting Artifex authorizes the initial P1, P2 and P3 for the milestone selected in P1. The umbrella starts P2 after P1 reports either (a) the approved kickoff and analysis revisions plus the selected milestone or (b) the approved kickoff revision plus the user's explicit confirmation that the scoped task is the milestone. After P2 reports the approved specs revision, completed implementation handoff and no blocker, the umbrella creates a dedicated P3 phase session from that handoff; the verification contract is not a P3 prerequisite. P4 and the verification run start from the umbrella's checkpoints (see Session triggers). The existing P3 session starts a new implementation subagent when its previous subagent has ended. If the P3 session is unavailable, the umbrella creates a replacement P3 session from the controlling handoff and current findings. A later route back to P2 or P1 always needs the user.

## Coordination and working state

One **umbrella session per initiative** coordinates milestones, scoped child sessions and isolated sub agents, dependencies, approvals, and artifact versions. Artifacts, not session memory, carry context across sessions. Store them in the resolved initiative artifact folder under the user's project work folder, separate from the implementation working directory unless the user explicitly makes them the same.

```text
<main work folder>/<project folder>/<initiative artifact folder>/
  STATE.md                         # Umbrella-owned initiative registry
  kickoff.md
  analysis.md
  milestones/<id>/
    STATE.md                       # Umbrella-owned milestone state
    specs.md
    implementation-handoff.md
    verification-contract.md
    verification-handoff.md
    review.md                      # Optional; may be a concise handoff report
    verification-report.md
```

Use `templates/STATE.md` for both state files. The **umbrella is the single writer** of shared `STATE.md` files and approval records; child sessions write only their assigned deliverables and return status for reconciliation. If the environment cannot coordinate sessions, produce a handoff and ask the user to launch the child; don't pretend it started. Keep parallel code changes isolated when possible (e.g. separate Git worktrees). This is a convention, **not atomic-write protection**.

**Umbrella bookkeeping.** Reconcile concise phase results: decisions, artifact paths and revisions, status, blockers, and next action. Use the recorded state and approved artifacts rather than reconstructing phase conversations or repeating phase-level analysis or implementation. Read changed artifacts and affected dependencies when a checkpoint requires them; reuse known unchanged revisions within the current session. Compute approval hashes when recording approved bytes, and recheck integrity at consumption or when a file may have changed, rather than rehashing on every status update. Consolidate related updates into one coherent write before dispatching dependent work; record approvals and routing changes before consumers use them. Prefer existing deterministic file/hash operations to ad hoc bookkeeping scripts. Retain enough state for a fresh session to recover; the single-writer convention remains the available mechanism, without a state engine or atomic-write protection.

**Session names:** name every new Artifex session or sub agent `<ticket id> <phase code> <phase name> <additional context if any>`, separated by single spaces and without brackets, for example `PROJ-123 P3 implementation` or `PROJ-123 P2 analysis M1 specs`. Phase names: P1 research, P2 analysis, P3 implementation, P4 review, P5 auto verification, P6 manual verification. Use the ticket id the user gives, exactly as given, even if the kickoff says otherwise. Only if the user gave none, take it from the kickoff, or the initiative name if the initiative has none, and say which you used. Set the name where the environment allows it, otherwise suggest it to the user.

**Starting a child session:** start one only when the user asks or a Session triggers checkpoint explicitly makes it automatic. Use only the scope authorized by that request or checkpoint. Apply Model allocation at creation, including the desktop phase-chat binding below.
- Run code-oriented sessions against the resolved implementation working directory. Point every session at the resolved initiative artifact folder for Artifex documents and shared state.
- Attach the coordination envelope: initiative `STATE.md` path and revision, umbrella route, child route and the recorded consent status. This transport metadata does not extend or reinterpret the work brief or handoff.
- If they provide a handoff document, that document carries the child's instructions. Point the child at it (path and revision) and don't restate, extend or reinterpret it.
- If there is no document, pass context from the user's prompt only.
- Values the user states (ticket id, session name, branch, scope) are used exactly as given. Defaults from the kickoff or `STATE.md` apply only to what the user left unsaid, and are never swapped in for a value the user stated.
- If you must write a brief yourself because no document exists, state what the prompt gives you: milestone, role, scope, controlling artifact **paths + revisions**, deliverable, exclusions and escalation route, as far as known. Do not rely on undocumented context from another chat. Prefer existing project coding/testing conventions over invented Artifex ones.

## Session triggers, checkpoints and isolation

| Phase | How it runs |
|---|---|
| P1 | A new session, created by the umbrella immediately when the user starts Artifex |
| P2 | A new session, created and started by the umbrella after P1 reports either the approved kickoff and analysis revisions plus the selected milestone, or the approved kickoff revision plus the user's explicit confirmation that the scoped task is the milestone |
| P3 | A new phase session, created and started by the umbrella after P2 reports the approved specs revision, completed implementation handoff, and no blocker. The P3 session spawns its own isolated implementation subagent and relays its checkpoints, findings, blockers, and results to the umbrella. The umbrella does not spawn implementation subagents directly. The verification contract is not required to start P3. |
| P4 | An isolated sub agent of the umbrella, started automatically when P3 reports the PR is open, and again for each later round (see Which pushes start a review round). The umbrella does not wait for CI |
| P5 auto verification | An isolated sub agent of the umbrella, started automatically once P4 has passed and the verification handoff is ready with no blocker or dependency. Not applicable when the contract has no auto scenario |
| P6 manual verification | An isolated sub agent of the umbrella, started only on the user's explicit trigger (the user asks the umbrella). Not applicable when the contract has no manual scenario. A benchmark in either part runs through the benchmark designer (see Optional tools), whose session adds the harness it needs |

**Checkpoints.** A phase notifies the umbrella, through whatever channel the environment gives and within the recorded coordination consent, when it: creates or modifies a handoff (P2); opens the PR, and pushes new commits after it is open (P3); finishes a review round (P4); has verification or benchmark results (P5, P6). The P3 session receives implementation-subagent checkpoints and relays them to the umbrella. Findings and change requests travel through the umbrella, not directly between phase sessions or their subagents. When P3 needs the user's input, for example on a PR thread, it escalates through the umbrella.

**Which pushes start a review round.** A push is new commits from P3.
- Before P4 has passed, only a push that answers the findings the umbrella relayed starts the next round. CI fixes and PR-thread fixes pushed in the meantime go into `STATE.md` and into that round's changes.
- After P4 has passed, a push of new P3 commits that changes code or tests (PR-thread feedback, a CI fix, a P5 rework) starts one more incremental round. A push that changes only documentation, comments or formatting starts none: the umbrella records it in `STATE.md`. The round doesn't count toward the 3, and if it doesn't end in `pass` the umbrella escalates as in `workflows/P4-review.md`. If a code or test change landed after P5 had started or passed, P5 reruns on the new head before sign-off.
- A rebase, or a merge of the target branch, starts no round and no P5 rerun. If it needed conflict resolution, the resolution is new code and counts as a push.
- The umbrella records the last reviewed head in `STATE.md`, and every other push beside it.

**Rework cap.** The umbrella counts the P3 reworks that P5 failures trigger in `STATE.md`. After 2, a further P5 `fail` that points to P3 stops and goes to the user with each cycle's findings and options; no third rework starts on its own. A fail routed to P2 or P1 doesn't count, because those always need the user. P4 keeps its own cap of 3 rounds.

**Reporting to the user.** The umbrella receives every checkpoint but posts only the major ones: approvals (needed or recorded), phase exits, blockers, decisions the user needs to make, PRs, and review or verification results. Routine checkpoints, such as a handoff touched, a push, a round starting, or a poll that found nothing, go into `STATE.md` and are not posted.

**If an implementation subagent can't keep polling.** A subagent may not outlive its own work. The P3 session schedules CI polls until CI passes, then PR-thread polls every 3 hours until the PR is completed. Each poll follows `standards/pr-feedback.md`; when a fix is needed, the existing P3 session starts a new implementation subagent after the previous one has ended. If the P3 session is unavailable, the umbrella creates a replacement P3 session from the controlling handoff and current findings.

**Isolation.** A session works from its own inputs and does not track other sessions' context or progress unprompted. A P2 session doesn't follow P5's results. If P5 finds that P2's artifacts must change, it notifies the umbrella, and the umbrella sends P2 the request. P2 processes that request only and does not monitor P5 afterwards.

## Model allocation

The native files linked below are the authoritative default model and effort settings. Handoffs reference the relevant file and record only the resolved selection and any override for their run.

| Role | Native configuration |
|---|---|
| Umbrella | [Umbrella profile](profiles/artifex-umbrella.config.toml) |
| P1 research | [Planning profile](profiles/artifex-planning.config.toml) |
| P2 analysis | [Planning profile](profiles/artifex-planning.config.toml) |
| P3 implementation session | [Planning profile](profiles/artifex-planning.config.toml) |
| P3 isolated workers | [`artifex_worker`](agents/artifex-worker.toml) |
| P4 independent review | [`artifex_reviewer`](agents/artifex-reviewer.toml) |
| P5 auto verification | [`artifex_verifier`](agents/artifex-verifier.toml) |

Use the user's override first. For P6, preserve the user's or handoff's selection; this policy assigns no new default. Complexity or evidence of model failure can justify higher effort or a stronger available model; record the reason and selection in the handoff or checkpoint. For an optional full PR review in P5, apply the P4 allocation to the reviewer while retaining the P5 allocation for scenario execution.

Prefer existing native Codex custom-agent configuration (`model` and `model_reasoning_effort`) when selecting a suitable agent type. Otherwise pass explicit model and effort through supported native spawn/session-creation options. Custom-agent settings can override spawn values: check that the selected role matches the intended allocation. Where the spawn API requires a fresh context to set these options, supply the controlling handoff and coordination envelope rather than full conversation history. Select a restricted tool surface when supported and adequate for the work.

**Separate top-level sessions:** the umbrella and P1–P3 are independent chats, so select both model and effort at each session's creation; subagent configuration does not configure them. Use native session-creation `model` and effort options when exposed. For CLI launches, use `codex --profile artifex-umbrella` for the umbrella or `codex --profile artifex-planning` for P1–P3; its file is `$CODEX_HOME/<name>.config.toml` (normally `~/.codex/<name>.config.toml`) with top-level `model` and `model_reasoning_effort` values from the corresponding bundled profile. Alternatively pass `--model <identifier> -c 'model_reasoning_effort="<effort>"'`. Profiles are startup selections, not changes to an existing chat; project or CLI overrides can supersede profile settings. See [Codex profiles](https://learn.chatgpt.com/docs/config-file/config-advanced#profiles).

**Desktop phase-chat creation (required):** whenever the umbrella creates P1, P2 or P3, including a replacement session, read the planning profile above (reuse its values while unchanged) and apply any explicit user override. With the Codex desktop `create_thread` tool (`mcp__codex_app__create_thread`), pass the resolved `model` as `model` and the profile's `model_reasoning_effort` as `thinking` in the creation call. Both fields are required by this Artifex instruction even when the tool schema marks them optional. Keep the existing project, workspace, title, handoff and coordination-envelope rules. A profile name, prompt text or agent TOML does not substitute for these creation arguments.

Record the requested model and effort alongside the returned phase-chat route in `STATE.md`. If the creation result exposes actual settings, record whether they match; otherwise mark runtime confirmation unavailable rather than asserting it. If the tool rejects the requested settings or lacks either selection control, report the creation blocker and requested values through the umbrella; obtain a user-selected fallback rather than silently inheriting the default. This rule does not create an extra approval gate when the native call accepts the configured values, and it does not switch an existing umbrella's model.

**Configuration activation:** keep the bundled agent and profile files as the source of truth. Expose `agents/artifex-*.toml` through symlinks in `$CODEX_HOME/agents/` (normally `~/.codex/agents/`), or the implementation project's `.codex/agents/`. Expose `profiles/artifex-*.config.toml` through symlinks directly under `$CODEX_HOME/`. These links are installation steps, not something skill invocation performs. Check for existing entries before installing; preserve unrelated configuration. An agent file stored only inside this skill is not automatically active.

Select the named agent when the spawn capability exposes agent types. If it exposes only model/effort options, read those settings from the relevant native file and pass them explicitly; instructions alone do not select a configured role. User overrides may require a different role or explicit spawn options because custom-agent file settings take precedence. Reload agent discovery or start a fresh Codex session after installation as needed, and verify runtime role/settings when evidence is available. Report installed files separately from successful runtime selection; do not claim that an existing chat switched models.

For an already-running umbrella or a top-level session without native selection controls, these settings are recommendations: state the requested selection and any mismatch; instructions cannot change the running model. If a model or control is unavailable, report the limitation and use a user-approved or available fallback without claiming enforcement. Do not create a launcher or model-switching layer. Model identifiers are supported by the current runtime; recheck availability only when the target environment differs or rejects one. Native configuration behavior is described in [Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Execution efficiency

- **Context:** load phase-relevant instructions and controlling approved artifacts, using the handoff instead of reconstructing prior conversations. Read an unchanged file again only for a concrete reason, such as a new question, suspected mutation or recovery after lost context. Reference artifact paths and revisions instead of copying their contents.
- **Tool output:** use targeted excerpts, search results, quiet build output and filtered checks. Save full build/test logs and diagnostic evidence to files when needed, then inspect relevant failures and summaries. Read a diff's stat before its relevant hunks; keep generated files out of conversational output. Preserve and inspect all evidence needed to diagnose a failure or verify a result; output reduction must not hide missing coverage or weaken checks.
- **Lifecycle:** when accumulated context obscures the active task or carries substantial obsolete discussion, evaluate native compaction or a fresh-session handoff. Preserve approved decisions and revisions, acceptance criteria, work in progress, evidence paths, blockers, ownership and coordination routes. Transition only when useful; avoid automatic thresholds or routine restarts. Recover from artifacts and update session routes through the umbrella when a replacement is necessary.

## Documents

Documents the user reads or approves are **human-targeted**: kickoff, analysis, specs, verification contract, verification report. By default:

1. **Native document artifacts available:** draft each as a **document artifact**, a commentable document in the environment's document or artifact system, so the user can review it with comments before approving. Keep every review round in the same artifact. Generate or update the corresponding markdown file (`kickoff.md`, `analysis.md`, `specs.md`, ...) in the resolved initiative artifact folder only after the user approves that artifact revision. The artifact is the source of truth and the markdown file is its derived copy.
2. **No native document artifacts:** create the markdown file directly in the resolved initiative artifact folder and immediately open it in the environment's artifact viewer or commentable document preview. The file is the source of truth. This step is complete only when the environment confirms that the file is open in a viewer that lets the user highlight a passage or select a visual element and send the annotation to the agent. A queued, unconfirmed or plain-editor open does not satisfy the gate; report that actual state instead of claiming the viewer is open. Keep every review round in the same file and preview.
3. In either branch, apply each comment or annotation to that specific area while preserving the rest of the document. Ask for explicit approval of the current revision. For a native artifact, record its provider artifact reference and provider revision ID in `STATE.md`; also record the SHA-256 content hash of its approved markdown copy. For a markdown-first document, record its path and SHA-256 content hash. Compute hashes from the exact approved file bytes.
4. If neither native artifacts nor an annotation-capable viewer are available, say so, draft the markdown file, open it in the best available editor or preview, and use passage-specific comments in chat.

Agent-facing documents (`STATE.md`, `review.md`, handoffs, execution summaries, runbooks) are written directly as markdown. The user can override the default for any document.

**Status tracker.** Create a remote status page, a document artifact, **only when the user asks for one**. Follow `references/status-page.md`.

## Optional tools

Workflows name tools by capability. Bind each one here:

| Capability | Used by | Default | Fallback |
|---|---|---|---|
| Benchmark designer: drafts a benchmark contract and runbook, and runs an approved one | P2 contract, P5, P6 | `benchmark-scenario` | `benchmark-designer`, when `benchmark-scenario` isn't installed. If neither exists, write the benchmark part of the contract by hand and say so |
| Handoff writer: turns a session's context into a document another session can execute | P2 | `handoff` | Write the document yourself: what the future session is for, decisions made, constraints, references to artifacts instead of copies, suggested skills. Redact secrets and personal data |
| PR reviewer: reviews a PR and returns findings, action classes and a verdict | P4 | `pr-review-pipeline` | Review by hand as P4 describes: coverage against the approved spec IDs, correctness, unjustified complexity and scope expansion, reported as concrete findings with evidence and a verdict |
| PR feedback handler | P3 | See `standards/pr-feedback.md` | Follow that standard directly |

## Reading map

- `policies/core.md`: authority, scope, approval/version and evidence constraints.
- `standards/design.md`: current/target models, meaningful edge cases, design decisions.
- `standards/specifications.md`: Given/When/Then, handoff and contract quality.
- `standards/evidence.md`: verification rigor, reporting and limitations.
- `standards/pr-feedback.md`: verifying, answering and escalating PR feedback; the PR feedback handler is an optional tool.
- `workflows/`: procedures, entry/exit and routing.
- `templates/`: minimal artifact starting points; omit irrelevant optional sections.
- `references/status-page.md`: the optional remote status page, only when the user asks.

**Deferred:** detailed code-review policy; delivery (merging, deployment, backports); routing tiers; mandatory claim-by-claim evidence tags; automated approval gates, locking and agent orchestration. Do not operationalize deferred items without user agreement.
