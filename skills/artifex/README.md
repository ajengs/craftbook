# Artifex

A user-led engineering workflow for larger changes. It is instruction-first and portable: copy this folder into your agent's skills directory and start from `SKILL.md`. The environment must be able to read project files. No particular model or agent tool is required.

## What it covers

One umbrella session coordinates six phases:

| Phase | What happens |
|---|---|
| P1 research | Frame the problem with you. Produce a kickoff, and an analysis unless the task is small or a defect |
| P2 analysis | Specs, then a verification contract, then handoffs for isolated sessions. You approve the specs and the contract |
| P3 implementation | An isolated sub agent implements from the handoff, opens the PR, and follows CI and review feedback |
| P4 review | An independent sub agent reviews the PR, up to 3 rounds, then escalates |
| P5 auto verification | Runs the contract's auto scenarios right after review passes, when there are any |
| P6 manual verification | Runs the contract's manual scenarios on your trigger, when there are any |

Approvals are tied to a specific revision of a specific artifact. Closing a milestone always needs your explicit sign-off.

## Not a harness

This package can't spawn agents, lock files, ensure atomic writes, enforce approvals or isolate worktrees. The umbrella coordinates those only where the environment provides tooling. Approval records in files are evidence, not access controls.

## Layout

| Folder | What it holds |
|---|---|
| `policies/` | What must be respected: authority, scope, approvals, internal codes, evidence integrity |
| `standards/` | How work and artifacts are produced: design, specifications, evidence, PR feedback |
| `workflows/` | One procedure per phase |
| `templates/` | Starting points for each artifact |
| `references/` | Optional extras, such as a remote status page |

## Optional tools

Workflows name tools by capability and `SKILL.md` binds each one, with a fallback when it isn't installed: a benchmark designer, a handoff writer and a PR feedback handler.

## Out of scope for now

Detailed code-review policy, automated approval gates, locking and agent orchestration, and delivery (merging, deployment, backports) unless separately authorized.
