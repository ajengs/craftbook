# Evidence and reporting

Produce **decision-useful evidence**, not a wall of annotation.

- Support consequential findings with a code location, trace/log, measurement, test result, or reproducible observation when available. Label hypotheses/uncertainties when they affect interpretation.
- A code review reports **coverage of approved requirements, specific findings with locations and impact, and a verdict** (`pass`, `blocked`, `inconclusive`). Detailed review policy is deferred; use project conventions without inventing a new global standard.
- Verification reports map contract scenario IDs to actual outcomes (`pass`, `fail`, `not run`, `invalid`), show the relevant raw evidence location, and separate raw observations from calculations.
- A failed or inconclusive run cannot become a pass through narrative. State environment, limitations and confounders when material.
- Keep reports concise: **verdict first**, then findings/evidence, limitations and next action. Do not hide incomplete work as a clean handoff.

## Evidence in one file

The document that makes a claim carries its evidence: the diagnosis, the verification report, a review finding. A reader must be able to check the claim from that one file, without opening raw outputs or rerunning tools. Raw files and analysis outputs stay where they are, as backing, and each excerpt names the file or link it came from.

For every source used, put the excerpt that proves the point in the document, for whichever of these exist:
- **Exceptions:** type, count, which threads or requests, over what window. Quote the message only when it carries no customer data.
- **Stack traces:** the frames that show the point, innermost first, framework frames cut, in a code block. Where several captures or dumps agree, say so and show one.
- **Logs:** the few lines that matter, with timestamp, instance and level, plus the query or link that finds them.
- **Metrics:** the values (before, during, after) and a link that keeps the instance, query and time range. A dashboard home page is not evidence.
- **Screenshots and images:** embedded or attached in the document, with what they show.
- **Dumps and profiler captures:** the command run and the key lines of its output.
- **Tests and reproductions:** the command and the red or green output that matters.

Say which kinds were unavailable and why. Redact secrets and customer data (credentials, session ids, query strings, SQL text, personal data) in every excerpt. Keep each excerpt to what the claim needs: evidence is not a dump of everything collected.

## Verification run inventory

For each run, report the planned and actual tools/skills (with references), why they were used, readiness evidence and date, required/optional artifacts and their purposes, collected paths or query links, and missing evidence with its consequence. Use the statuses in `references/verification-tools.md`. Record environment, head, scenario IDs, timestamps/timezone and capture settings so recordings, dashboard views and snapshots can be correlated. A link must preserve the instance, query and time range; a dashboard home page is not evidence of a measurement. Manual user results identify what the user actually did or reported and what the agent independently observed.
