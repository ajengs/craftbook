# Verification contract — <milestone>

Status: draft (starts after the implementation checkpoint; the verification handoff is written immediately after this contract is approved)
Specs: <path@revision>
Kind: functional | benchmark | both. For a benchmark, design it with the benchmark designer and reference its contract.

## Scenarios (high level)
Routine test and CI runs are not scenarios. List what they don't show. Keep each scenario at the level of what to check, not a step-by-step script. Mark each **auto** (P5, runs right after review passes) or **manual** (P6, runs on the user's trigger). Either part may be empty.

| Code | Type | Run | Specs covered | What to check | Evidence to collect | Pass condition |
|---|---|---|---|---|---|---|
| VER-001 | Spec-to-test match | auto | All SPEC rows | Each approved spec has a test that covers it, added or existing | Table of spec → test, with gaps listed | No spec without a covering test |
| VER-002 | Full PR review (optional) | auto | All SPEC rows | Review the whole PR, not only the new commits, with the PR reviewer | The review file | No blocks-merge findings. Include only if the user approves it. Runs once: skipped on reruns after rework |
| VER-003 | <user interaction / API / workflow / data consistency / benchmark / other> | <auto / manual> | <SPEC ids> | | | |

## Environment / fixtures / reproducibility

## Benchmark comparison / noise rules (only if applicable)

## Raw output location / derivation method

## Material limitations / exclusions

Approval: pending. Reconcile to approved spec revision before seeking user approval; record decision in `STATE.md`. Approval does not authorize starting any other session.
