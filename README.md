# craftbook

Reusable agent skills for engineering work. Each skill is a self-contained folder: a `SKILL.md` entry point plus its own policies, standards, workflows, templates and references. No skill depends on another one being installed, and none assumes a particular company, stack or tracker.

**Status:** drafts, not yet exercised end to end. Skills are instructions, not an enforcement mechanism: nothing here locks files, enforces approvals or guarantees that an agent was launched.

## Skills

| Skill | What it does |
|---|---|
| [`artifex`](skills/artifex/SKILL.md) | A user-led engineering workflow for larger changes. One umbrella session coordinates six phases: research, development analysis (specs, a verification contract, handoffs), implementation, independent review, auto verification and manual verification. Human-facing documents are drafted as commentable documents and written as markdown only after approval. |
| [`benchmark-designer`](skills/benchmark-designer/SKILL.md) | Designs and runs a benchmark from one template: an approval contract (question, configurations, workloads, decision rule, validity, schedule) and an agent runbook that executes it. Works for any stack. |
| [`pr-review-pipeline`](skills/pr-review-pipeline/SKILL.md) | A verdict-first pull request review. It builds a commit-accurate diff, runs two or three specialist reviewers in parallel, calibrates severity, and writes a local review that separates what blocks the merge from what must be fixed before a feature is switched on. Works with any git host and doesn't post to the PR. |

## Install

See [`INSTALL.md`](INSTALL.md) for Linux, macOS and Windows, Claude Code, Claude.ai, Codex CLI, Gemini CLI and other agents.

## How the pieces fit

`artifex` names tools by capability and binds each one in its `SKILL.md` ("Optional tools"). If a tool isn't installed, it falls back instead of failing.

| Capability | Default | Fallback |
|---|---|---|
| Benchmark designer | `benchmark-scenario`, if you have it installed | `benchmark-designer` from this repo |
| Handoff writer | A `handoff` skill, if available | Follow the same instructions directly: a self-contained document that references artifacts instead of copying them |
| PR reviewer | `pr-review-pipeline` from this repo | Review by hand: coverage against the approved specs, correctness, unjustified complexity and scope expansion |
| PR feedback handler | Any handler you have installed | `standards/pr-feedback.md` |
| Document system for review drafts | A commentable document or artifact system | Markdown files |
| Sub agents and session creation | Whatever your environment provides | The umbrella prepares a brief and asks you to start the session |

## Layout

```
skills/
  artifex/
    SKILL.md              entry point
    policies/             what must be respected
    standards/            how artifacts and work are produced
    workflows/            one procedure per phase
    templates/            artifact starting points
    references/           optional extras, such as a remote status page
  benchmark-designer/
    SKILL.md
    templates/
    references/
  pr-review-pipeline/
    SKILL.md
    references/
    scripts/              deterministic findings aggregation
```

## Conventions

- A skill folder is self-contained. Scripts, templates and references live inside it and are referenced relative to it.
- Skills name other tools by capability and give a fallback. They don't hard-code personal paths, company names or tracker names.
- Codes a skill invents for tracking stay in notes. They don't go into code, commits, pull requests or tickets.
