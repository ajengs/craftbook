---
name: benchmark-designer
description: Design and run a benchmark from one standard template. Draft turns a short intake (what is compared, where, what the user provides) into two documents, a contract the user approves (question, configurations, workloads, decision rule, measurements, validity, schedule) and an agent runbook that executes it. Run executes the runbook once the contract is approved. Use for "design a benchmark", "A/B this change", "benchmark A vs B", "write a benchmark contract", "is this faster with X on", "run the benchmark in <contract path>". Works for any stack.
argument-hint: "[draft | run <contract or runbook path>] [id] [anything already known]"
---

# Benchmark designer

One template for every benchmark. The user supplies only what has no sensible default. The agent fills the rest and writes two documents: the **contract** (intent and verdict rules the user approves) and the **agent runbook** (operations that never reinterpret the contract). Nothing runs while a required field is blank.

`<skill-dir>` is the folder holding this file.

| File | When |
|---|---|
| `templates/benchmark-contract.md` | Draft: the approval contract |
| `templates/benchmark-agent-runbook.md` | Draft: the operations document |
| `references/contract-writing-rules.md` | Draft step 5: how to write the contract, and the final checklist |

## Modes

- **Draft** (default): intake, defaults, contract and runbook, then the user reviews. Draft never touches the system under test.
- **Run**: given a contract or runbook path, execute the runbook. Refuse unless the contract's status is `approved`, it has no Blocking inputs or values marked proposed, and the runbook has no unfilled required fields or unconfirmed value sources. Run reads only the approved local markdown contract: a contract that exists only as a review document is not approved yet.

A request that names a contract or runbook file is Run. Anything else is Draft.

## Three rules behind every value

**1. Every value carries its source.** Track a tag per value in the runbook: `[user]` (the user stated it), `[context: <where>]` (from a ticket, notes or the conversation; becomes `[user]` once confirmed), `[default]` (a default from this skill), `[proposal]` (anything the agent came up with). The contract carries no tags: confirmed values are stated plainly, unconfirmed ones are marked **proposed** and listed under Blocking inputs, and each contract value's tag goes in the runbook's Contract value sources table. A proposal is never written as the user's decision. Picking an option confirms only what the option is called, and silence confirms nothing.

**2. Defaults never add work.** Defaults are the minimum that answers the question: 1 unit per arm, only the phases the scenarios need, only the captures the outputs need. Anything that adds units, phases, warm-ups, gates or captures is an **offer** with its cost, and is left out unless the user says yes. Ask for numbers as numbers. Never adopt a number or threshold from another plan as a default.

**3. Changes carry reasons.** When the user changes a field, re-check every field that depends on it and update the ones that follow mechanically. Don't reword a user-confirmed field yourself: propose the change, mark it proposed, and say which edit made it necessary. Simplifying wording never changes a decision.

## Draft

### 1. Intake: propose from context, confirm, ask only for gaps

Harvest the conversation first, then any ticket, notes or earlier plan. A decision already made in the session is a **proposed value**, not a question. A rejected option stays rejected. Then send **one message** with three parts: **Proposed from context** (each field you could fill, with its source), **Agent proposals** (values nobody stated, marked as yours), and **Still needed** (only fields with no value anywhere, plus offers with their cost). Never silently promote a guess to a proposed value.

| # | Field | Why there's no default |
|---|---|---|
| I1 | **Question and decision rule:** what result changes what decision ("C is at least 15% faster on S2, so ship it; within noise, drop it") | Without it, "passing" means nothing |
| I2 | **Arms:** what differs between them (build, parameter, flag, configuration) and the value per arm | It is the variable under test |
| I3 | **Target:** the instance, environment or build to run against | Only the user knows what is safe to load |
| I4 | **Access the user provides:** credential environment variable **names** (never values), sign-ins, dashboards | The agent must not set these up itself |
| I5 | **Workload intent:** what traffic or work matters and roughly how hard | It picks the scenarios |
| I6 | **Id and output folder:** where documents and run folders go (default `benchmarks/<id>/` in the working folder) | Where results live |
| I7 | **Mechanism verification: out by default. Include any?** | Explaining *why* costs run time and can perturb the numbers. Only the user can trade that off |

Also ask the **code-location question** when I2 is a flag or parameter: which process runs the code under test, and does the switch reach it? It decides how arms are switched.

**Output capture vs mechanism verification.** An output capture (a recording, trace or log needed to measure or verify an output) belongs in the measurement plan, runs in every counted unit on every arm, and needs no extra confirmation. Mechanism verification (call trees, per-step breakdowns, wait analysis) explains *why* an output moved. It is out by default and added only if the user says yes at I7, with specific suggestions: what it would show, how it is captured, what it costs. Opted-in mechanism work that the outputs don't need runs in its own phases, on every arm, and only explains the verdict.

