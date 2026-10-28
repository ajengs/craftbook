---
name: pr-review-pipeline
description: Verdict-first pull request review that separates what blocks the merge from what must be fixed before a feature is switched on. Builds a commit-accurate diff, runs two or three specialist reviewers in parallel, calibrates severity, and writes a local review document with a suggested verdict. Use when the user names a PR by id or URL, or a branch range, and wants to know "can I merge this", "what would block this PR", or "review this PR before I approve". Works with any git host. Writes a local file and does not post to the PR.
---

# PR review pipeline

Two or three specialist reviewers read the same diff in parallel. You merge their findings, calibrate severity, and write one review that leads with the verdict. What makes this better than "just review the PR":

1. **A correct diff.** Most bad automated reviews reviewed the wrong bytes. Step 2 prevents that.
2. **Severity that survives contact with reality.** An ungrounded "high" trains the author to ignore the review.
3. **Findings grouped by what the reader must do**, not by who found them or how bad they are.
4. **A decision, not a transcript.** The review answers "can I merge" and "what do I owe before it ships", and keeps the rest as evidence.

**Scope:** this writes a local review file and reports to the user. It does not post to the PR. If the user wants the findings on the PR, they copy them across, or ask explicitly and you post as a separate action.

## Setup

- **Target:** a PR id or URL, or two branch names or a commit range. If none was given, ask. Don't guess.
- **Review folder:** the user's choice. Default `~/pr-reviews/` (`%USERPROFILE%\pr-reviews` on Windows). Never write review files inside the project folder.
- **Project notes:** if the repo has review notes (`.review/notes.md`) or conventions in `AGENTS.md` or `CLAUDE.md`, take the parts that matter for review and pass them to the reviewers as PROJECT NOTES. Otherwise leave the section out.
- **Requirements (optional):** acceptance criteria or specs the change must satisfy. If given, they go to the reviewers, who report each as covered, partly covered or not covered, and raise a finding for any not covered.
- **Previous review (optional):** the path of an earlier review of this PR. If given, later rounds review only what changed since it (see step 2).
- Track the nine steps below with a todo list.

## 1. PR source

Get these however the environment offers them (a CLI, an MCP, an API, or the user pasting them): **title, description, source branch, target branch, changed file paths**. Linked work items are optional. If a field is missing, ask or derive it from git. With no PR service at all, take a branch range and use the newest commit messages as the description. From here on it is plain git.

## 2. Build a commit-accurate diff

**Never diff branch against branch.** `git diff target..source` includes the inverse of every commit that landed on the target after the source diverged, so it reports the author as having deleted code they never touched. Reviewers then spend their budget on phantom regressions.

1. Sync the source branch without touching the working tree: fetch it into a local ref (`git fetch origin <source>:<source>` if it is missing or stale). Don't check out or merge, because the user may have work in progress.
2. List the PR's commits: `git log <target>..origin/<source> --oneline`.
3. **One commit:** diff it against its own parent (`git diff <hash>^..<hash>`). **Several:** find the merge base (`git merge-base origin/<source> <target>`) and diff from it (`git diff <base>..origin/<source>`).
4. **Sanity-check** the diff's scope against the commit messages and description. "Updated 6 call sites" with 50 changed hunks means the range is wrong: re-derive it before going on.
5. If the diff is over about 20,000 characters, truncate it and say so in the review.

**Incremental rounds.** If a previous review is given, read the commit it reviewed (the "Reviewed commit" line). If that commit is an ancestor of the current source head (`git merge-base --is-ancestor <reviewed> origin/<source>`), diff only `<reviewed>..origin/<source>`, embed only the files that diff touches, and give the reviewers the previous review's blocks-merge and before-enablement findings to verify. If it isn't an ancestor (the branch was rebased or force-pushed), fall back to the full diff and say so. Either way, record the head commit you reviewed.

## 3. Build the context

- **Size gate.** Count the implementation files (paths without "test" or "spec"). If more than 10, ask which paths matter, or whether to proceed with truncation.
- **Files.** Embed each changed implementation file whole if it is 150 lines or fewer. Otherwise embed only the changed hunks plus about 40 lines either side, prefixed `[TRUNCATED: diff-relevant sections only. Full file: <path>]`.
- **Tests.** For each implementation file, find tests by naming convention: test or spec files and folders that mention the class or module name. Embed what matches, plus any test files already in the PR. Implementation files with no test go into MISSING_TESTS. Tests go to the tests reviewer only.

