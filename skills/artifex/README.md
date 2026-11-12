# Artifex

A user-led engineering workflow for larger changes. It is instruction-first and portable: copy this folder into your agent's skills directory and start from `SKILL.md`. The environment must be able to read project files. No particular model or agent tool is required.

> *[Artifex](https://en.wiktionary.org/wiki/artifex)* is Latin for craftsperson, artisan, or maker.
> 
> The name reflects the philosophy behind this framework: **engineering is a craft that requires deliberate thinking, sound judgment, and discipline.**
> 
> Artifex aims to make engineering practices repeatable and reliable through structured workflows, clear boundaries, and automation—without replacing the human judgment behind them.
> 
> **Automate the mechanics. Preserve the craftsmanship.**

## What it covers

One umbrella session coordinates six phases, plus a bug track. The invocation picks where it starts: `artifex_state.py route` reads the mode (`project`, `milestone`, `defect` or `implementation`) and prints the start, or recommends a mode when the invocation names none:

| Phase                  | What happens                                                                                                     |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------- |
| P1 research            | Frame the problem with you. Review and approve a kickoff, then either an analysis and milestone or the scoped small task |
| P2 analysis            | Review and approve specs, record the tradeoffs and limitations you accept in a living register, write the implementation handoff for P3, then continue with the verification contract and handoff |
| P3 implementation      | An isolated sub agent, started by the umbrella from each handoff, opens the PR; the umbrella follows CI and review feedback |
| P4 review              | An independent sub agent reviews the PR, up to 3 rounds, then escalates                                          |
| P5 auto verification   | Runs the contract's auto scenarios right after review passes, when there are any                                 |
| P6 manual verification | Runs the contract's manual scenarios on your trigger, when there are any                                         |
| D1 bug investigation | For a bug ticket (`defect` mode) or a major P5 finding, in place of P1 and P2: reproduce, find the root cause, then fix directly or after you approve the cause and the fix. P3 to P6 follow; a fix that needs design can go to P2 |

`milestone` mode starts at P2 from a scope you give as a file, a link or a description. `implementation` mode starts at the router when you supply the specs, the verification contract and both handoffs, and at a short P2 when you supply some of them or only context.

Several P2 sessions can be active at once, one per milestone or ad hoc analysis. Each hands its work to the umbrella, which runs the implementation and verification sub agents.

Approvals are tied to a specific revision of a specific artifact. Closing a milestone always needs your explicit sign-off.

The tradeoffs register (`tradeoffs.md`) is the exception to revision-bound artifacts: it records each accepted or deferred tradeoff with its consequence, severity, rationale, a decision log and the boundary at which the behavior is still a defect. Reviewers and verifiers use that boundary to separate known limitations from real defects, and you see the open rows when you sign off.

## Not a harness

This package can't spawn agents, lock files, ensure atomic writes, enforce approvals or isolate worktrees. The umbrella coordinates those only where the environment provides tooling. Approval records in files are evidence, not access controls.

One deterministic piece is included: `scripts/artifex_flow.py`, a router for the P3–P6 loop. It decides what runs next, applies the review and rework caps, classifies pushes from git and checks each agent's result against its artifacts before acting on it. The umbrella carries out its actions and handles only the exceptions it raises. It needs Python 3.10+ and git 2.36+, and has no other dependencies. See `references/orchestration.md`. Beside it, `scripts/artifex_state.py` keeps the umbrella's structured state in `state.json` and renders a `STATE.md` only when the user asks (`references/state.md`). `scripts/artifex_cost.py` reports a milestone's token cost from Claude Code or Codex transcripts. Tests run with `python -m unittest test_artifex_flow test_artifex_state test_artifex_cost` from `scripts/`.

## Layout

| Folder        | What it holds                                                                           |
| ------------- | --------------------------------------------------------------------------------------- |
| `policies/`   | What must be respected: authority, scope, approvals, internal codes, evidence integrity |
| `standards/`  | How work and artifacts are produced: design, specifications, evidence, PR feedback      |
| `workflows/`  | One procedure per phase                                                                 |
| `templates/`  | Starting points for each artifact                                                       |
| `references/` | Optional extras, such as a remote status page, and the router reference                 |
| `scripts/`    | The P3–P6 router, the state store, and their tests                                      |

## Optional tools

Workflows name tools by capability and `SKILL.md` binds each one, with a fallback when it isn't installed: a benchmark designer, a handoff writer and a PR feedback handler.

## Out of scope for now

Detailed code-review policy, automated approval gates, locking, a headless driver that launches agents itself, and delivery (merging, deployment, backports) unless separately authorized.
