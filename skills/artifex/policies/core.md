# Core policies

These are **boundaries**, not a second workflow. Applies wherever relevant across P1–P6.

## Human authority and approval

- The user confirms problem framing, chooses design direction and milestone, approves the P2 specs and the verification contract, and explicitly signs off final milestone closure.
- Approval is **artifact- and revision-specific**. Record the user's explicit decision and revision in `state.json`; ambiguous replies do not count. Approval records are evidence, not technical access controls.
- On a **material** change to an approved artifact, identify impacted specs, handoff, tests, and contracts; reconcile and request renewed approval where applicable. Do not keep executing against stale approvals.
- Approval is needed again only when the specs or the verification contract change. A handoff has no approval of its own: specs approval authorizes the implementation handoff, and verification-contract approval authorizes the verification handoff. Write each immediately after its controlling approval and record it in `state.json`.
- Starting Artifex authorizes the start `route` prints for the invocation's mode (P1, P2, D1 or the router) and, in `project` mode, the P2 for the milestone selected in P1, and the implementation and review that follow. The umbrella starts P2 after P1 reports either (a) the approved kickoff and analysis revisions plus the selected milestone or (b) the approved kickoff revision plus the user's explicit confirmation that the scoped task is the milestone. More P2 sessions, one per further milestone or for an ad hoc analysis, start when the user asks the umbrella. Whenever a P2 session reports an approved specs revision, a completed implementation handoff and no blocker, the umbrella starts an isolated implementation sub agent from that handoff itself; there is no P3 session, and the verification contract is not a prerequisite. P4 and the verification run start from the umbrella's checkpoints. When P4 findings, P5 failures or PR feedback call for a rework, the umbrella starts a new implementation sub agent once the previous one has ended, up to the caps (3 review rounds, 2 reworks after P5 failures). A later route back to P2 or P1 always needs the user.
- The tradeoffs register (`standards/design.md`) records the user's decisions to accept or defer a limitation. It is not an approval gate and doesn't invalidate any approval when it changes. An `accepted` or `deferred` row needs the user's decision; it never covers data loss, corruption, a leak, a security impact or an approved spec behavior.
- A session works from its own inputs and does not track other sessions unprompted. Cross-session changes go through the orchestrator, and the receiving session only processes the request.
- After successful review and verification an agent may report **ready for acceptance**; it must not declare **closed** without user sign-off.

## Design decisions

- During P2, work **with** the user to decide the current/target design and record material choices.
- In P3, **every newly discovered design decision** must be escalated to the user before continuing affected work. State the question, meaningful options, trade-offs, and recommendation. Continue genuinely independent work if safe.
- Routine implementation choices already authorized by the design do **not** count as new design decisions. A review finding that exposes a design ambiguity goes back to the user rather than becoming a reviewer-imposed redesign.

## Scope and proportionality

- Edge cases, dependencies and technical concerns are **findings, not implicit requirements**. Classify material cases as `handle`, `defer` or `escalate` using the definitions in `standards/design.md`.
- No unapproved expansion of requirements, generalized abstractions, defensive layers, or speculative fallback paths. A technically possible scenario alone is insufficient justification.
- Existing approved correctness, reliability, and security obligations are **not optional**. If satisfying them demands a new design choice or substantial scope increase, escalate rather than silently omit or expand.
- Prefer the simplest implementation that satisfies approved requirements. Add abstractions for demonstrated needs, and reopen approved architectural decisions only with concrete contradictory evidence. Minor operational inconveniences do not justify new framework components.
- Review must not manufacture requirements from speculative edge cases.

## Internal codes stay in notes

- Codes we coin for tracking live only in notes: artifacts, `state.json`, handoffs and the status page. That covers Artifex ids such as `SPEC-`, `VER-` and `LIM-`, phase and gate codes, and any other internal code introduced during a session.
- Never put them in code, tests or test names, comments, commit messages, PR titles, descriptions or comments, ticket comments, or any other surface outside the notes. Describe the behavior in words instead. Ticket ids are a team convention and stay.
- This applies in every phase, and to any code added later.

## Evidence integrity

- Don't claim work, approvals, tests, review independence, or results that did not happen.
- Distinguish **observations**, **inferences**, and **assumptions** where the distinction affects a decision or verdict; link material claims to their evidence. Avoid inline tags on every sentence.
- Tests/benchmarks need a reproducible method, raw results where available, derived results clearly separated, and limitations stated. Inconclusive is an acceptable verdict.

## Autonomous execution

Work toward the approved acceptance criteria and, where applicable, verification contract. After a failed implementation, debugging or verification attempt, use its evidence to revise the diagnostic hypothesis or approach before trying again. A retry of the same operation needs a meaningful change in inputs, conditions or evidence, such as confirmed recovery from a transient failure.

Continue routine debugging while each iteration produces useful evidence or progress. When attempts stop doing so, escalate persistent blockers, environmental failures, specification ambiguity or material scope changes through the umbrella. Report attempted approaches, relevant evidence paths, what remains unknown and the decision or external change needed. Another technically possible attempt alone is not a reason to continue. Preserve contract pass conditions and necessary correctness safeguards; an unresolved or invalid run remains explicit under `standards/evidence.md`.
