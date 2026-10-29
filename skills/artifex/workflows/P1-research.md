# P1 — Research & analysis

**Entry:** User has a problem and a reason to investigate it. **Start:** the umbrella creates this session immediately when the user starts Artifex. **Owner:** User frames; research agent investigates.

**Inputs:** Problem, why, goals/objectives, in scope, out of scope, optional hypothesis; relevant references.

**Documents:** kickoff and analysis are human-targeted. Create and review them sequentially using the native-artifact or markdown-viewer branch in `SKILL.md`, Documents.

1. Draft the kickoff with the user from `templates/kickoff.md`. Ask for **materially missing** inputs only; don't invent goals or scope. Follow `SKILL.md`, Documents: use a native document artifact when available; otherwise create `kickoff.md` and open it in the artifact viewer immediately. Process passage or visual annotations as focused revisions while preserving the rest of the document.
2. Ask the user to approve the current kickoff revision. Until that approval is explicit, keep revising the same kickoff document; do not create an analysis artifact or `analysis.md`, and do not begin the investigation. On approval, ensure the approved `kickoff.md` derived copy exists as required by `SKILL.md`, Documents. Ask the user whether the approved kickoff is a small task or defect whose scope is already clear enough to use as the milestone; only the user makes this classification. If the user explicitly confirms it, record that confirmation and the scoped task as the selected milestone, then continue at step 6 without creating an analysis.
3. Unless the user selected the small-task route, investigate the narrowest relevant sources. Separate observed findings, assumptions, and open questions (`standards/evidence.md`).
4. Draft the analysis from `templates/analysis.md`. Describe the current situation, likely direction and **meaningful** alternatives/trade-offs; don't require an alternative for its own sake. Propose milestones, rough sizing/confidence, dependencies, risks and unresolved questions. Follow the same native-artifact or markdown-viewer branch and focused annotation loop as the kickoff.
5. Ask the user to approve the current analysis revision, choose the direction, and select one milestone for P2. On approval, ensure the approved `analysis.md` derived copy exists as required by `SKILL.md`, Documents.
6. Notify the umbrella with one complete checkpoint: either (a) the kickoff and analysis paths and approved revisions plus the selected milestone, or (b) the kickoff path and approved revision plus the user's explicit small-task scope confirmation and the scoped task as the selected milestone. Include unresolved blockers. The umbrella records the checkpoint in `STATE.md`, creates a new P2 session, and starts it with the selected milestone and the coordination envelope. If coordination is unavailable or not authorized, produce the same checkpoint for manual relay instead of claiming P2 started.

**Outputs:** Confirmed kickoff, plus either an analysis with direction/design proposal, milestones/sizing, dependencies, risks and open questions, or the user's explicit small-task scope confirmation.

**Exit:** The checkpoint has reached the umbrella for P2 creation with either (a) approved kickoff and analysis revisions, an accepted direction, and one selected milestone or (b) an approved kickoff revision and the user's explicit confirmation that the scoped task is the milestone. If evidence invalidates framing, return to step 1; if insufficient, report what is missing rather than filling placeholders.
