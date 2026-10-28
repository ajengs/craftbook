# Specs, handoff, and verification contract

## Specifications (P2)

- Write concise, testable behaviors as a table with one row per behavior: code, given, when, then, related classes/methods. Give classes/methods where known and leave the cell empty rather than guess.
- Add Constraints and Boundaries (behaviors to preserve, out of scope, relevant edge cases) only for what is not already covered elsewhere. Each part is optional. Edge cases follow `standards/design.md`. Avoid restating the analysis.
- User approval must name the exact artifact revision before the verification contract is drafted.

## Implementation handoff (P2 → P3)

- Create it only after the specs **and the verification contract** are approved and the user asks for it, with the handoff writer (`SKILL.md`, Optional tools). Reference both approved revisions.
- It is an isolated document: a fresh session can execute it using only this document and the approved artifacts it names.
- Do **not** duplicate the entire spec or architectural analysis.
- Name the branch the session works on and include the implementation rules from the template.
- State the milestone objective, agreed approach, relevant code/interfaces, constraints, exclusions, checks expected, and what counts as a completed changeset.
- Make design authority and escalation route clear. Do not over-prescribe trivial coding steps.
- It has no approval step of its own: the user's request to write it is approval of the current specs and contract.
- A second isolated document, the verification handoff, serves the P5 auto and P6 manual verification runs. It names the approved revisions, the auto and manual contract scenarios, how to verify (prefer extended integration tests that run without the app), and where evidence and results go.

## Verification contract (starts after specs are approved; the handoff follows its approval)

- State the kind: functional, benchmark, or both. Design a benchmark with the benchmark designer (`SKILL.md`, Optional tools).
- List **high-level scenarios**, each with a code (`VER-001`, ...). They cover what routine test and CI runs do not show: spec-to-test matching (every approved spec has a covering test) and, as the milestone needs, user interactions, APIs, workflows and data consistency checks. Do not write step-by-step scripts and do not list "run the tests" as a scenario.
- For each scenario: linked spec IDs, what to check, evidence to collect, **measurable pass condition**. Add environment and limitations.
- Prefer extended integration tests that can run without running the app. For a benchmark, its session adds the harness it needs. Mark each scenario `auto` (P5) or `manual` (P6); either part may be empty.
- For benchmarks only: comparison baseline, workload equivalence, repetitions/noise/invalid-run rules, and derivation method as relevant.
- Name where raw evidence will be stored; do not assume it already exists.
- Reconcile the draft with the currently approved specs before requesting approval. If materially affected by later changes, seek approval again before P5.
