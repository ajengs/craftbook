# Review document template

Write the file in one pass to `<review-dir>/PR-<id>-<title-slug>-<YYYY-MM-DD>.md`.

## The one rule

**The result goes first.** A reader opens a PR review to answer two questions: can this merge, and what do I owe before it ships. Everything else is evidence. Nobody should have to reach the bottom to learn they can merge.

## Structure

```markdown
## Automated PR review

**{{PR_TITLE}}** · `{{SOURCE_BRANCH}}` → `{{TARGET_BRANCH}}` · PR {{PR_ID}} · {{DATETIME}}
Reviewed commit: `{{HEAD_SHA}}` · Scope: {{full, or incremental since `{{PREVIOUS_SHA}}`}}

> ## {{VERDICT_LABEL}} into `{{TARGET_BRANCH}}`
>
> {{ONE_LINE_STATE}}
> {{OUTCOME_LINE}}
>
> {{RATIONALE}}
>
> {{IF blocking IDs:}}**Before merge:** [C1] short reason · [H2] short reason{{END IF}}
> {{IF enablement IDs:}}**Before production enablement:** [M1] short reason · [M2] short reason{{END IF}}

{{IF the diff was truncated: one line saying so and where}}

## What this PR does

{{PR_CHANGE_SUMMARY}}

<<< findings.md, verbatim: outcome line, action-class groups, metadata block >>>
```

`ONE_LINE_STATE` is one sentence: what changed since any previous review, and whether earlier findings are resolved. `OUTCOME_LINE` comes from the script. `RATIONALE` is two or three sentences citing finding IDs.

Example opening:

> **✅ Approve for merge into `main`.**
> All six earlier high-severity issues are fixed. No new critical or high findings.
> **2** to fix before production enablement · **3** test/verification gaps · nothing blocking merge

## Writing rules

- The findings body is final. Splice it in verbatim. No re-ranking, re-wording, severity edits or dropped entries.
- State shared context once, in the summary, not inside findings.
- The summary answers four questions and stops. Don't walk the architecture.
- Write what is true and what to do, not how it was discovered.

## Verdict criteria

| Verdict | Criteria |
|---|---|
| ✅ **Approve** | No critical or high findings. Medium and below are advisory. |
| 💬 **Approve with suggestions** | No critical findings. High findings exist but are well scoped, low risk and reasonably addressed after merge. |
| ⏳ **Wait for author** | Critical findings, or several highs that need author clarification, a design discussion or non-trivial rework. |
| ❌ **Reject** | A fundamental design flaw, a data-safety risk (loss or corruption possible), a required migration that is missing, or a violation of core architecture principles. |

**Mergeable is not enablement-ready.** A change can be safe to merge while still carrying work that must happen before the feature is switched on. Say both, separately.

**Not yet enabled is not a discount.** Judge the PR at the state it will be in when live.
