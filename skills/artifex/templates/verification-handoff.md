---
auto_agent: <[auto agent run scenario ids], or []>
manual_agent: <[manual agent run scenario ids], or []>
manual_user: <[manual user run scenario ids], or []>
---
# Verification handoff — <milestone>

The frontmatter is read by the router (`references/orchestration.md`, Handoff frontmatter) and must match the scenario sections below.

Approved specs: <path@revision>
Approved verification contract: <path@revision>
Branch / PR: <given by the umbrella when it starts you>
Run by: an isolated sub agent of the umbrella session, using the `artifex` skill. P5 auto verification (`workflows/P5-verification.md`) runs the auto agent scenarios. P6 manual verification (`workflows/P6-manual-verification.md`) runs manual agent and manual user scenarios, on the user's trigger.
Model / effort: <resolved selection from `SKILL.md`, Model allocation; separate reviewer selection if included; P6 selection when applicable; any override and reason>
Agent type: <native configured type matching the selection, or the default; limit tools when supported>
Session name: `<ticket id> P5 auto verification <additional context if any>` or `<ticket id> P6 manual verification <additional context if any>`

## Auto agent runs (P5)
Scenario IDs from `auto_agent`. Start automatically after passing P4 and ready approved inputs.

## Manual agent runs (P6)
Scenario IDs from `manual_agent`. Start only on the user's explicit trigger; the agent executes the entire run. Do not ask the user to operate the app or collect its evidence.

## Manual user runs (P6)
Scenario IDs from `manual_user`. Start only on the user's explicit trigger. Name agent preparation, exact user interactions, resume signal, evidence source and acceptance check. The agent pauses at those interactions; never invent a user action or observation.

## Run tools, readiness and collection plan
Copy the approved contract's per-run tool/evidence plan by reference and supply execution details: approved pinned catalog source/path/full SHA-256 (check it at execution; do not rediscover), exact skill paths or tool names, target environment, commands or invocation references, setup and collector start/stop timing, output paths, and cleanup. Carry every required/optional artifact, its purpose, readiness evidence, unresolved gap and owner. See `references/verification-tools.md`. Recheck readiness before execution; a material substitution changes the contract and needs approval.

## How to verify
Prefer extended integration tests that run without running the app. Add explicit integration tests where a scenario needs one. Use the running app only when a scenario can't be checked otherwise.

## Where tests go
By default, commit added integration tests on the PR's branch. Do this only once the umbrella confirms that no implementation sub agent is active on the PR's branch. If implementation work is active, stop and tell the umbrella; that is handled manually. Notify the umbrella of any push.

## Evidence and reporting
Raw output goes in the `evidence_dir` the umbrella gives when it starts you (`evidence/<run id>/` in the milestone folder), never in `results/`, which holds only result files. Name anything that must go elsewhere, such as a benchmark's own output folder. Report results, limitations and any spec or contract change you think is needed to the umbrella. Do not change the specs or the contract yourself. End by writing the result file to the given `result_path`, with an outcome for every assigned scenario, and return only that path (`references/orchestration.md`, Result file).

## Rules
- Write no comments in test code. If context is absolutely necessary, add the why in at most 3 lines.
- Follow `SKILL.md`, Execution efficiency, for context, tool output and session transitions, and `policies/core.md`, Autonomous execution, for debugging and escalation.
- Add tests only. Never change production code. A test that fails against the PR is a finding: run it, report it to the umbrella, and don't fix it here.
- Internal codes (Artifex ids like SPEC- and VER-, phase codes, any other code coined in sessions) stay in notes. Don't put them in test names, code, commits, PRs or ticket comments; describe the behavior in words.
- You may run build, test, commit and push on the PR's branch, as the user's `delivery_authorization` in your spawn inputs grants, once the umbrella confirms that no implementation sub agent is active on it. Don't open or merge a PR, deploy or backport.
