# P3 — Implementation

**Entry:** Approved specs and the completed implementation handoff, with exact revisions and no blocker. The verification contract is not required to start. **Start:** The umbrella creates a dedicated P3 session from the implementation handoff. That session owns implementation coordination and runs the coding work through its own isolated subagent. **Owner:** P3 session; the user retains design authority.

**Codes:** internal codes stay in notes. Keep them out of code, tests, commits and the PR (`policies/core.md`).

1. Confirm the authorized milestone scope, exclusions, controlling artifact revisions, coordination route and project coding/testing conventions. Start one isolated implementation subagent from the controlling handoff; give it the handoff by path and revision without restating or expanding it.
2. The implementation subagent implements the agreed change. It chooses routine implementation tactics as needed, but does **not** invent requirements, abstractions or extra edge-case coverage.
3. The implementation subagent runs appropriate local checks, preserves useful results and notes anything not run.
4. If the implementation subagent finds a **new design decision**, it pauses affected work and reports the question, realistic options, trade-offs and recommendation to the P3 session. P3 escalates it through the umbrella and waits for the user's decision. Independent work may proceed safely. If material, update and reapprove the affected specs and any existing affected verification contract through P2 before proceeding.
5. If the implementation subagent finds an unanticipated edge case, it assesses whether approved behavior already requires it; otherwise it reports the case as a finding to P3 and applies the scope policy. It does not automatically implement it.
6. The implementation subagent opens the PR **ready for review, not as a draft**, once the change and its unit tests are in. Explicit VER integration tests are P5 scope. It reports the open PR to the P3 session; the P3 session relays that checkpoint to the umbrella without waiting for CI, and the umbrella starts P4.
7. **After the PR is open**, the P3 session coordinates CI polling until it passes. When a fix is needed, the existing P3 session starts a new implementation subagent after the previous one has ended; that subagent debugs, fixes, pushes and reports the push to P3, which relays it to the umbrella.
8. Once CI has passed, the P3 session coordinates polling of the PR's threads **every 3 hours** until the PR is completed, following `standards/pr-feedback.md`. Feedback also includes P4 findings that the umbrella relays to P3. When a fix is needed, P3 starts a new implementation subagent after the previous one has ended. The subagent fixes, pushes and reports to P3; P3 relays every push to the umbrella. If a thread needs the user's input, P3 escalates through the umbrella. Whether a push starts a review round is the umbrella's call (`SKILL.md`, Which pushes start a review round).
9. The implementation subagent hands the P3 session a concise summary: changeset reference, change summary, checks/results, deviations, blockers and any decisions. The P3 session relays checkpoints, findings, blockers and results to the umbrella for state reconciliation.

**Rework:** The existing P3 session starts a new implementation subagent when its previous subagent has ended. If the P3 session is unavailable, the umbrella creates a replacement P3 session from the controlling handoff and current findings.

**Output:** The PR and an execution summary with evidence; no mandatory standalone implementation report.

**Exit:** Approved scope is implemented, the PR is open with CI passing, and known gaps are explicit. The P3 session remains the coordination owner while thread polling continues until the PR is completed. Unresolved blocking design choices prevent a clean exit. P4 handles independent review.