**Review format.** One line, default named: **review document only** (the draft contract is a commentable document the user reads and comments on, and the local markdown is written once approved), **review document plus local draft**, or **local markdown only**. If the environment has no commentable document system, say so and use local markdown.

### 2. Apply the defaults

Write the chosen value into the document it belongs to, with a short reason where the reason affects approval, so the user can veto it in review.

- **Topology.** Arms that differ only by a switch that reaches every process under test run on **one instance**, in order (interleaved if repetitions are asked for). Arms that are different builds run on **separate instances** of the same size and data, and every difference between the sides is recorded, not claimed controlled. If one arm's workload changes data the other reads, use separate instances or a reset between arms. If only one instance exists for different builds, mark the result **low confidence**. Never use a shared instance when the switch would change behavior for other users: ask for a dedicated one.
- **Switching arms.** One configuration per arm, set before the run and never changed during it. A change mid-phase makes the configuration an untracked variable.
- **Run shape.** Default **1 unit per arm**, no warm-up, no A/A gate. A unit is a batch, a round, an iteration or a fixed-duration window. With n = 1 the result is a **reproduction**: report per-arm numbers and the within-unit spread, call a difference only if it is large against that spread, and don't report ratios as benchmark results. When the user asks for repetitions, interleave arms (`A B A B`), and report the median with range for n < 10, or with IQR for n of 10 or more; latencies get p50/p95/p99 pooled per arm. An **A/A gate** (same arm twice before any A/B) gives the noise floor, and is worth suggesting on noisy environments, but it is the user's call.
- **Measurements: outputs first.** Defaults: end-to-end latency including queue wait (p50/p95/p99), successful-operations throughput, completion time for async work, errors by class, and correctness parity where arms could produce different data. Resource use (CPU, memory) is context, not a verdict.
- **Passing criteria.** Testable rules, not adjectives. Pass or fail is the decision rule from I1 applied to the per-arm numbers, against the A/A spread if one ran, otherwise the spread within each unit. Correctness: zero unexplained parity mismatches, and any mismatch fails the arm. **Invalid run** (discard, don't count as a fail): a restart or eviction during the phase, a deploy or configuration change during the phase, a failed arm check, an error rate above the contract's threshold, saturation from neighbours, or a lost capture.
- **Guardrails.** Copy the runbook template's guardrails, then add run-specific "never touch" entries.
- **Artifacts.** Per phase: run log, raw measurements (CSV or JSON), environment printout, links scoped to the phase window.
- **Duration estimate.** Fill the contract's schedule table with a low–high range per step: preparation, rehearsal, measured runs, analysis and teardown. Put the basis of each estimate in the runbook (the user, a previous run's ledger, or an explicit proposal; never present an assumption as a measurement). Give one total range per possible ending, name what waiting on the user is excluded, and add a **time guard** against any known deadline. The total is a proposal unless the user gave it. Re-estimate when the run shape changes.

### 3. Map scenarios to tools

