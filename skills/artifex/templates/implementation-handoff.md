# Implementation handoff — <milestone>

Approved specs: <path@revision>
Branch: <branch name the session works on>
Run by: a dedicated P3 phase session using the `artifex` skill and `workflows/P3-implementation.md`; that session spawns its own isolated implementation subagent.
P3 session and isolated worker model / effort: <resolved selections from `SKILL.md`, Model allocation; any override and reason>
Agent type: <native configured type matching the selection, or the default; limit tools when supported>
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
- Follow `SKILL.md`, Execution efficiency, for context, tool output and session transitions, and `policies/core.md`, Autonomous execution, for debugging and escalation.
- Internal codes (Artifex ids like SPEC- and VER-, phase codes, any other code coined in sessions) stay in notes. Don't put them in code, tests, commits, PRs or ticket comments; describe the behavior in words.
- You may run build, test, commit, push and open pull requests. Merging, deploying and backporting are not covered.

New design decisions during P3 go to user. This handoff has no approval step of its own: approval of the referenced specs authorizes its creation.
