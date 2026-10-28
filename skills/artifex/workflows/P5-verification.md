# P5 — Auto verification

**Entry:** Passing review **and** user-approved verification contract, reconciled to the latest approved specs. **Owner:** Verification agent; user signs off closure.

**Applicability:** only when the contract marks scenarios **auto**, functional, benchmark or both. If it has none, P5 is not applicable: tell the umbrella, which tells the user whether P6 applies.

**Start:** an isolated sub agent started by the umbrella **automatically** once P4 has passed and the verification handoff is ready with no blocker or dependency. It works from the auto scenarios in the verification handoff, and the approved specs and contract.

**Codes:** internal codes stay in notes. Keep them out of test names, code, commits, the PR and ticket (`policies/core.md`).

1. Check that the reviewed changeset and contract/spec revisions align. If not, stop and reconcile affected approvals.
2. Execute **the auto scenarios**. They go beyond routine test and CI runs: matching each spec to a covering test, and, as the contract lists them, user interactions, APIs, workflows and data consistency checks. A benchmark marked auto runs through the benchmark designer's Run mode (`SKILL.md`, Optional tools), whose session adds the harness it needs. Prefer extended integration tests that run without running the app, and add explicit integration tests where a scenario needs one. Commit them on the PR's branch, and only once the umbrella has confirmed P3 is not making changes. Parallel changes should not happen, because P5 starts after P3 and P4 are done. If P3 turns out to be active, stop and tell the umbrella; that case is handled manually. Notify the umbrella of any push. Use the running app only when a scenario can't be checked otherwise. Keep raw output and derived calculations separate. Don't silently alter workloads or pass conditions to make a run pass.
3. Report scenario results, environment, deviations, invalid runs and material limitations (`standards/evidence.md`); draft the verification report (human-targeted: a document artifact, with `verification-report.md` generated on approval per `SKILL.md`, Documents) with scenario outcomes, evidence paths, limitations and verdict. **Notify the umbrella when results are in.**
4. Derive `pass`, `fail`, or `inconclusive` **from the contract**, not confidence or prose.
5. On `fail`, tell the umbrella: implementation defects go to P3, design/spec issues to P2, invalid research assumptions to P1, through the umbrella. If unclear, request user triage. On `inconclusive`, identify what is missing. Do not monitor the receiving session afterwards.
6. On `pass`: if the contract has no manual scenarios, mark **ready for acceptance** and request **explicit user sign-off**. If it has, report the P5 results and leave sign-off until P6 is done. Only the umbrella may record `closed` after the user's approval.

**Output:** The verification report with raw evidence references and a verdict for the auto scenarios.

**Exit:** Results are in. User signs off closure when there is no P6. **Deployment, merging and backports are outside this six-phase skill** unless separately authorized and defined; successful verification does not authorize them.
