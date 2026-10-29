# P4 — Independent review

**Entry:** An isolated sub agent started by the umbrella **automatically** when P3 reports the PR is open, and again for each later round (`SKILL.md`, Which pushes start a review round). The umbrella does not wait for CI or the verification contract. Inputs: the PR or changeset, P3 evidence, approved specs and implementation handoff; include the approved verification contract only when it is already available. **Owner:** Separate review sub agent.

**Codes:** internal codes stay in notes. Keep them out of anything posted to the PR or ticket (`policies/core.md`).

**Review loop (maximum 3 review rounds; only 1 round for P3 rework that P5 triggered):**

1. Establish separation from implementation where supported; describe any independence limitation honestly.
2. Run the PR reviewer (`SKILL.md`, Optional tools) on the PR. Give it the approved specs as its requirements, so it reports each spec as covered, partly covered or not covered. Give it the implementation handoff as a project note and, if already approved, the verification contract; never delay P4 waiting for that contract. Also give it the previous round's review if there was one (rounds 2 and 3 are then incremental: only the changes since the last reviewed head, plus a check that the earlier findings are resolved; a full review of the whole PR runs in P5 when the contract includes it), and the milestone folder as its review folder. If the environment doesn't let a sub agent start further agents, the reviewer runs its lenses itself, one after another. Without a PR reviewer, inspect requirement coverage against the **approved spec IDs**, correctness, unjustified complexity and scope expansion yourself. Use relevant project conventions. Apply `SKILL.md`, Execution efficiency, to tool output. **Detailed code-review policy is deferred.**
3. Keep only concrete findings with relevant evidence, location and impact. Don't impose hypothetical edge-case requirements.
4. Give a verdict with a short rationale (`standards/evidence.md`): `pass`, `blocked` or `inconclusive`. With the PR reviewer's output:
   - **pass:** its verdict is Approve, or Approve with suggestions, and nothing is classed blocks-merge. Suggestions and before-enablement items are recorded as follow-ups, not blockers.
   - **blocked:** anything is classed blocks-merge, or its verdict is Wait for author or Reject.
   - **inconclusive:** a reviewer ran out of budget on something that matters, the diff was truncated, or a spec couldn't be assessed.

   **Notify the umbrella** that the round is done and report the verdict and findings to it, not to the implementer. The umbrella records the round and verdict in `STATE.md`.
5. On `blocked`, the umbrella relays the findings to the P3 session. P3 starts a new implementation subagent after its previous subagent has ended; the subagent fixes and pushes, and P3 relays the push to the umbrella. If the P3 session is unavailable, the umbrella creates a replacement P3 session from the controlling handoff and findings. When P3 reports a push that answers the findings, the umbrella starts the next round as a new review sub agent, giving it the previous review and the last reviewed head. If history was rewritten or the target branch was merged in, the range from the old head no longer isolates P3's own changes: compare with `git range-diff`, skip commits that came from the target branch, and review any conflict resolution, since the reviewer has not seen that code. Use the previous review and artifact references to give the new reviewer the context it needs.
6. Route **design or specification ambiguities** to the user or P2 through the umbrella, not as an invented reviewer decision. If inconclusive, request the missing evidence.
7. If the third round does not end in `pass`, the umbrella **stops and escalates to the user** with the unresolved findings, what changed each round and options. No fourth round starts on its own. For P3 rework that a P5 failure triggered, only one round runs. If it doesn't end in `pass`, the umbrella escalates the same way instead of starting another round.

P4 does not watch the PR or CI. P3 does that. After a pass, new P3 commits that change code or tests start one more incremental round (`SKILL.md`, Which pushes start a review round); documentation-only pushes, a rebase or a merge of the target branch alone don't.

**Output:** Review verdict + findings per round; a `review.md` is optional if the result is already persistently captured. The PR reviewer's own review file can serve as that record.

**Exit:** A `pass` with no unresolved blocking findings. The umbrella then starts P5 (auto verification) if it applies and the verification handoff is ready with no blocker or dependency, and tells the user whether P6 applies. P5 and P6 also need a separately approved verification contract.
