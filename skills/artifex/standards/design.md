# Design and edge-case assessment

Use in P1–P2; use the **decision write-up** during P3 escalation or P4 to P6 ambiguity.

## Current → target understanding

Explain only what matters to the milestone: current behavior, constraints, affected components/data flows, intended changes, and relevant code locations. Confirm the high-level current and target models **with the user** before finalizing P2 specs. No exhaustive architecture inventory.

## Decisions

For a material unresolved choice, provide the question, realistic alternatives, material trade-offs, and one recommendation. Include a no-change option **only if meaningful**. Record the user's decision in the controlling artifact/state; don't turn everyday design discussion in P2 into formal escalation.

## Edge cases

A case is **material** only if it affects requirements, design decisions or scope boundaries. Record only material cases, and do not enumerate hypothetical ones merely for completeness. Think through reachability and cost as needed, but write only four things, briefly: scenario, impact, disposition, reason. No mini-investigation.

Dispositions:

- `handle` — required by approved specs or existing guarantees, and can be addressed within the approved design. Specify the behavior.
- `defer` — not required for the current scope, with understood and acceptable consequences. Record it only if it is worth revisiting.
- `escalate` — requires a new design decision, scope expansion, or acceptance of a meaningful risk.

`escalate` is not a final disposition. It means the agent needs the user's decision before the case is handled or deferred. Once the user decides, record `handle` or `defer`.

Record material cases in the specs under Relevant Edge Cases. Existing correctness/security obligations cannot be silently deferred.

## Tradeoffs and limitations register

`milestones/<id>/tradeoffs.md` (`templates/tradeoffs.md`) keeps what the user knowingly accepted or put off during design and implementation, so a later reviewer or verifier can tell a known limitation from a real defect. It holds decided items only. An open question is a blocking question in the specs, or an `escalate` edge case, until the user decides.

**What goes in.** Every `defer` edge case, every design tradeoff the user chose that has a lasting consequence, and later the same kind of decision from P3 to P6. Not behavior the specs already require, and not a `handle` case, which is specified behavior.

**Statuses.** `accepted`, `deferred` or `handled`, defined in the template. Any change between them is allowed and logged.

**Severity** is the consequence while the behavior stays inside its boundary:

- `low`: no user-visible effect, or cosmetic or rare with an easy workaround.
- `medium`: visible degradation or a manual workaround for some users or operators, but never wrong results.
- `high`: wrong or missing behavior for a meaningful set of cases, or an ongoing operational burden. Register it only when the user's decision names it.

**Never registered as accepted or deferred:** data loss, corruption or a leak, a security impact, or behavior that makes an approved spec row untrue. Existing correctness, reliability and security obligations stay mandatory (`policies/core.md`). Dropping a spec behavior is a specs change that needs approval again, not a register row.

**Boundary** is what keeps the register from excusing everything. Behavior inside a row's boundary and as described is *known*: P4 reports it as such and P5 and P6 don't fail it. Behavior outside the boundary, or a worse consequence than the row states, is a normal finding or failure that cites the row. A register row never relaxes a contract pass condition; if one makes a pass condition unreachable, the contract changes and needs approval again.

**Who writes it.** P2 creates it right after specs approval, from the `defer` rows and the proposed tradeoffs the user approved with the specs, before the implementation handoff. Approval of the register is not separate: the user's decision on each row is logged with the specs revision. It is not tied to a revision hash, so changing it doesn't invalidate the specs, the handoffs or the contract. Later entries are change requests through the umbrella that the P2 session applies, or the umbrella applies itself when the session is gone. They need the user's decision, in P3 through the usual design-decision escalation. A reviewer or verifier who finds an unregistered limitation reports it as a finding; they don't add the row.

**Who reads it.** The implementation and verification handoffs link it, P4 reads it as a project note, and the umbrella lists its `accepted` and `deferred` rows when it asks the user to sign off the milestone (`SKILL.md`, Reporting to the user).
