# Specifications — <milestone>

Kickoff: <path@revision>
Analysis: <path@revision, if one exists>

## Current → target system (high level)

## Behaviors
| Code | Given | When | Then | Related classes/methods |
|---|---|---|---|---|
| SPEC-001 | <starting condition> | <action> | <observable result> | <where known> |

## Constraints and Boundaries
Optional. Omit any subsection already covered elsewhere, such as in the analysis or the behaviors above.

### Behaviors to Preserve

### Out of Scope

### Relevant Edge Cases
Only cases that affect requirements, design decisions or scope boundaries. Do not list hypothetical cases for completeness. An `escalate` row is resolved by the user into `handle` or `defer`.

| Scenario | Impact | Disposition (`handle` / `defer` / `escalate`) | Reason |
|---|---|---|---|

### Tradeoffs and Limitations Accepted
Design tradeoffs the user chose that have a lasting consequence and aren't an edge case above, one line each: what, consequence, and the boundary at which it would still be a defect. Together with the `defer` rows above, approving the specs is the user's decision on these, and they seed `tradeoffs.md` (`templates/tradeoffs.md`). Omit if there are none. Dropping a behavior from the table above is a specs change, not a tradeoff.

## Blocking questions
Each question the user must answer before approval, including workspace choices such as branch, target or working directory, with the options and a recommendation. None if there are none.

Approval: pending; explicit decision + revision recorded in `state.json`.
