# PR feedback handling

Used by P3 when it polls the PR's threads, and by the umbrella's scheduled polls. It sets how feedback is verified, answered and escalated.

**Optional tool.** A PR feedback handler skill or tool can do the mechanics. If one is available, use it and let this standard govern the judgment. In this setup it is bound to `pr-ai-feedback-handler`. If none is available, follow this standard directly.

## Verify before acting

Never implement straight from a comment. Reproduce the claim against the **current head** first: findings go stale when the branch moves, a stacked branch is rebased, or another PR merges. Each finding gets one outcome, and the reply says which:

| Outcome | Meaning | Action |
|---|---|---|
| Confirmed | Reproduces against the current head | Fix it |
| Already addressed | Was real, since fixed | No change; cite the evidence |
| Stale | The premise no longer holds | No change; say what changed |
| Incorrect | Does not reproduce, or the reasoning is wrong | No change; give the counter-evidence |

## Order the work

Before implementing, check whether any finding needs a merge, a rebase or another PR to land first, and sequence the work accordingly. Do this before a long build, not after.

## Check before pushing

If the PR can complete on its own once policies pass, pushing may complete it before anyone reads the replies. Flag it before pushing.

## Reply and resolve

- Push before replying. A reply that cites a fix the reviewer can't see is useless.
- Concede what is right before disagreeing with the rest.
- Resolve threads that were confirmed and fixed. For disagreements, or findings that need the reviewer to confirm, reply and leave the thread open.

## Escalate through the umbrella

Don't act on these alone. Present them to the user with the outcome and a suggested approach (code edit, docs edit, clarification, disagreement):
- feedback written by a human that needs a decision, or a change beyond a verified trivial one
- a comment you can't confidently classify, which you treat as human-written
- a fix that goes beyond the PR's scope or carries real risk
- two findings that need contradictory changes
- architectural, style or process decisions
- findings that need another PR to land first