## 4. Run the reviewers

Read `references/reviewer-prompts.md`. Assemble each prompt as shared preamble plus one lens, and send them **in one message** so they run concurrently.

| Reviewer | When | Tool calls |
|---|---|---|
| `logic-reviewer`: correctness, design, performance | Always | 8 |
| `test-reviewer`: test coverage | Always | 8 |
| `config-reviewer`: configuration and wiring drift | Only if the diff touches configuration, dependency registration, public contracts or migrations | 15 |

Each returns one JSON block. If one returns prose or malformed JSON, re-prompt that reviewer once for the block instead of discarding its work.

**If you can't start sub agents** (the environment doesn't allow it, or you are already running as one), run the lenses yourself one after another. Give each its own tool budget, produce its own JSON block, and keep them separate, then continue at step 5.

## 5. Summarize what the PR does

Write the PR summary: four or five sentences grounded in the diff and commit messages, no speculation. Answer exactly four questions: what does it enable, what changed since the previous review (which earlier findings are resolved), is it safe to merge, and what still blocks production enablement. Don't narrate the architecture. A detail earns a sentence only if it was previously wrong. State shared context that recurs ("the flag is off by default") here, once. The reviewers were told not to repeat it per finding.

## 6. Aggregate and rank

**Severity pass, done by you.** For every critical or high finding, read its `blast_radius`. Downgrade one level if it is empty, hedged ("could cause issues") or purely theoretical. **Do not downgrade because the feature is off by default or flag-gated.** Code ships disabled to be switched on later, often by a config change with no second review. Judge each finding at the severity it carries once enabled.

**Action class, done by you.** Add `action_class` to every finding. It depends on merge context the reviewers never saw: whether this is a stacked draft, what the target feeds, what ships next.

| Class | Means |
|---|---|
| `blocks-merge` | Cannot merge until fixed |
| `before-enablement` | Safe to merge; fix before the feature is switched on |
| `verification` | A test or coverage gap: nothing is known broken, but nothing proves it isn't |
| `cleanup` | Advisory, author's discretion |

**Then run the script**, which does dedup, ranking, counting, IDs and rendering deterministically:

```bash
# save each reviewer's JSON block as <reviewer-name>.json in a temp dir first
python scripts/aggregate_findings.py <temp-dir> --json-out <temp-dir>/aggregated.json --md-out <temp-dir>/findings.md
```

Read its warnings (thin blast radii, unclassified findings, same-location findings it did not merge), fix the JSON and re-run. Every finding needs an exact line number: if a reviewer returned `null`, find it in the pre-loaded content.

**Keep the raw reviewer JSON.** Copy the temp folder's reviewer files to `<review-dir>/<review-file-name-without-extension>.reviewers/`, so a later check can measure which reviewer found what. Copy `aggregated.json` there too: the next round reads the findings from it.

## 7. Decide the verdict

Pick one of the four verdicts using the criteria in `references/review-template.md`. Produce: the label with the **target branch named in it**, a one-line state sentence (what changed since any previous review), a two or three sentence rationale citing finding IDs, and **two separate ID lists**: what blocks the merge, and what must be fixed before production enablement. Keeping those two apart is most of the verdict's value. A verdict must never rest on "the flag is off".

## 8. Write the document

Write it yourself from `references/review-template.md`, in one pass, to `<review-dir>/PR-<id>-<title-slug>-<YYYY-MM-DD>.md` (title lowercased, spaces to hyphens, special characters stripped, 40 characters at most). If the user has a writing-style guide, apply it to the verdict, summary and rationale only. **Put the verdict block at the top**, above the summary. **Splice `findings.md` in verbatim**: don't re-rank, re-word, re-severity or drop findings.

## 9. Report back

In chat, result first: the verdict, the outcome line from the script, the review file path, and one line for each `blocks-merge` and `before-enablement` finding. Mention any coverage gap (a reviewer's `budget_exceeded`, a truncated diff). Don't preview verification or cleanup items: they are in the file.
