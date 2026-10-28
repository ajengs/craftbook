# Implementation handoff — <milestone>

Approved specs: <path@revision>
Approved verification contract: <path@revision>
Branch: <branch name the session works on>
Run by: an isolated sub agent of the umbrella session, using the `artifex` skill, implementation role, `workflows/P3-implementation.md`.
Session name: `<ticket id> P3 implementation <additional context if any>`

## Objective and agreed approach

## Relevant components / locations

## Scope boundaries, exclusions and constraints

## Required checks and expected deliverable

## Settled decisions / unresolved blockers

## Implementation rules
- Don't run a failing test before the change.
- First add any missing tests that preserve or guard existing behavior. Make sure they pass. Commit.
- Then make the change in a separate commit containing the proposed changes and their tests.
- Write no comments. If context is absolutely necessary, add the why in at most 3 lines.
- Internal codes (Artifex ids like SPEC- and VER-, phase codes, any other code coined in sessions) stay in notes. Don't put them in code, tests, commits, PRs or ticket comments; describe the behavior in words.
- You may run build, test, commit, push and open pull requests. Merging, deploying and backporting are not covered.

New design decisions during P3 go to user. This handoff has no approval step of its own: the user's request to write it is the approval of the current specs and contract revisions.