Use tools the user already has before writing new scripts. Every workload says whether it is **scripted** (requests, order, count and pacing fixed in code, so every arm runs the same thing) or **agent-driven** (the agent follows steps, so the steps can match across arms but the execution can't). A measured workload whose decision rule depends on pacing, concurrency, request count or end-to-end duration must be scripted. Agent-driven fits single-user timings and unmeasured setup, and its label says "pacing not controlled". Add a response check to any replayed request, because status alone doesn't show the arm produced the right result. A script written for a step no tool covers is listed in the runbook's tooling table with its state (`exists`, `written, never run`, `rehearsed`).

Picking scenarios: start from the decision rule and cut any scenario that can't change the verdict. Include one where the candidate **should** win clearly (it validates the setup), one where it **should** be neutral (it catches regressions behind the headline), and an idle scenario when the change touches background work. For async work the output is completion time for a fixed amount of work, not per-step timings.

### 4. Find gaps before the user does

Go through the known traps of the chosen environment: shared neighbours, expiry or deadlines, cold caches, first-visit prompts, rate limits, data growth between arms. Each trap that applies becomes a **preflight check** (verifiable now), an **open item** (what resolves it), or a **blocker** (stops the run, with the fallback named). Anything that needs the user (a build, a sign-in, an activation) goes under "What the user provides", with **when** it is needed.

### 5. Write the contract and the runbook

- The runbook is always local markdown, from `templates/benchmark-agent-runbook.md`.
- The contract follows the review format chosen in step 1. For a review document, titled `<id> Benchmark Contract`, put the template's Status line in the body, and write links to sibling files as full paths in code, because relative links don't resolve there.
- **Existing documents.** A contract already `approved` is never touched: write the new pair as the next free `-vN`. An unapproved draft is updated in place, keeping the user's edits and comments. A big rewrite of an unapproved draft (a different question, configurations or decision rule) is the next `-vN`; if unclear whether a change is big, ask.
- **Write the contract for a human approver**, following `references/contract-writing-rules.md`, and run its final checklist before handing back.
- **What goes where.** The contract holds what could change the approval decision, the reading of results, the safety boundary or the expected time. The runbook holds the how: readiness, value sources, preflight, stop conditions, arm setup, per-unit steps, artifacts, tooling, permissions, teardown, ledger, results order. A decision is stated once, in the contract.
- **Consistency.** Numbers in both documents match, preflight and gap ids are numbered without gaps, a prohibition under Never never also appears under Ask, and the contract's status is authoritative.
- Each output gets a noise reference that fits it: a request-level spread doesn't apply to a batch-level duration.
- Re-list the folder right before writing, since a parallel session may write there.
- Fill every section. List every open item and every proposal under the contract's **Blocking inputs**. Write every script before hand-back, with state `written, never run`. Set both statuses to `draft`.

### 6. Hand back

Reply with the contract's link or path and the runbook path, the estimated total (range, plus what it waits on from the user), the blocking inputs, and the two or three defaults most likely to be vetoed. Don't paste the documents. When the user changes something, apply rule 3 before replying. Edits the user made in the review document are theirs: read its changes before every edit and never overwrite them.

### 7. Approval

When the user approves:
1. Re-read the whole review document, including edits and open comment threads. An open thread asking for a change is unresolved: ask first.
2. Apply the consistency checks and the final checklist. Anything still proposed or under Blocking inputs blocks approval: say what, and stop.
3. Set the status to `approved` with the user's name and date.
4. Write the document's content to the local `benchmark-contract.md` (or its `-vN`) in the output folder, restoring relative links, and mirror the status in the runbook. Overwrite a local draft only from the document, never by hand-merging.
5. Reply with the local path. From now on the contract changes only as a new `-vN` with a fresh approval.

With local markdown only, approval is steps 2, 3 and the runbook mirror in the file.

## Run

1. **Read both documents fully.** Refuse and list what's missing if the contract isn't approved, still has Blocking inputs or proposed values, or the runbook has required fields, proposal-tagged values, or a tooling row still `to write`.
2. **Preflight.** Run every check in the runbook's checklist. Any failure means stop and report; don't improvise around it.
3. **Rehearse** one short phase of the first scenario in the first arm. Check that every artifact listed for the phase lands, fix scripts in place, note each fix in the ledger, and set the scripts' state to `rehearsed`. Then **re-project the duration** from the measured time. If it exceeds the contract's upper bound or the deadline, stop and report before the first counted unit.
4. **A/A gate**, if the contract has one. If the spread is at least the smallest effect the decision rule cares about, stop and report: that is a finding, not a failure to retry.
5. **Phases** in the runbook's order. After each: run the arm check, apply the invalid-run rules, check parity, and update the **run ledger** (phase, arm, UTC window, duration, valid, artifacts path, notes). Every phase gets a ledger row, including waiting on the user. Record timestamps as they happen, never reconstructed.
6. **Teardown**: everything in the runbook's list. Revert any switch the agent made, and ask before deleting test data.
7. **Results**: write `benchmark-results-<round>.md` next to the contract, in the runbook's results order: verdict against the decision rule (labelled a reproduction when n = 1), per-scenario numbers, parity, invalid runs and why, what wasn't measured, and the run duration (estimate vs actual, active vs waiting). Every number gets its source. Mechanism claims are hypotheses unless a capture shows them.

**Stop and ask** when a guardrail would be crossed, a preflight check fails, the A/A gate fails, an arm check fails twice, a deadline will pass before the run order finishes, elapsed or projected time passes the contract's upper bound, or a step needs a user-owned action. **Proceed and log** for everything else: a single invalid run, a script bug fixed in place, a recovery the runbook describes.

## Rules in both modes

- Reproduction is not a benchmark. A run with n = 1 per arm, or without interleaving, is labelled a reproduction, and its exact ratios aren't reported as benchmark results. That is a label, not a reason to add repetitions the user didn't ask for.
- Change one variable per comparison.
- Count attempted and successful operations separately, so failing arms don't look cheaper.
- Fail loudly on unexpected exceptions. Never fold them into an expected error class.
- Never print, log or write a secret. Credentials come from environment variables the user named.
- Never queue builds or pipeline runs, deploy, activate or change shared configuration, write to repositories or pull requests, or run unscoped test suites, unless the contract or the user explicitly says to.
