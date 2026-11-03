# D1 — Bug investigation

**Entry:** A bug, from one of two sources: the user starts Artifex on a bug ticket, or a P5 run reports a **major finding** (`workflows/P5-verification.md`) and the user agrees to investigate it. **Start:** the umbrella creates and starts this session in place of P1 and P2. A bug needs no kickoff or analysis unless the user asks for one. For a P5 finding it also links the new `milestones/<id>/` folder to the milestone and the finding in `STATE.md`. **Owners:** the investigation agent, and the user where the path below asks for approval.

**Inputs:** The ticket, or the P5 finding with its evidence; the code and environment access the user confirms, and the telemetry and artifacts the environment offers. For a P5 finding, the milestone's PR and the head it was verified on.

**Documents:** `diagnosis.md` (`templates/diagnosis.md`). It is human-targeted when the path needs approval (`SKILL.md`, Documents) and plain markdown when it doesn't. It replaces the specs, the verification contract and the verification handoff for this bug.

**Codes:** internal codes stay in notes. Keep them out of the reproduction, tests, commits, the PR and the ticket (`policies/core.md`).

1. **Symptom, place and evidence.** Restate the symptom as reported, with where and on which version it was seen, and don't guess at causes yet. Ask the user once for the branch and working directory (checkout or worktree) the fix will be made on; for a P5 finding the default is the milestone's PR branch.
   - For a bug that comes from a ticket, collect what the available telemetry and artifacts show before building the reproduction: metrics, traces, logs, debug recordings, profiler captures and dumps, for the reported instance and time window (`SKILL.md`, Optional tools). Record in `diagnosis.md` what each one showed, what was unavailable and what wasn't checked. Evidence can locate the cause when no reproduction is possible, but the fix still follows the reproduction rule in step 7.
   - For a P5 finding, start from P5's evidence and add telemetry only where it doesn't identify the cause.
2. **Reproduction.** Build a command that goes red on this symptom, with the debug loop tool (`SKILL.md`, Optional tools), phases 1 to 4. It must be deterministic, fast, runnable unattended, and assert the reported symptom rather than a nearby failure. Minimise it until every remaining element is load-bearing. Record its kind: automatic, manual (steps a person runs) or none.
   - Revert temporary instrumentation and working-tree edits at the end; D1 commits and pushes nothing. Save the reproduction files in the milestone folder and name the run command.
   - If no reproduction can be built, say what was tried and ask the user for access to a reproducing environment, a captured artifact, or permission to add temporary instrumentation. Don't hypothesise past that.
3. **Root cause.** Rank 3 to 5 falsifiable hypotheses before testing any, test them one variable at a time, and name the cause with its evidence, marking what was observed and what is only inferred. Say what was ruled out.
4. **Fix approach.** The exact change (files and methods), what stays as it is, where a regression test can assert the symptom (no correct seam is itself a finding), and the same cause elsewhere.
5. **Path.** Pick one, and record in `diagnosis.md` which conditions are met and how they are shown.

| Path | Conditions | User approval |
|---|---|---|
| Direct | The cause is observed, not inferred. The change is small and exact (named files and methods, one component) and the evidence is conclusive. A regression test can assert the symptom. Confidence is high | None |
| Reproduced | The reproduction is automatic and red, and goes green on the proposed change in a scratch copy | None |
| Confirm | Anything else: the cause is inferred, the reproduction is manual or missing, or more than one fix is reasonable | The root cause first, then the fix approach |

   Whatever the path, a fix that needs a design decision (a contract, schema or data change, or behavior beyond the symptom) belongs to the user: use Confirm for that decision.
6. **Direct or Reproduced.** Write the implementation handoff right away with the handoff writer (`SKILL.md`, Optional tools), referencing the diagnosis revision (`templates/implementation-handoff.md`). Notify the umbrella with the path, the conditions met, and the diagnosis and handoff paths and revisions. The umbrella starts the implementation sub agent and posts one line saying a bug fix started without approval and why, so the user can redirect it.
7. **Confirm.** Present the diagnosis for root-cause approval with the best reproduction in hand, and the user approves a revision. Then add the fix approach and the user approves that revision. The fix does not start without a solid reproduction: red, run at least once, and matching the reported symptom. A manual reproduction is run by the user and also becomes a manual scenario (P6). With none, the user decides what to supply or explicitly accepts fixing without one, and the umbrella records that as a risk. After the fix-approach approval, write the handoff as in step 6; the approval is the go-ahead and the handoff has no approval of its own.
8. **In flight.** The user can move a bug between paths at any time, in either direction ("ask me before fixing", "just fix it"). The umbrella records the change in `STATE.md` and it takes effect at once. If the implementation sub agent on Direct or Reproduced finds that its change doesn't turn the reproduction green, or that the fix needs a design decision, it stops and reports to the umbrella, which sends the bug back to D1 on Confirm. That is not a rework and counts toward no cap.

**From a P5 finding.** The fix goes on the milestone's PR through the usual P3 and P4 path and counts as one of the 2 reworks after P5 failures (`SKILL.md`, Rework cap). A bug outside the milestone's changes gets its own PR, and whether it blocks the milestone's closure is the user's decision, which the umbrella asks for.

**Verification.** The reproduction is the verification scenario, and `diagnosis.md` stands in for the contract and the handoff.
- If the reproduction is the regression test in the PR and CI runs it, P5 is not applicable: once P4 has passed and CI is green, the umbrella asks for sign-off.
- If it needs an environment, data or a benchmark, P5 runs it on the PR head, with any sibling symptoms the diagnosis lists. A manual reproduction goes to P6 on the user's trigger.
- A performance bug's reproduction is a benchmark: design it with the benchmark designer (`SKILL.md`, Optional tools), and the diagnosis points to its contract.

From the implementation handoff on, P3 to P6 run as usual. D1 stays available for change requests relayed by the umbrella and does not monitor P3 to P6.

**Output:** `diagnosis.md`, the reproduction files, and the implementation handoff.

**Exit:** On Direct and Reproduced, the handoff is complete and reported. On Confirm, the fix approach is approved and the handoff is complete and reported.
