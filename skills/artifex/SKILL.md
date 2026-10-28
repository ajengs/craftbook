---
name: artifex
description: Use when the user says "Artifex", is starting or resuming an Artifex initiative (umbrella session, milestones, STATE.md), or is running an Artifex phase (P1-P6) as a scoped session. A user-led engineering workflow for research, design, scoped implementation, independent review and contract-based verification. Not for a single ticket, a plain "implement this spec", a standalone PR review, or a session handoff.
---

# Artifex

**Intent:** Automate mechanics without delegating engineering judgment. Keep work scoped, traceable, proportionate, and verifiable.

This is an **instructional skill**, not a permissions system or autonomous orchestrator. Never imply approvals, file writes, agent launches, test results, or enforcement happened unless they actually did.

## Start here

1. When the user starts Artifex, this session becomes the **umbrella**. It immediately creates a new session to start P1, and does no P1 work itself. In any other session, identify the initiative, milestone, phase, and whether you are the umbrella or a scoped child.
2. Read the relevant `STATE.md`, current controlling artifacts, and **only** the workflow for the active phase. Follow its linked standards and template(s), not the whole package.
3. If an approval, source artifact, or status is missing, say so. Do not infer it from conversational enthusiasm or an older artifact.
4. Perform the work and hand back a concise result: **verdict / findings, artifacts changed, decisions or blockers, next action**. Avoid documenting routine mechanics.

## Six phases

| Phase | Workflow | Main output | Exit condition |
|---|---|---|---|
| P1 Research & analysis | `workflows/P1-research.md` | Kickoff, plus analysis with direction and milestones unless the task is small or a defect | User chooses direction and milestone, or for a small task approves the kickoff alone |
| P2 Development analysis | `workflows/P2-development-analysis.md` | Given/When/Then specs, then verification contract, then the implementation and verification handoffs | User approves specs and contract. Handoffs are written when the user asks. Nothing starts a session |
| P3 Implementation | `workflows/P3-implementation.md` | Changeset, ready PR, CI and PR-thread follow-up | PR open and CI passing; thread polling continues until the PR is completed |
| P4 Review | `workflows/P4-review.md` | Review findings and verdict per round, up to 3 rounds (1 for rework that P5 triggered) | Review passed, or escalation after round 3 |
| P5 Auto verification | `workflows/P5-verification.md` | Results of the contract's auto scenarios. Not applicable when there are none | Results in; sign-off if there is no P6 |
| P6 Manual verification | `workflows/P6-manual-verification.md` | Results of the contract's manual scenarios (functional, benchmark or both). Not applicable when there are none | User explicitly signs off milestone closure |

