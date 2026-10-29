# Implementation handoff — <milestone>

Approved specs: <path@revision>
Branch: <branch name the session works on>
Run by: a dedicated P3 phase session using the `artifex` skill and `workflows/P3-implementation.md`; that session spawns its own isolated implementation subagent.
Implementation subagent model / agent type: <strongest available model>; <agent type limited to the tools this work needs, or the default>
Session name: `<ticket id> P3 implementation <additional context if any>`

## Objective and agreed approach

## Relevant components / locations

## Scope boundaries, exclusions and constraints

## Required checks and expected deliverable

## Settled decisions / unresolved blockers
Every choice that would change the code's shape if reopened: test approach, test data format and size, file layout, how the work splits into PRs. Don't build an alternative to a settled decision; ask through the umbrella.

## Implementation rules
- Don't run a failing test before the change.
- First add any missing tests that preserve or guard existing behavior. Make sure they pass. Commit.
- Then make the change in a separate commit containing the proposed changes and their tests.
- Write no comments. If context is absolutely necessary, add the why in at most 3 lines.
- Keep command output small: use the project's quiet build mode, scope test runs with a filter, write full logs to a file and read only the failures or the summary, check `git diff --stat` before reading a full diff, and never print large generated files. Every later call re-reads what you print.
- Internal codes (Artifex ids like SPEC- and VER-, phase codes, any other code coined in sessions) stay in notes. Don't put them in code, tests, commits, PRs or ticket comments; describe the behavior in words.
- You may run build, test, commit, push and open pull requests. Merging, deploying and backporting are not covered.

New design decisions during P3 go to user. This handoff has no approval step of its own: approval of the referenced specs authorizes its creation.
