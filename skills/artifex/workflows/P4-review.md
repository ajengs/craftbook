# P4 — Independent review

**Entry:** An isolated sub agent started by the umbrella **automatically** when P3 reports the PR is open, and again for each later round when P3 reports fixes pushed. The umbrella does not wait for CI. Inputs: the PR or changeset, P3 evidence, approved specs, verification contract and implementation handoff. **Owner:** Separate review sub agent.

**Codes:** internal codes stay in notes. Keep them out of anything posted to the PR or ticket (`policies/core.md`).

**Review loop (maximum 3 review rounds):**

1. Establish separation from implementation where supported; describe any independence limitation honestly.
2. Inspect requirement coverage against **approved spec IDs**, correctness, unjustified complexity and scope expansion. Use relevant project conventions. **Detailed code-review policy is deferred.**
3. Report only concrete findings with relevant evidence/location and impact. Don't impose hypothetical edge-case requirements.
4. Give `pass`, `blocked`, or `inconclusive` with a short rationale (`standards/evidence.md`). **Notify the umbrella** that the round is done and report the verdict and findings to it, not to the implementer. The umbrella records the round and verdict in `STATE.md`.
5. On `blocked`, the umbrella relays the findings to P3, which fixes and pushes. When P3 reports the push, the umbrella starts the next round as a new review sub agent.
6. Route **design or specification ambiguities** to the user or P2 through the umbrella, not as an invented reviewer decision. If inconclusive, request the missing evidence.
7. If the third round does not end in `pass`, the umbrella **stops and escalates to the user** with the unresolved findings, what changed each round and options. No fourth round starts on its own.

P4 does not watch the PR or CI. P3 does that.

**Output:** Review verdict + findings per round; a `review.md` is optional if the result is already persistently captured.

**Exit:** A `pass` with no unresolved blocking findings. The umbrella then starts P5 (auto verification) if it applies and the verification handoff is ready with no blocker or dependency, and tells the user whether P6 applies. P5 and P6 also need a separately approved verification contract.
