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
