# P1 — Research & analysis

**Entry:** User has a problem and a reason to investigate it. **Start:** the umbrella creates this session immediately when the user starts Artifex. **Owner:** User frames; research agent investigates.

**Inputs:** Problem, why, goals/objectives, in scope, out of scope, optional hypothesis; relevant references.

**Documents:** kickoff and analysis are human-targeted. Draft each as a document artifact and generate markdown only on approval (`SKILL.md`, Documents).

1. Build `kickoff.md` with the user. Ask for **materially missing** inputs only; don't invent goals or scope. User confirms framing.
2. Investigate the narrowest relevant sources. Separate observed findings, assumptions, and open questions (`standards/evidence.md`).
3. Describe the current situation, likely direction and **meaningful** alternatives/trade-offs. Don't require an alternative for its own sake.
4. Propose milestones, rough sizing/confidence, dependencies, risks and unresolved questions (`templates/analysis.md`).
5. Present a clear direction and ask the user to choose/approve it **and select one milestone** for P2. Record decision and referenced revision in the umbrella-owned `STATE.md`.

**Outputs:** Confirmed kickoff, analysis with direction/design proposal, milestones/sizing, dependencies, risks and open questions.

**Exit:** User has accepted the direction and picked a milestone. For a small task or defect whose scope is already clear, an approved kickoff is enough: skip the analysis and go straight to P2, with the task as the milestone. If evidence invalidates framing, return to step 1; if insufficient, report what is missing rather than filling placeholders.
