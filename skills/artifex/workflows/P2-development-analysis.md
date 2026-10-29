# P2 — Development analysis

**Entry:** One selected milestone plus either (a) approved kickoff and analysis revisions or (b) an approved kickoff revision and the user's explicit small-task scope confirmation. **Start:** the umbrella creates and starts this session when either complete P1 checkpoint arrives. **Owners:** User and analysis agent, collaboratively.

**Inputs:** Selected milestone, approved kickoff revision, either the approved analysis revision or the user's recorded small-task scope confirmation, and relevant code/system context.

**Documents:** specs and verification contract are human-targeted. Review each using the native-artifact or markdown-viewer branch in `SKILL.md`, Documents. Handoffs are agent-facing markdown.

**Order:** specs, implementation handoff and P3 checkpoint; then verification contract and verification handoff. Specs and contract are approved by the user. Each approval immediately produces its handoff. P2 only produces artifacts and runs no implementation; it remains open while P3 runs and for later change requests.

**Context after approval:** use the approved artifact for the next handoff. Evaluate compaction or a fresh-session handoff under `SKILL.md`, Execution efficiency, when the review conversation has become burdensome; approval itself does not require a restart or delay the implementation checkpoint.

1. Restate the **selected milestone only**: objectives, scope/exclusions, constraints, dependencies.
2. Investigate relevant current behavior and architecture; create a shared **high-level current-state model** with the user.
3. Agree on the **target-state model** and material design choices. Use `standards/design.md`; don't introduce complexity to accommodate speculative edge cases.
4. Draft the Given/When/Then specifications as a table (`templates/specs.md`). Add Constraints and Boundaries only for what isn't already covered elsewhere. List only edge cases that affect requirements, design decisions or scope boundaries, each with `handle`, `defer` or `escalate` (`standards/design.md`). Follow `SKILL.md`, Documents: use a native document artifact when available; otherwise create `milestones/<id>/specs.md` and open it in the artifact viewer immediately. Process passage or visual annotations as focused revisions while preserving the rest of the document.
5. Resolve `escalate` cases with the user, or list them as blocking questions. The user reviews the specs through annotations and approves a specific revision. On approval, ensure the approved `milestones/<id>/specs.md` derived copy exists; the umbrella records the provider revision ID and SHA-256 markdown hash, or the markdown-first path and SHA-256 hash, as required by `SKILL.md`, Documents.
6. **Implementation handoff, immediately after specs approval** (`templates/implementation-handoff.md`, `standards/specifications.md`). Create `milestones/<id>/implementation-handoff.md` with the handoff writer (`SKILL.md`, Optional tools), or its fallback, without another approval or request. It is an agent-facing instruction document that a fresh dedicated P3 session can use to coordinate implementation through its own isolated subagent, using only the handoff and the approved specs it names.
   - Tell the writer that the future session implements this milestone from the approved specs, and give it the template's headings.
   - Name the branch the session works on. Use the branch the user gives; if none, propose one for confirmation. An unresolved branch or design choice is a blocker, not a reason to write an incomplete handoff.
   - Include the implementation rules from the template unchanged unless the user says otherwise.
   - Reference the approved specs revision and do not repeat the specs or require a verification contract.
   - Settle every choice that would change the code's shape if reopened (`standards/specifications.md`). Name the model, reasoning effort and agent type for the run (`SKILL.md`, Model allocation).
   - Name `artifex` and `workflows/P3-implementation.md` as suggested instructions, and name the session `<ticket id> P3 implementation <context>`.
   - Notify the umbrella with the approved specs revision, completed implementation-handoff path and revision, and any blocker. With no blocker, this first P2 checkpoint tells the umbrella to create and start a dedicated P3 phase session from the handoff. That P3 session spawns its own isolated implementation subagent. P2 continues to step 7; it does not stop or monitor P3.
7. **Verification contract, after the implementation checkpoint** (`templates/verification-contract.md`, `standards/specifications.md`). Draft and review it through the same native-artifact or markdown-viewer branch in `SKILL.md`, Documents; in the markdown-first branch, create `milestones/<id>/verification-contract.md` before review and keep revising that same file.
   - Decide with the user what the milestone needs: functional verification, a benchmark, or both.
   - List **high-level scenarios**, not scripts, covering what routine test and CI runs don't show: matching each approved spec to a test that covers it, plus, as the milestone needs, user interactions, APIs, workflows and data consistency checks.
   - Prefer extended integration tests that can run without running the app.
   - Mark each scenario **auto** (runs in P5 right after P4 passes) or **manual** (runs in P6 on the user's trigger). A milestone may have no auto scenarios, no manual ones, or both. Say which.
   - Offer the **full PR review** as an optional scenario: the PR reviewer (`SKILL.md`, Optional tools) reviews the whole PR, not only the new commits, in P5. It runs only if the user approves the contract with it included.
   - Benchmark: invoke the benchmark designer (`SKILL.md`, Optional tools) in Draft mode to design the benchmark contract and its runbook. The benchmark session adds the harness it needs. Mark the benchmark auto or manual like any other scenario. The contract is human-targeted and the runbook is agent-facing.
   - Both: one verification contract covers the functional scenarios and points to the benchmark contract for the benchmark part.
   - The user reviews the contract through comments or annotations and approves a specific revision. On approval, synchronize the approved `milestones/<id>/verification-contract.md` copy and record the exact artifact and file identities required by `SKILL.md`, Documents. The draft is **not** permission to execute anything.
8. **Verification handoff, immediately after verification-contract approval** (`templates/verification-handoff.md`). Create `milestones/<id>/verification-handoff.md` with the handoff writer, or its fallback, without another approval or request. It lists the approved specs and contract revisions, the auto and manual scenarios, how to verify them, the evidence destination, and the model and agent type for P5/P6. Notify the umbrella when it is created or modified. P5 cannot start until the approved contract and this handoff are ready.
9. Keep the P2 session available after both checkpoints. Do not monitor P3, P4 or P5. If the umbrella later sends a change request for the specs, contract or either handoff, process that request only. A changed spec or contract needs approval again and any affected handoff must be regenerated before its next consumer starts.

**Handoff meaning:** writing a handoff creates an agent-facing instruction document; handing off creates the phase session that consumes it. Specs approval is the go-ahead to write the implementation handoff, and its complete checkpoint tells the umbrella to create P3 automatically. The P3 session, not the umbrella, starts isolated implementation subagents. Verification-contract approval is the go-ahead to write the verification handoff. Neither handoff has a separate approval gate.

**Outputs:** Approved specs and verification contract; implementation and verification handoff documents ready to run in isolated sessions.

**Exit:** Approved specs and verification contract; implementation and verification handoff documents ready to run in isolated sessions. P3 starts from the first checkpoint in step 6. P2 remains available to finish the verification artifacts while P3 runs and to process later change requests.
