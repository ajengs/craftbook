---
auto_agent: <[VER ids] for P5, or [] if none>
manual_agent: <[VER ids] for a user-triggered, fully agent-executed run, or []>
manual_user: <[VER ids] requiring user interactions, or []>
---
# Diagnosis — <bug>

The frontmatter is read by the router, which records this diagnosis as the verification handoff (`references/orchestration.md`). Quote frontmatter values containing ` #` so the hash is not treated as an inline comment.

Source: <ticket link | P5 finding in milestone <id>>
Seen on: <version, head or environment>
Path: <direct | reproduced | confirm>
Status: <draft | root cause approved <revision> | fix approach approved <revision>>

## Symptom
What was reported, and the behavior expected instead.

## Evidence collected
One entry per source, for the reported instance and time window or version:
- <type: ticket | metric | trace | log | debug recording | profiler capture | dump | P5 report | screenshot | other> | <link or path> | <instance, window or head> | <what it showed>

Unavailable or not checked: <list, and why>.

### Proof
The excerpts that prove the root cause, in this file (`standards/evidence.md`, Evidence in one file): sample exceptions with counts, the stack traces in code blocks, log lines, metric values with window-scoped links, screenshots, dump or profiler output, test output. Each one names its source file or link. Redact customer data.

## Reproduction
One `REP-` row per way to reproduce the symptom or per missing reproduction. Use the verification section to assign available reproductions to runs. Record accepted gaps and their residual risk under Material limitations.

| Code | Symptom it asserts | Kind | Run and owner | Files | Result before the fix | Minimised |
|---|---|---|---|---|---|---|
| REP-001 | <the reported symptom> | <automatic / manual / none> | <P3 regression test, other command and owner, user-run steps, or pending reproduction> | <paths, if available> | <recorded failure and version, P3 baseline assignment, user observation, or accepted gap and decision> | <what was cut and why the rest is load-bearing, if applicable> |

## Verification
This section is the bug's verification contract and verification handoff, shaped like `templates/verification-contract.md`. Routine test and CI runs are not scenarios. Assign each scenario exactly one category: **auto agent run** (`auto_agent`, P5 after P4 passes), **manual agent run** (`manual_agent`, user-triggered P6, fully agent-executed) or **manual user run** (`manual_user`, user-triggered P6 with specified user interactions). The frontmatter lists the `VER-` codes by category.

| Code | Type | Run | Reproductions covered | What to check | Evidence to collect | Pass condition |
|---|---|---|---|---|---|---|
| VER-001 | Reproduction verification (when applicable) | auto_agent | <automatic REP rows assigned to this run> | Check the reported symptom and named sibling symptoms | Recorded before-fix failures and passing results on the exact PR head | Each listed REP failed on the symptom before the change and passes on the head |
| VER-002 | Full PR review (optional) | auto_agent | All REP rows | Review the whole PR with the PR reviewer: the change addresses the named root cause and stays within the fix approach | The review file | No blocks-merge findings. Include only if the user approves it. Runs once: skipped on reruns after rework |
| VER-003 | <environment / data / benchmark / user interaction / other> | <auto_agent / manual_agent / manual_user> | <REP ids> | <observed before-fix failure and expected result on the PR head> | <baseline, head and run output or user observation> | <expected behavior on the PR head> |

### Tools and evidence by run
Local tools catalog: <resolver source, resolved absolute path and full SHA-256; or explicitly not applicable>. See `references/verification-tools.md`.

| Run category / scenario IDs | Tool or skill + reference | Why needed | Artifacts to collect + why | Required / optional | Readiness + checked evidence/date | Gap action / owner |
|---|---|---|---|---|---|---|
| <category / IDs> | <exact tool or skill path/name> | <question it resolves> | <format and observation it supports> | <required / optional> | <ready / needs adjustment / missing / blocked / unchecked; evidence> | <action / owner or none> |

### User interactions (manual user runs only)
| Scenario | Agent preparation | User action / observation needed | Resume signal | Evidence and pass check |
|---|---|---|---|---|
| <ID> | | | | |

### Environment / fixtures / raw output location

### Material limitations / exclusions
<Missing reproduction, user decision and date, alternative evidence and residual risk to carry through to sign-off.>

## Root cause
What is wrong, where (files, methods) and why it produces the symptom.
Evidence: <observed: the probe or measurement that flips the result, with its link or path | inferred: why, and from which sources above>.
Ruled out: <hypotheses and what disproved each, with sources>.

## Fix approach
The exact change: files and methods, and what stays as it is.
Regression test: <where it asserts the symptom | no correct seam, and why>.
Same cause elsewhere: <sibling entry points, or none>.

## Path criteria
Which conditions for the path are met and how they are shown. Confidence: <high | medium | low> and what would change it. For Confirm: what the user must approve or supply.

## Open decisions
Each question the user must answer before approval, with the options and a recommendation. None if there are none.

## Limitations
What was not reproduced, tried or verified.
