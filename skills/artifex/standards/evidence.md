# Evidence and reporting

Produce **decision-useful evidence**, not a wall of annotation.

- Support consequential findings with a code location, trace/log, measurement, test result, or reproducible observation when available. Label hypotheses/uncertainties when they affect interpretation.
- A code review reports **coverage of approved requirements, specific findings with locations and impact, and a verdict** (`pass`, `blocked`, `inconclusive`). Detailed review policy is deferred; use project conventions without inventing a new global standard.
- Verification reports map contract scenario IDs to actual outcomes (`pass`, `fail`, `not run`, `invalid`), show the relevant raw evidence location, and separate raw observations from calculations.
- A failed or inconclusive run cannot become a pass through narrative. State environment, limitations and confounders when material.
- Keep reports concise: **verdict first**, then findings/evidence, limitations and next action. Do not hide incomplete work as a clean handoff.
