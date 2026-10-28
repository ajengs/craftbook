# ⟨id⟩ — Benchmark agent runbook

**Status:** `draft` (mirrors the contract; the contract is authoritative) · **Date:** ⟨YYYY-MM-DD⟩  
**Contract:** [benchmark-contract.md](benchmark-contract.md)

This runbook says how to execute the contract. It never reinterprets it: a decision is stated once, in the contract. Tag each value `[user]`, `[context: <where>]`, `[default]` or `[proposal]`. A required field still marked ⟨required⟩ blocks Run.

## Readiness gate

Run only when all hold: the contract is `approved`, it has no Blocking inputs or proposed values, this runbook has no ⟨required⟩ fields or `[proposal]` values, and every tooling row below is past `to write`.

## Contract value sources

| Contract value | Value | Tag | Source or basis |
|---|---|---|---|
| ⟨e.g. decision threshold⟩ | ⟨value⟩ | ⟨tag⟩ | ⟨who said it, where, or what the estimate rests on⟩ |

## Preflight checklist

Every check passes before the first unit. A failure means stop and report.

| ID | Check | How | Expected |
|---|---|---|---|
| F1 | Target reachable and healthy | ⟨command or query⟩ | ⟨expected state⟩ |
| F2 | Build or configuration under test is the intended one | ⟨provenance check⟩ | ⟨commit or version⟩ |
| F3 | Access works (credentials by name, sign-in, tunnels) | ⟨how⟩ | ⟨expected⟩ |
| F4 | Arm switch reaches the code under test | ⟨reversible probe⟩ | ⟨expected evidence⟩ |
| F5 | Output folder and capture tools ready | ⟨how⟩ | ⟨expected⟩ |

## Stop conditions

- ⟨a guardrail would be crossed⟩.
- ⟨a preflight check fails, or the A/A gate fails⟩.
- ⟨an arm check fails twice⟩.
- ⟨the deadline will pass before the run order finishes, or elapsed or projected time passes the contract's upper bound⟩.
- ⟨a step needs a user-owned action⟩.

Everything else is proceed and log: a single invalid run, a script bug fixed in place, a recovery described here.

## Arm setup and signatures

| Arm | Setting | Full value | How applied | How verified |
|---|---|---|---|---|
| ⟨name (code)⟩ | ⟨setting⟩ | ⟨exact value⟩ | ⟨step⟩ | ⟨arm check⟩ |

## Per-unit procedure

1. ⟨apply the arm and run its arm check⟩.
2. ⟨run the workload with the named script or steps⟩.
3. ⟨collect the artifacts listed below⟩.
4. ⟨apply the contract's invalid-run rules and the parity check⟩.
5. ⟨append a ledger row⟩.

## Artifacts per phase

| Phase | Artifact | Path |
|---|---|---|
| Every unit | Run log, raw measurements, environment printout | ⟨path pattern⟩ |
| ⟨phase⟩ | ⟨capture⟩ | ⟨path⟩ |

## Tooling and work still to implement

| Item | Purpose | State |
|---|---|---|
| ⟨script or tool⟩ | ⟨what it does⟩ | `exists` / `written, never run` / `rehearsed` / `to write` |

## Permissions

**Allowed:** ⟨actions the contract approves, including run-specific ones⟩.

**Ask first:** ⟨anything not under Allowed or Never⟩.

**Never:**
- Queue builds or pipeline runs, deploy, activate or change shared configuration, write to repositories or pull requests, or run unscoped test suites, unless the contract names it.
- Print, log or write a secret.
- ⟨run-specific prohibitions⟩.

## Teardown

- [ ] Revert any switch the agent made, and verify it.
- [ ] Stop anything the agent started.
- [ ] Ask before deleting test data.
- [ ] ⟨run-specific cleanup⟩.

## Run ledger

Every phase gets a row: preflight, setup, rehearsal, each unit attempt and rerun, analysis, teardown, results, and any time spent waiting on the user. Write timestamps as they happen.

| Phase | Arm | UTC window | Duration | Valid? | Artifacts path | Notes |
|---|---|---|---|---|---|---|

## Results order

`benchmark-results-⟨round⟩.md`, in this order: verdict against the contract's decision rule (labelled a reproduction when n = 1), per-scenario numbers (with the A/A spread if one ran), parity, invalid runs and why, what wasn't measured, and the run duration (estimate vs actual, active vs waiting, post-rehearsal projection, rerun cost, cause of the biggest deviation). Every number gets its source. Mechanism claims are hypotheses unless a capture shows them.
