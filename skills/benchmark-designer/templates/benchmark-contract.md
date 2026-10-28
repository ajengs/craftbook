# ⟨id⟩ — Benchmark contract

**Status:** `draft` · **Date:** ⟨YYYY-MM-DD⟩  
**Reference:** ⟨ticket or issue link and title⟩ · **Change:** ⟨PR or build link, or "none (comparison of settings)"⟩  
**Related:** [Agent runbook](benchmark-agent-runbook.md) · ⟨background: earlier plans, notes, or omit⟩

> **Approval required:** Do not start measured runs until the status is `approved`. This contract defines the experiment and the decision rules. The runbook defines how to execute it.

<!-- Authoring notes for the agent. Delete every comment when filling the template; follow references/contract-writing-rules.md. -->

## Blocking inputs

- **⟨Decision to confirm⟩:** ⟨value, options, or unresolved condition⟩.
- **⟨Proposed threshold⟩:** ⟨value and what it controls⟩.
- **⟨Scope, time or permissions⟩:** ⟨anything the approver must explicitly accept⟩.

<!-- One bullet per open item: every required field and every value the user hasn't confirmed. Remove the section if nothing is open beyond the status change. -->

## 1. The question

**⟨One sentence: what are we trying to find out? Phrase it so both possible answers are visible.⟩**

⟨One or two sentences: why the experiment is needed and what current evidence can't establish.⟩

### Test configurations

| Configuration | Key difference | Purpose |
|---|---|---|
| **⟨Descriptive name⟩ (⟨code⟩)** | ⟨relevant setting⟩ | Baseline |
| **⟨Descriptive name⟩ (⟨code⟩)** | ⟨relevant setting⟩ | Candidate |
| **⟨Descriptive name⟩ (⟨code⟩)** | ⟨relevant setting⟩ | Only if ⟨trigger⟩ |

<!-- Full parameter values go here only when approval depends on the values themselves. Otherwise link to the runbook's arm setup. -->

### Workloads

| Workload | What runs | Execution | Expected samples |
|---|---|---|---:|
| **⟨Descriptive name⟩** | ⟨brief scenario; link to script⟩ | ⟨Scripted / Agent-driven (pacing not controlled)⟩ | ⟨n⟩ |

### Run schedule and estimated duration

| Step | Configuration / action | Estimate |
|---|---|---:|
| **Preparation** | ⟨set up data and environment, confirm access⟩ | ⟨range⟩ |
| **Rehearsal (R0)** | ⟨configuration⟩: verify scripts, collection and prerequisites; not counted | ⟨range⟩ |
| **⟨Stage 1⟩ (R1–Rn)** | **R1:** ⟨configuration (code)⟩ → **R2:** ⟨configuration (code)⟩ → … | ⟨range⟩ |
| **⟨Stage 1 decision⟩** | Stop if ⟨specific condition⟩; otherwise continue | Included above |
| **⟨Optional tests⟩** | ⟨configuration, trigger and number of runs⟩ | ⟨range, conditional⟩ |
| **Analysis and results** | ⟨decode, compare, links, cleanup, report⟩ | ⟨range⟩ |

<!-- Drop stage, decision and optional rows the run doesn't have. With one unit per configuration there is usually a single "Measured runs" row. -->

**Total:** ⟨range per ending: stopped early / full / with optional branch⟩. ⟨What's excluded, such as waiting for sign-in or approvals.⟩

⟨One sentence on why the run order protects validity, only if the order was chosen for that.⟩

**Evidence limits:** ⟨what each stage's sample can support. With one run per configuration: "a **reproduction**, not a measured benchmark; timing differences are preliminary and reported with within-run variation, not ratios." Name what isn't planned (A/A test, warm-ups) and comparisons that must never be made.⟩

**Time guard:** ⟨after the rehearsal the estimate is redone from its measured time; stop before the next measured run if the projection exceeds the applicable upper estimate or the deadline ⟨date UTC⟩.⟩

## 2. Verdict / decision rule

⟨Define the one or two measurements the rules depend on, with everyday labels first.⟩

| Observation | Decision |
|---|---|
| ⟨condition for early stop⟩ | ⟨conclusion; whether later stages are skipped⟩ |
| ⟨condition for a measured change, with threshold and noise check⟩ | ⟨how to report it⟩ |
| ⟨condition for optional follow-up⟩ | ⟨what gets tested next; who chooses the final setting⟩ |
| Difference within measurement precision | **No measurable difference at this precision.** |
| ⟨Primary and cross-check workloads disagree⟩ | Report both; **no verdict.** |
| Correctness check fails | **Fail**; no passing result is claimed. |
| ⟨Invalid or insufficient results⟩ | No verdict for that configuration; explain why. |

**Measurement precision:** ⟨how variation is estimated (A/A spread, range of per-run medians, or within-run spread) and what small samples can't establish⟩.  
**Approval status:** ⟨"thresholds confirmed on ⟨date⟩" or "⟨thresholds⟩ proposed, awaiting approval"⟩.

## 3. What is measured

| Category | Measurements | Purpose |
|---|---|---|
| **⟨Primary workload⟩** | ⟨count, duration percentiles, relevant internal timing⟩ | Main comparison |
| **⟨Decision input⟩** | ⟨metric used by a stop or branch rule⟩ | ⟨which rule⟩ |
| **⟨Secondary workload⟩** | ⟨metrics⟩ | Regression check |
| **Measurement source** | ⟨capture per run, and any approximation⟩ | Traceability |
| **Resource use (context only)** | ⟨CPU, memory, threads⟩ | Interpretation, not verdict |

**Excluded:** ⟨meaningful exclusions only: mechanism verification (default), declined captures, out-of-scope decisions⟩.

## 4. Environment and controls

| Item | Setup / control |
|---|---|
| **Target** | ⟨instance or environment, and one line on topology: same instance with a switch / separate instances / redeploys⟩ |
| **Build** | ⟨build or commit link, and the commit that contains the change⟩ |
| **Data** | ⟨fixed dataset and prerequisites; how it differs from real use if that matters⟩ |
| **Configuration changes** | ⟨how configurations switch, what stays unchanged, what is verified per run⟩ |
| **Access the agent has** | ⟨tunnels, credentials by name, tools the agent may use, or "none needed"⟩ |
| **Shared or uncontrolled conditions** | ⟨known sources of variance and mitigation; recorded is not controlled⟩ |
| **Deadline** | ⟨environment expiry in UTC, if relevant; mark unverified timing⟩ |

⟨One sentence linking exact names, provenance checks and setup procedures to the [agent runbook](benchmark-agent-runbook.md).⟩

## 5. Validity and limitations

**Repeat or reject a run if:**
- ⟨objective invalidation condition⟩.

**Rehearsal requirements:**
- ⟨what must be verified before measured runs, and what failing it means⟩.

**Limitations:**
- ⟨uncontrolled factors or uncertainty⟩.
- ⟨what the measurements do not mean⟩.

## 6. Deliverables and authorization

**Deliverables:**
- ⟨results document and structured outputs⟩.
- Verdict against section 2, actual versus estimated duration, and a source for every figure.

**Human actions:**
- Approve this contract ⟨and the specific proposed values listed in Blocking inputs⟩.
- ⟨Sign-ins, downloads or other authorizations, with when they are needed⟩.

**Permission boundary:**
- ⟨allowed environment and actions⟩.
- ⟨explicitly prohibited actions⟩.
- The [agent runbook](benchmark-agent-runbook.md) has the full execution permissions.
