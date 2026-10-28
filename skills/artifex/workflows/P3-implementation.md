# P3 — Implementation

**Entry:** Approved specs, approved verification contract **and** the implementation handoff, with exact revisions. **Start:** when the user says "start P3", the umbrella runs P3 as an **isolated sub agent**, working from the implementation handoff. **Owner:** Implementation agent; user retains design authority.

**Codes:** internal codes stay in notes. Keep them out of code, tests, commits and the PR (`policies/core.md`).

1. Confirm authorized milestone scope, exclusions, controlling artifact revisions and project coding/testing conventions.
2. Implement the agreed change. Choose routine implementation tactics as needed, but do **not** invent requirements, abstractions or extra edge-case coverage.
3. Run appropriate local checks. Preserve useful results and note anything not run.
4. If a **new design decision** appears, **pause affected work**, present realistic options/trade-offs/recommendation to the user through the umbrella, and wait for their decision. Independent work may proceed safely. If material, update/reapprove affected specs and verification contract through P2 before proceeding.
5. If an unanticipated edge case appears, assess whether approved behavior already requires it; otherwise document it as a finding and apply the scope policy. Do not automatically implement it.
6. Open the PR **ready for review, not as a draft**, once the change and its unit tests are in. Explicit VER integration tests are P5 scope. **Notify the umbrella that the PR is open, and don't wait for CI.** The umbrella then starts P4.
7. **After the PR is open**, poll its CI status and stop once it passes. If CI fails, debug, fix, push, **notify the umbrella of the push**, and poll again.
8. Once CI has passed, poll the PR's threads for feedback **every 3 hours** until the PR is completed, following `standards/pr-feedback.md`. Feedback also includes P4 findings that the umbrella relays. Fix what it raises, push, and notify the umbrella of the push. If a thread needs the user's input, **escalate through the umbrella**. If the environment can't keep this sub agent polling between checks, tell the umbrella, which then schedules the polls itself. Notify the umbrella of every push; whether it starts a review round is the umbrella's call (`SKILL.md`, Which pushes start a review round).
9. Hand the umbrella a concise summary: changeset reference, change summary, checks/results, deviations, blockers and any decisions, for state reconciliation.

**Output:** The PR and an execution summary with evidence; no mandatory standalone implementation report.

**Exit:** Approved scope is implemented, the PR is open with CI passing, and known gaps are explicit. Thread polling continues until the PR is completed. Unresolved blocking design choices prevent a clean exit. P4 handles independent review.
