# Rules for human-readable benchmark approval contracts

## 1. Purpose and separation

- The **contract** helps a person decide whether to approve an experiment: question, variants, workloads, sequence and cost, decision rules, validity, risks and permissions.
- The **runbook** tells an agent how to execute it: commands, setup, file paths, run ids, collection steps, logs and recovery.
- Keep a detail in the contract only if removing it could change the approval decision, the interpretation of results, the safety boundary, or the expected time or cost. Otherwise link to the runbook.
- Never silently change decisions or thresholds while simplifying. Mark unconfirmed values as proposed, and preserve conditions and stop rules.

## 2. Language

- Lead with the question and the decision, not methodology jargon.
- Use direct names for configurations ("Old unlimited", "Cap 8", "Serial") and for stages ("Rehearsal", "Stage 1").
- Explain a technical term only when a decision needs it, once, near first use.
- Remove repeated qualifiers, introductory filler and statements that only describe how the document was written.
- Keep numbers, inequalities, sample limits and caveats that affect what the results can claim.
- Don't promise a measured result from a preliminary, single-run observation.

## 3. Codes and references

- A short code never stands alone when it could need a lookup. Write the descriptive name first and the code in parentheses: **Cap 8 (S-B)**, **Rehearsal (R0)**. In a run schedule, "R1:" is fine when the action next to it names the configuration.
- If an identifier is long, link to its definition instead of repeating it.
- Define each configuration in one table and use the same names everywhere.
- Use codes only where they are needed to match recordings, scripts or the runbook, not as the main language of the contract.
- Keep document-authoring conventions in this file, never as commentary in the final contract.

## 4. Structure and formatting

- Keep the six sections: **1. The question; 2. Verdict / decision rule; 3. What is measured; 4. Environment and controls; 5. Validity and limitations; 6. Deliverables and authorization.** Put **Blocking inputs** before them only when approval decisions remain open.
- Combine the run schedule and the estimated duration into one table, with any stage gate, optional branch and totals directly beneath it.
- Use bullets for short independent steps, requirements, limitations and permissions. Sections 5 and 6 are bullets.
- Use tables for comparisons or items with several attributes. Sections 3 and 4 are tables.
- Use paragraphs only for connected reasoning, and don't repeat table content in prose.
- Bold useful anchors, not every noun. Keep headings short.

## 5. Approval-grade detail

**Keep in the contract:**
- The question and why the test is needed.
- Configurations with meaningful differences (full parameter names only if approval depends on them).
- Workloads, approximate sample counts, stages, early-stop conditions, and run order if it protects validity.
- Overall time estimates and what increases or stops the work.
- Decision thresholds, noise checks, scope of conclusions and unresolved approvals.
- Primary metrics, measurement limits, validity failures and real environmental risks.
- Deliverables, human actions and the permission boundary.

**Link to the runbook for:**
- Exact commands, setup and configuration manipulation.
- Long identifiers, hashes and detailed build provenance.
- Recording, parsing and report-generation steps.
- Run-log and file naming conventions.
- Operational checks that don't change authorization or validity.

## 6. Final review checklist

- [ ] Can a reviewer state the experiment's question after the first paragraph?
- [ ] Are approval items clearly separate from established decisions?
- [ ] Are configurations named consistently, with codes attached or linked?
- [ ] Is there one combined schedule and time table, including conditional stages?
- [ ] Can the reviewer tell when to stop, continue, or withhold a verdict?
- [ ] Does the contract separate preliminary evidence from measured differences?
- [ ] Are sections 3 and 4 tables and sections 5 and 6 bullets?
- [ ] Are limits, risks, deliverables and permissions easy to scan?
- [ ] Have execution-only details and writing instructions been removed?
- [ ] Does every workload say scripted or agent-driven, and is every measured workload whose decision rule depends on pacing, concurrency, request count or end-to-end duration scripted?
- [ ] Does every scripted workload link its script?
- [ ] Does every retained detail justify its reading cost?

## 7. Additions

- **No source tags in the contract.** Confirmed values are stated plainly. An unconfirmed value is written as **proposed** where it appears and gets a bullet under Blocking inputs. Provenance for every contract value, and the basis of each duration estimate, lives in the runbook's Contract value sources table.
- **Delete every template comment and placeholder.** A required field the user still owes becomes a Blocking-inputs bullet, not a leftover placeholder.
- **One run per configuration is a reproduction.** Say so under Evidence limits and keep timing claims preliminary.
- **The runbook keeps the operational identifiers** the contract links to: environment names, configuration names, provenance checks, artifact paths.
