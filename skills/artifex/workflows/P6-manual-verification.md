# P6 — Manual verification

**Entry:** Passing review **and** user-approved verification contract, reconciled to the latest approved specs. P5 has finished or is not applicable. **Owner:** Verification agent; user signs off closure.

**Applicability:** only when the contract marks scenarios **manual**, functional, benchmark or both. If it has none, P6 is not applicable and sign-off follows P5.

**Start:** only on the user's explicit trigger: the user asks the umbrella to start P6. It runs as an isolated sub agent working from the manual scenarios in the verification handoff, and the approved specs and contract.

**Codes:** internal codes stay in notes. Keep them out of test names, code, commits, the PR and ticket (`policies/core.md`).

1. Check that the reviewed changeset and contract/spec revisions align. If not, stop and reconcile affected approvals.
2. Execute **the manual scenarios**, with the same care as P5: raw output and derived calculations kept separate, workloads and pass conditions never altered to make a run pass, tests committed only once the umbrella confirms P3 is not making changes, and any push reported to the umbrella. A benchmark marked manual runs through the benchmark designer's Run mode (`SKILL.md`, Optional tools), which refuses to run unless the contract is approved as local markdown. Its session adds the harness it needs.
3. Add the results to the **same verification report** that P5 started, never a new one (`SKILL.md`, Documents). **Notify the umbrella when results are in.**
4. Derive `pass`, `fail`, or `inconclusive` **from the contract**, not confidence or prose.
5. On `fail`, route as in P5: defects to P3, design/spec issues to P2, invalid research assumptions to P1, through the umbrella; unclear cases to user triage.
6. On `pass`, with P5 also passed or not applicable, mark **ready for acceptance** and request **explicit user sign-off**. Only the umbrella may record `closed` after that approval.

**Output:** The verification report extended with the manual scenarios' results and a verdict.

**Exit:** User signs off closure. **Deployment, merging and backports are outside this six-phase skill** unless separately authorized and defined; successful verification does not authorize them.