**Order in P2:** the verification contract is drafted **only after the specs are approved**, and the handoffs are written **only after the contract is approved**. The contract lists high-level scenarios that go beyond routine test and CI runs, and prefers extended integration tests that run without the app. The contract marks each scenario **auto** (run in P5 right after P4 passes) or **manual** (run in P6 on the user's trigger). P5 and P6 require a passing review **and** the approved contract. Approval is needed again only if the specs or the contract change.

## Boundaries

Read `policies/core.md`. In particular:
- The user owns framing, new design decisions, approvals of specs and the verification contract, and final milestone closure. A handoff has no approval of its own: the user's request to write it counts as approval of the current specs and contract revisions, so don't ask again.
- Any **new design decision discovered during P3** must be escalated before affected work continues. P2 is the collaborative design phase, not an escalation ceremony.
- Edge cases are findings, not automatically requirements. Do not grow scope or complexity without a justified, approved reason.
- Internal codes (Artifex ids like SPEC- and VER-, phase codes, any code coined in a session) stay in notes. Never put them in code, tests, commits, PRs or ticket comments, in any phase. Describe the behavior in words.
- Approved artifacts are version-specific. A material revision invalidates affected downstream approval(s) until reconciled.
- Approving an artifact is not a go-ahead to start another session. Starting P2 and P3 needs the user's own request. P1 starts when the user starts Artifex, and P4 and the verification run start from the umbrella's checkpoints (see Session triggers).

## Coordination and working state

One **umbrella session per initiative** coordinates milestones, scoped child sessions and isolated sub agents, dependencies, approvals, and artifact versions. Artifacts, not session memory, carry context across sessions.

```text
work/<initiative>/
  STATE.md                         # Umbrella-owned initiative registry
  kickoff.md
  analysis.md
  milestones/<id>/
    STATE.md                       # Umbrella-owned milestone state
    specs.md
    implementation-handoff.md
    verification-contract.md
    review.md                      # Optional; may be a concise handoff report
    verification-report.md
```

Use `templates/STATE.md` for both state files. The **umbrella is the single writer** of shared `STATE.md` files and approval records; child sessions write only their assigned deliverables and return status for reconciliation. If the environment cannot coordinate sessions, produce a handoff and ask the user to launch the child; don't pretend it started. Keep parallel code changes isolated when possible (e.g. separate Git worktrees). This is a convention, **not atomic-write protection**.

**Session names:** name every new Artifex session or sub agent `<ticket id> <phase code> <phase name> <additional context if any>`, separated by single spaces and without brackets, for example `PROJ-123 P3 implementation` or `PROJ-123 P2 analysis M1 specs`. Phase names: P1 research, P2 analysis, P3 implementation, P4 review, P5 auto verification, P6 manual verification. Use the ticket id the user gives, exactly as given, even if the kickoff says otherwise. Only if the user gave none, take it from the kickoff, or the initiative name if the initiative has none, and say which you used. Set the name where the environment allows it, otherwise suggest it to the user.

**Starting a child session:** when the user asks for one, do exactly what they asked and no more.
- If they provide a handoff document, that document carries the child's instructions. Point the child at it (path and revision) and don't restate, extend or reinterpret it.
- If there is no document, pass context from the user's prompt only.
- Values the user states (ticket id, session name, branch, scope) are used exactly as given. Defaults from the kickoff or `STATE.md` apply only to what the user left unsaid, and are never swapped in for a value the user stated.
- If you must write a brief yourself because no document exists, state what the prompt gives you: milestone, role, scope, controlling artifact **paths + revisions**, deliverable, exclusions and escalation route, as far as known. Do not rely on undocumented context from another chat. Prefer existing project coding/testing conventions over invented Artifex ones.

## Session triggers, checkpoints and isolation

| Phase | How it runs |
|---|---|
| P1 | A new session, created by the umbrella immediately when the user starts Artifex |
| P2 | A new session, started manually: the user asks the umbrella, once the kickoff is approved |
| P3 | An **isolated sub agent** of the umbrella session, started when the user says "start P3", working from the implementation handoff |
| P4 | An isolated sub agent of the umbrella, started automatically when P3 reports the PR is open, and again for each later review round when P3 reports fixes pushed. The umbrella does not wait for CI |
| P5 auto verification | An isolated sub agent of the umbrella, started automatically once P4 has passed and the verification handoff is ready with no blocker or dependency. Not applicable when the contract has no auto scenario |
| P6 manual verification | An isolated sub agent of the umbrella, started only on the user's explicit trigger (the user asks the umbrella). Not applicable when the contract has no manual scenario. A benchmark in either part runs through the benchmark designer (see Optional tools), whose session adds the harness it needs |

**Checkpoints.** A phase notifies the umbrella, through whatever channel the environment gives, when it: creates or modifies a handoff (P2); opens the PR, and pushes new commits after it is open (P3); finishes a review round (P4); has verification or benchmark results (P5, P6). Findings and change requests travel through the umbrella, not directly between sessions or sub agents. When P3 needs the user's input, for example on a PR thread, it escalates through the umbrella.

**Reporting to the user.** The umbrella receives every checkpoint but posts only the major ones: approvals (needed or recorded), phase exits, blockers, decisions the user needs to make, PRs, and review or verification results. Routine checkpoints, such as a handoff touched, a push, a round starting, or a poll that found nothing, go into `STATE.md` and are not posted.

**If P3 can't keep polling.** A sub agent may not outlive its own work. If the environment can't keep the P3 sub agent polling, the umbrella schedules the polls with the environment's scheduler: CI until it passes, then PR threads every 3 hours until the PR is completed. Each poll follows `standards/pr-feedback.md`, and when a fix is needed the umbrella starts a new P3 sub agent from the implementation handoff and the findings.

**Isolation.** A session works from its own inputs and does not track other sessions' context or progress unprompted. A P2 session doesn't follow P5's results. If P5 finds that P2's artifacts must change, it notifies the umbrella, and the umbrella sends P2 the request. P2 processes that request only and does not monitor P5 afterwards.

## Documents

Documents the user reads or approves are **human-targeted**: kickoff, analysis, specs, verification contract, verification report. By default:

1. Draft each as a **document artifact**, a commentable document in the environment's document or artifact system (for example a Claude Docs document), so the user can review with comments before approving. If the environment has none, say so and draft the markdown file instead.
2. Generate the **markdown** file (`kickoff.md`, `specs.md`, ...) in the work folder only **after the user approves** that revision. Record the artifact reference and the approved revision in `STATE.md`.
3. Every later change goes to the **same artifact**, never a new one. If the markdown already exists, update it in the same step so the two match. The artifact is the source and the markdown is a derived copy. Never edit only one of them.

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
