---
name: ship-check
description: Check a deliverable before it reaches someone else: trace every claim to a source, have a fresh agent cold-read it as the audience, and render it and look. Use before publishing, sharing or handing over anything written for other people (a slide deck, document, report, summary, PR description, ticket comment, status update, retro), when the user says "check this before I share it", "cold read", "is this clear", or after review comments keep coming in on the same deliverable. Not for code correctness (use a code review) or for drafting the content itself.
argument-hint: "<deliverable path or url> [audience]"
---

# Ship check

The person who wrote a deliverable is the worst judge of whether it reads: they fill every gap from what they already know. Three failures recur, and none is about the format:

- **Compression.** Shorthand coined while working ("the pin", "missing against lost", a ticket number used as a noun) reads as jargon to anyone who wasn't there.
- **Untraced claims.** A line taken from a summary written earlier, or an inference worded as a fact. The source may have been overtaken: the fix a report recommended is not always the fix that shipped.
- **Never looked at.** "It published" is not "it fits": text clips, a table overflows, a chart is empty.

When the reviewer is the one catching these, the check is in the wrong place. Run this before the deliverable leaves your hands, and again after a round of review changes.

## 1. Trace the claims

List every factual claim: numbers, dates, causes, who did what, what was fixed, before or after what. For each, write where it comes from:

| Claim | Source | Status |
|---|---|---|
| | file and line, commit, query, link | verified · inferred · unverified |

- **Re-check against the current state**, not the document you read it in, whenever the claim could have changed since: what shipped, what merged, a ticket's status, who owns something. Read the commit, the merged change, the live record.
- **An inference stays labelled** in the deliverable ("inferred from …", "not measured"). Never round it up to a fact because it reads better.
- **A claim you can't source and don't need, cut.** One you need and can't source, label and tell the user.

## 2. Cold read

Give a fresh agent the deliverable and nothing else: no notes, no transcript, none of your context. That isolation is the point. Without a subagent, ask the user to have a colleague read it instead; don't cold-read your own work.

Brief it with the audience (who they are, what they already know, what they don't) and ask it to quote the exact text for each:

- **Jargon:** a term, code or phrase the audience couldn't follow without the working notes.
- **Unclear:** a sentence it had to read twice, or whose point it can't state in one line.
- **Unsupported:** a claim with no basis on the page, a number with no unit or comparison point, a contradiction between parts.
- **Missing step:** a conclusion that doesn't follow from what's shown, or the obvious next question ("which step found it?", "before or after?", "who did that?").
- **Tone:** blame, defensiveness, or self-praise the audience would notice.
- For each section: its point in one line, or "can't tell".

Ask for findings only, no rewrites and no praise.

## 3. Render and look

Open the deliverable the way its audience will: rendered slides, the published page, the PR preview. Check that every slide or page fits without clipping, tables and code blocks don't overflow, images and charts render, and links resolve. If you can't render it, say so in the report. Don't claim it fits.

## 4. Fix the class, not the instance

For each finding, from the cold read or from a human reviewer, fix every place the same problem occurs, not only the quoted line. A jargon term flagged on one slide is usually on three. Then re-run step 2 on the changed parts.

## Report

Tell the user, briefly:

- the claims you corrected or labelled, and any you couldn't source;
- what the cold read flagged and what you changed, by section;
- what you rendered and checked, and anything you couldn't check.
