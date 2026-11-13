# Tradeoffs and limitations — <milestone>

Specs: <path@revision of the specs this was seeded from>
Rules: `standards/design.md`, Tradeoffs and limitations register. A living register, not an approval gate: rows are never deleted, and every status change adds a line to the row's decision log.

| ID | Limitation / tradeoff | Impact / consequence | Severity | Rationale | Status | Decision log | Boundary: still a defect when | References |
|---|---|---|---|---|---|---|---|---|
| LIM-001 | <what we live with, in one sentence> | <what a user, operator or later change actually experiences> | low / medium / high | <why this was chosen over the alternative, and what it buys> | accepted / deferred / handled | <YYYY-MM-DD · who · — → status · note> | <testable condition at which this stops being a known limitation> | <spec ids, edge-case row, PR or thread, commit, review or evidence path, follow-up ticket> |

No rows yet. Replace the placeholder row above, or delete it if nothing is registered.

## Writing a row

- **Status.** `accepted`: we live with it and don't plan to remove it. `deferred`: not now, with a follow-up named in References, or the word `none` if there isn't one yet. `handled`: mitigated or removed within the approved design; the row stays to record what remains and where it's dealt with.
- **Decision log.** One entry per status change, oldest first, separated by `<br>`: `date · who · from → to · note`. The first entry's `from` is `—`. `who` is the person who decided. `accepted` and `deferred` need the user; the proposing agent goes in the note. `handled` may be recorded by the agent that did the work, with the commit or PR in References.
- **Boundary.** A measurable condition, such as a number, a data shape or a scenario, after which the behavior is a real defect and a review finding or verification failure. If you can't state one, the tradeoff isn't understood well enough: escalate it instead of registering it.
- **Not registrable as accepted or deferred:** a consequence of data loss, corruption or a leak, a security impact, or a behavior that makes an approved spec row untrue. Those are defects or spec changes.
- Internal ids (`LIM-`, `SPEC-`) stay in this file. Describe the behavior in words anywhere else.
