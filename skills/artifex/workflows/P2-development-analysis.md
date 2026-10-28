# P2 — Development analysis

**Entry:** One selected milestone and an approved kickoff, plus the approved analysis when P1 produced one. Small tasks and defects may skip the analysis. **Start:** manually: the user asks the umbrella to start it, once the scope is defined and the kickoff is approved. **Owners:** User and analysis agent, collaboratively.

**Inputs:** Selected milestone, kickoff revision, analysis revision if any, relevant code/system context.

**Documents:** specs and verification contract are human-targeted. Draft each as a document artifact and generate markdown only on approval (`SKILL.md`, Documents). Handoffs are agent-facing markdown.

**Order:** specs, then verification contract, then the handoffs. Specs and contract are approved by the user, each before the next starts. P2 only produces artifacts and runs no implementation.

1. Restate the **selected milestone only**: objectives, scope/exclusions, constraints, dependencies.
2. Investigate relevant current behavior and architecture; create a shared **high-level current-state model** with the user.
3. Agree on the **target-state model** and material design choices. Use `standards/design.md`; don't introduce complexity to accommodate speculative edge cases.
4. Draft the Given/When/Then specifications as a table (`templates/specs.md`). Add Constraints and Boundaries only for what isn't already covered elsewhere. List only edge cases that affect requirements, design decisions or scope boundaries, each with `handle`, `defer` or `escalate` (`standards/design.md`).
5. Resolve `escalate` cases with the user, or list them as blocking questions. The user reviews the specs through comments and approves a specific revision. On approval, write `milestones/<id>/specs.md`; the umbrella records the artifact reference and revision in milestone `STATE.md`.
6. **Verification contract, only after the specs are approved** (`templates/verification-contract.md`, `standards/specifications.md`).
   - Decide with the user what the milestone needs: functional verification, a benchmark, or both.
   - List **high-level scenarios**, not scripts, covering what routine test and CI runs don't show: matching each approved spec to a test that covers it, plus, as the milestone needs, user interactions, APIs, workflows and data consistency checks.
   - Prefer extended integration tests that can run without running the app.
   - Mark each scenario **auto** (runs in P5 right after P4 passes) or **manual** (runs in P6 on the user's trigger). A milestone may have no auto scenarios, no manual ones, or both. Say which.
   - Benchmark: invoke the benchmark designer (`SKILL.md`, Optional tools) in Draft mode to design the benchmark contract and its runbook. The benchmark session adds the harness it needs. Mark the benchmark auto or manual like any other scenario. The contract is human-targeted and the runbook is agent-facing.
   - Both: one verification contract covers the functional scenarios and points to the benchmark contract for the benchmark part.
   - The user reviews the contract through comments and approves a specific revision. On approval, write `milestones/<id>/verification-contract.md` and record it in milestone `STATE.md`. The draft is **not** permission to execute anything.
7. **Handoffs, only after the verification contract is approved and the user asks for them.** The user's request to write a handoff is also approval of the current specs and contract revisions. Record that in milestone `STATE.md` and do not ask again. Create each with the handoff writer (`SKILL.md`, Optional tools). P2 only **produces** these documents. Do not execute them, start any session, or begin implementing here. Each is an isolated document: a fresh session must be able to execute it using only that document and the approved artifacts it names.
   - **Implementation handoff** (`templates/implementation-handoff.md`), for the P3 session.
     - Tell the writer what the future session is for (implementing this milestone from the approved specs) and give it the template's headings.
     - It names the branch the session works on. Use the branch the user gives; if none, propose one for the user to confirm.
     - It includes the implementation rules from the template unchanged, unless the user says otherwise.
     - It references the approved specs and contract revisions and does not repeat them.
     - Its suggested-skills section names `artifex` and `workflows/P3-implementation.md`, and it gives that session's name as `<ticket id> P3 implementation <context>`.
   - **Verification handoff** (`templates/verification-handoff.md`), for the P5 auto verification and P6 manual verification runs. It lists the auto and manual scenarios and how to verify them. P5 cannot start until it exists.
   - Handoffs are agent-facing, so write them as markdown. A handoff writer may save to a temporary directory by default; save each in `milestones/<id>/` instead, because it is a controlling artifact.
   - If the handoff writer cannot be invoked by you, ask the user to run it, or use the fallback in Optional tools.
8. **Notify the umbrella** when a handoff is created or modified. Then stop. P2 does not monitor P3, P4 or P5. If the umbrella later sends a change request for the specs, contract or a handoff, process that request only. A changed spec or contract needs approval again.

**Approval is not a go-ahead to hand off or to start a session.** Approving the contract starts nothing. The user asks for the handoffs, and later starts P3, separately.

**Outputs:** Approved specs and verification contract; implementation and verification handoff documents ready to run in isolated sessions.

**Exit:** Specs and contract approved, and the handoffs written on the user's request. P3 starts only when the user starts it.
