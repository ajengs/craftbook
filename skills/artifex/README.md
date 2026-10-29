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

One umbrella session coordinates six phases:

| Phase                  | What happens                                                                                                     |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------- |
| P1 research            | Frame the problem with you. Review and approve a kickoff, then either an analysis and milestone or the scoped small task |
| P2 analysis            | Review and approve specs, write the implementation handoff for P3, then continue with the verification contract and handoff |
| P3 implementation      | Starts automatically from the complete P2 checkpoint; implements, opens the PR, and follows CI and review feedback |
| P4 review              | An independent sub agent reviews the PR, up to 3 rounds, then escalates                                          |
| P5 auto verification   | Runs the contract's auto scenarios right after review passes, when there are any                                 |
| P6 manual verification | Runs the contract's manual scenarios on your trigger, when there are any                                         |

Approvals are tied to a specific revision of a specific artifact. Closing a milestone always needs your explicit sign-off.

## Not a harness

This package can't spawn agents, lock files, ensure atomic writes, enforce approvals or isolate worktrees. The umbrella coordinates those only where the environment provides tooling. Approval records in files are evidence, not access controls.

## Layout

| Folder        | What it holds                                                                           |
| ------------- | --------------------------------------------------------------------------------------- |
| `policies/`   | What must be respected: authority, scope, approvals, internal codes, evidence integrity |
| `standards/`  | How work and artifacts are produced: design, specifications, evidence, PR feedback      |
| `workflows/`  | One procedure per phase                                                                 |
| `templates/`  | Starting points for each artifact                                                       |
| `references/` | Optional extras, such as a remote status page                                           |

## Optional tools

Workflows name tools by capability and `SKILL.md` binds each one, with a fallback when it isn't installed: a benchmark designer, a handoff writer and a PR feedback handler.

## Out of scope for now

Detailed code-review policy, automated approval gates, locking and agent orchestration, and delivery (merging, deployment, backports) unless separately authorized.
