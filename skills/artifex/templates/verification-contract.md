# Verification contract — <milestone>

Status: draft (starts after the implementation checkpoint; the verification handoff is written immediately after this contract is approved)
Specs: <path@revision>
Kind: functional | benchmark | both. For a benchmark, design it with the benchmark designer and reference its contract.

## Scenarios (high level)
Routine test and CI runs are not scenarios. List what they don't show. Keep each scenario at the level of what to check, not a step-by-step script. Assign exactly one category: **auto agent run** (`auto_agent`, P5 automatically after P4 passes); **manual agent run** (`manual_agent`, explicitly user-triggered P6, then fully agent-executed); **manual user run** (`manual_user`, user-triggered P6 requiring specified user interactions). Any category may be empty. Starting P6 is not evidence that its user interactions happened.

| Code | Type | Run | Specs covered | What to check | Evidence to collect | Pass condition |
|---|---|---|---|---|---|---|
| VER-001 | Spec-to-test match | auto_agent | All SPEC rows | Each approved spec has a test that covers it, added or existing | Table of spec → test, with gaps listed | No spec without a covering test |
| VER-002 | Full PR review (optional) | auto_agent | All SPEC rows | Review the whole PR, not only the new commits, with the PR reviewer | The review file | No blocks-merge findings. Include only if the user approves it. Runs once: skipped on reruns after rework |
| VER-003 | <user interaction / API / workflow / data consistency / benchmark / other> | <auto_agent / manual_agent / manual_user> | <SPEC ids> | | | |

## Tools and evidence by run
Local tools catalog: <resolver source, resolved absolute path and full SHA-256; or explicitly not applicable>. See `references/verification-tools.md`.

| Run category / scenario IDs | Tool or skill + reference | Why needed | Artifacts to collect + why | Required / optional | Readiness + checked evidence/date | Gap action / owner |
|---|---|---|---|---|---|---|
| <category / IDs> | <exact tool or skill path/name> | <question it resolves> | <format and measurement/observation it supports> | <required / optional> | <ready / needs adjustment / missing / blocked / unchecked; evidence> | <action / owner or none> |

List only selected capabilities. A required missing tool or artifact prevents a pass; document an equivalent fallback or resolve the gap. Optional evidence may be omitted with a reason. Do not collect every catalog artifact by default.

## User interactions (manual user runs only)
| Scenario | Agent preparation | User action / observation needed | Resume signal | Evidence and pass check |
|---|---|---|---|---|
| <ID> | | | | |

## Environment / fixtures / reproducibility

## Benchmark comparison / noise rules (only if applicable)

## Raw output location / derivation method

## Material limitations / exclusions

## Open decisions
Each question the user must answer before approval, with the options and a recommendation. None if there are none.

Approval: pending. Reconcile to approved spec revision before seeking user approval; record decision in `state.json`. Approval does not authorize starting any other session.
