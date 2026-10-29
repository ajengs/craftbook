# Core policies

These are **boundaries**, not a second workflow. Applies wherever relevant across P1–P6.

## Human authority and approval

- The user confirms problem framing, chooses design direction and milestone, approves the P2 specs and the verification contract, and explicitly signs off final milestone closure.
- Approval is **artifact- and revision-specific**. Record the user's explicit decision and revision in the milestone `STATE.md`; ambiguous replies do not count. Approval records are evidence, not technical access controls.
- On a **material** change to an approved artifact, identify impacted specs, handoff, tests, and contracts; reconcile and request renewed approval where applicable. Do not keep executing against stale approvals.
- Approval is needed again only when the specs or the verification contract change. A handoff has no approval of its own: specs approval authorizes the implementation handoff, and verification-contract approval authorizes the verification handoff. Write each immediately after its controlling approval and record it in `STATE.md`.
- Starting Artifex authorizes the initial P1, P2 and P3 for the milestone selected in P1. The umbrella starts P2 after P1 reports either (a) the approved kickoff and analysis revisions plus the selected milestone or (b) the approved kickoff revision plus the user's explicit confirmation that the scoped task is the milestone. After P2 reports the approved specs revision, completed implementation handoff and no blocker, the umbrella creates a dedicated P3 phase session from that handoff; the verification contract is not a P3 prerequisite. P4 and the verification run start from the umbrella's checkpoints. The existing P3 session starts a new implementation subagent when its previous subagent has ended. If the P3 session is unavailable, the umbrella creates a replacement P3 session from the controlling handoff and current findings. A later route back to P2 or P1 always needs the user.
- A session works from its own inputs and does not track other sessions unprompted. Cross-session changes go through the orchestrator, and the receiving session only processes the request.
- After successful review and verification an agent may report **ready for acceptance**; it must not declare **closed** without user sign-off.

## Design decisions

- During P2, work **with** the user to decide the current/target design and record material choices.
- In P3, **every newly discovered design decision** must be escalated to the user before continuing affected work. State the question, meaningful options, trade-offs, and recommendation. Continue genuinely independent work if safe.
- Routine implementation choices already authorized by the design do **not** count as new design decisions. A review finding that exposes a design ambiguity goes back to the user rather than becoming a reviewer-imposed redesign.

## Scope and proportionality

- Edge cases are **findings, not implicit requirements**. Assess only material cases for realism, consequences, and the smallest adequate handling.
- No unapproved expansion of requirements, generalized abstractions, defensive layers, or speculative fallback paths. A technically possible scenario alone is insufficient justification.
- Existing approved correctness, reliability, and security obligations are **not optional**. If satisfying them demands a new design choice or substantial scope increase, escalate rather than silently omit or expand.
- Review must not manufacture requirements from speculative edge cases.

## Internal codes stay in notes

- Codes we coin for tracking live only in notes: artifacts, `STATE.md`, handoffs and the status page. That covers Artifex ids such as `SPEC-` and `VER-`, phase and gate codes, and any other internal code introduced during a session.
- Never put them in code, tests or test names, comments, commit messages, PR titles, descriptions or comments, ticket comments, or any other surface outside the notes. Describe the behavior in words instead. Ticket ids are a team convention and stay.
- This applies in every phase, and to any code added later.

## Evidence integrity

- Don't claim work, approvals, tests, review independence, or results that did not happen.
- Distinguish **observations**, **inferences**, and **assumptions** where the distinction affects a decision or verdict; link material claims to their evidence. Avoid inline tags on every sentence.
- Tests/benchmarks need a reproducible method, raw results where available, derived results clearly separated, and limitations stated. Inconclusive is an acceptable verdict.
