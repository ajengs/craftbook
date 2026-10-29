# Verification handoff — <milestone>

Approved specs: <path@revision>
Approved verification contract: <path@revision>
Branch / PR: <given by the umbrella when it starts you>
Run by: an isolated sub agent of the umbrella session, using the `artifex` skill. P5 auto verification (`workflows/P5-verification.md`) runs the auto scenarios. P6 manual verification (`workflows/P6-manual-verification.md`) runs the manual ones, on the user's trigger.
Model / agent type: <a cheaper model to run the scenarios; the strongest available model if the full PR review is included>; <agent type limited to the tools the run needs, or the default>
Session name: `<ticket id> P5 auto verification <additional context if any>` or `<ticket id> P6 manual verification <additional context if any>`

## Auto scenarios (P5)
Contract scenarios marked auto, functional and benchmark. Leave empty if there are none: P5 is then not applicable.

## Manual scenarios (P6)
Contract scenarios marked manual, functional and benchmark. Leave empty if there are none: P6 is then not applicable. They run only on the user's explicit trigger. A benchmark runs through the benchmark designer, and its session adds the harness it needs.

## How to verify
Prefer extended integration tests that run without running the app. Add explicit integration tests where a scenario needs one. Use the running app only when a scenario can't be checked otherwise.

## Where tests go
By default, commit added integration tests on the PR's branch. Do this only once the umbrella confirms that the P3 session has no active implementation subagent making changes. If implementation work is active, stop and tell the umbrella; that is handled manually. Notify the umbrella of any push.

## Evidence and reporting
Where raw output goes. Report results, limitations and any spec or contract change you think is needed to the umbrella. Do not change the specs or the contract yourself.

## Rules
- Write no comments in test code. If context is absolutely necessary, add the why in at most 3 lines.
- Keep command output small: use the project's quiet build mode, scope test runs with a filter, write full logs to a file and read only the failures or the summary, and never print large generated files. Every later call re-reads what you print.
- Add tests only. Never change production code. A test that fails against the PR is a finding: run it, report it to the umbrella, and don't fix it here.
- Internal codes (Artifex ids like SPEC- and VER-, phase codes, any other code coined in sessions) stay in notes. Don't put them in test names, code, commits, PRs or ticket comments; describe the behavior in words.
- You may run build, test, commit and push on the PR's branch once the umbrella confirms that the P3 session has no active implementation subagent making changes. Don't open or merge a PR, deploy or backport.
