---
auto: <[scenario ids marked auto], or []>
manual: <[scenario ids marked manual], or []>
---
# Verification handoff — <milestone>

The frontmatter is read by the router (`references/orchestration.md`, Handoff frontmatter) and must match the scenario sections below.

Approved specs: <path@revision>
Approved verification contract: <path@revision>
Known tradeoffs and limitations: <path to `tradeoffs.md`>. Behavior inside a row's boundary that no scenario's pass condition covers is reported as known, not as a failure. Outside the boundary it is a finding. A row never relaxes a pass condition.
Branch / PR: <given by the umbrella when it starts you>
Run by: an isolated phase worker of the umbrella session, using the `artifex` skill. P5 auto verification (`workflows/P5-verification.md`) runs the auto scenarios. P6 manual verification (`workflows/P6-manual-verification.md`) runs the manual ones, on the user's trigger.
Model / effort: <resolved selection from `SKILL.md`, Model allocation; separate reviewer selection if included; P6 selection when applicable; any override and reason>
Execution: <independent phase chat on Codex; isolated worker on other hosts>
Role configuration: <model/effort reference; not a native agent-type selection for a Codex chat>
Session name: `<ticket id> P5 auto verification <additional context if any>` or `<ticket id> P6 manual verification <additional context if any>`

## Auto scenarios (P5)
Contract scenarios marked auto, functional and benchmark. Leave empty if there are none: P5 is then not applicable.

## Manual scenarios (P6)
Contract scenarios marked manual, functional and benchmark. Leave empty if there are none: P6 is then not applicable. They run only on the user's explicit trigger. A benchmark runs through the benchmark designer, and its session adds the harness it needs.

## How to verify
Prefer extended integration tests that run without running the app. Add explicit integration tests where a scenario needs one. Use the running app only when a scenario can't be checked otherwise.

## Where tests go
By default, commit added integration tests on the PR's branch. Do this only once the umbrella confirms that no implementation worker is active on the PR's branch. If implementation work is active, stop and tell the umbrella; that is handled manually. Notify the umbrella of any push.

## Evidence and reporting
Raw output goes in the `evidence_dir` the umbrella gives when it starts you (`evidence/<run id>/` in the milestone folder), never in `results/`, which holds only result files. Name anything that must go elsewhere, such as a benchmark's own output folder. Report results, limitations and any spec or contract change you think is needed to the umbrella. Do not change the specs or the contract yourself. End by writing the result file to the given `result_path`, with an outcome for every assigned scenario, and report the finalized path as `references/orchestration.md`, Result delivery describes (`references/orchestration.md`, Result file).

## Rules
- Write no comments in test code. If context is absolutely necessary, add the why in at most 3 lines.
- Follow `SKILL.md`, Execution efficiency, for context, tool output and session transitions, and `policies/core.md`, Autonomous execution, for debugging and escalation.
- Add tests only. Never change production code. A test that fails against the PR is a finding: run it, report it to the umbrella, and don't fix it here.
- Internal codes (Artifex ids like SPEC- and VER-, phase codes, any other code coined in sessions) stay in notes. Don't put them in test names, code, commits, PRs or ticket comments; describe the behavior in words.
- You may run build, test, commit and push on the PR's branch, as the user's `delivery_authorization` in your assigned inputs grants, once the umbrella confirms that no implementation worker is active on it. Don't open or merge a PR, deploy or backport.
