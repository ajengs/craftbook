#!/usr/bin/env python3
"""Aggregate reviewer JSON into a ranked, deduplicated findings report.

Usage:
    python aggregate_findings.py <dir-of-reviewer-json> \
        [--json-out aggregated.json] [--md-out findings.md]

Each *.json file in <dir> is one reviewer's response, matching the schema in
references/reviewer-prompts.md. Files may contain a bare JSON object or a
markdown ```json fence around one -- both are accepted, since agents fence
their output by habit.

The script does the mechanical work only: merge, rank, count, assign IDs,
render. Severity judgement stays with the model, which is why weak
blast_radius values are reported as warnings rather than silently downgraded.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}
SEVERITY_LABEL = {
    "critical": "🔴 Critical",
    "high": "🟠 High",
    "medium": "🟡 Medium",
    "low": "🔵 Low",
    "info": "ℹ️ Info",
}
ID_PREFIX = {"critical": "C", "high": "H", "medium": "M", "low": "L", "info": "I"}

# Findings are grouped by what the reader has to DO about them, not by severity.
# Severity says how bad; action class says when it lands on someone's plate — and
# that is the question a reader actually opens the document with. Two medium
# findings can be a production blocker and a missing test; grouping them as peers
# forces the reader to re-derive the distinction for every entry.
ACTION_ORDER = ["blocks-merge", "before-enablement", "verification", "cleanup"]
ACTION_RANK = {a: i for i, a in enumerate(ACTION_ORDER)}
ACTION_HEADING = {
    "blocks-merge": "🚫 Blocks merge",
    "before-enablement": "⚠️ Fix before production enablement",
    "verification": "🧪 Verification gaps",
    "cleanup": "🧹 Cleanup (non-blocking)",
}
# Short phrases for the outcome line at the top of the document.
ACTION_PHRASE = {
    "blocks-merge": "blocking merge",
    "before-enablement": "to fix before production enablement",
    "verification": "test/verification gaps",
    "cleanup": "cleanup items",
}
# These two classes carry the reader's actual work, so they get full narrative.
# The rest get one line each: enough to find them, not enough to slow the read.
DETAILED_CLASSES = {"blocks-merge", "before-enablement"}

# Phrases that signal a blast radius was written to satisfy the schema rather
# than to describe a real scenario.
VAGUE_PATTERNS = [
    r"\bcould cause\b",
    r"\bmay cause\b",
    r"\bmight\b",
    r"\bpotential(ly)? (issue|problem|impact)",
    r"\bunclear\b",
    r"\bpossibl[ey]\b",
    r"\bin theory\b",
    r"\btheoretical",
    r"\bsome (issues|problems)\b",
]
MIN_BLAST_RADIUS_CHARS = 60

FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


# ---------------------------------------------------------------- loading


def load_reviewer(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = FENCE_RE.search(raw)
    if match:
        return json.loads(match.group(1))
    # last resort: first balanced-looking object in the file
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        return json.loads(raw[start : end + 1])
    raise ValueError(f"{path.name}: no JSON object found")


# ---------------------------------------------------------------- merging


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def normalize_file(path: str) -> str:
    return (path or "").replace("\\", "/").strip().lower()


def dedupe(findings: list[dict]) -> tuple[list[dict], list[str]]:
    """Merge identical findings; return (merged, warnings)."""
    merged: dict[tuple, dict] = {}
    order: list[tuple] = []

    for finding in findings:
        key = (
            normalize_file(finding.get("file", "")),
            finding.get("line"),
            normalize_title(finding.get("title", "")),
        )
        existing = merged.get(key)
        if existing is None:
            finding["reviewers"] = [finding.get("reviewer", "unknown")]
            merged[key] = finding
            order.append(key)
            continue

        # Keep the higher severity; carry the other reviewer's wording across so
        # the extra perspective is not lost.
        keep, drop = existing, finding
        if SEVERITY_RANK.get(finding.get("severity"), 9) < SEVERITY_RANK.get(
            existing.get("severity"), 9
        ):
            keep, drop = finding, existing
            keep["reviewers"] = existing.get("reviewers", [])
            merged[key] = keep

        reviewer = drop.get("reviewer", "unknown")
        if reviewer not in keep["reviewers"]:
            keep["reviewers"].append(reviewer)
        drop_desc = (drop.get("description") or "").strip()
        if drop_desc and drop_desc not in (keep.get("description") or ""):
            keep["description"] = (
                keep.get("description", "").rstrip()
                + f"\n\n*Also raised by {reviewer}:* {drop_desc}"
            )
        if not keep.get("blast_radius") and drop.get("blast_radius"):
            keep["blast_radius"] = drop["blast_radius"]

    result = [merged[k] for k in order]

    # Different titles at the same location are often the same defect seen
    # through two lenses. Too risky to auto-merge; worth a human glance.
    warnings: list[str] = []
    by_location: dict[tuple, list[dict]] = defaultdict(list)
    for finding in result:
        by_location[
            (normalize_file(finding.get("file", "")), finding.get("line"))
        ].append(finding)
    for (file, line), group in by_location.items():
        if len(group) > 1 and file:
            titles = " | ".join(f.get("title", "?") for f in group)
            warnings.append(
                f"Same location {file}:{line} has {len(group)} findings "
                f"with different titles — check for a duplicate: {titles}"
            )
    return result, warnings


def check_blast_radius(findings: list[dict]) -> list[str]:
    warnings = []
    for finding in findings:
        if finding.get("severity") not in ("critical", "high"):
            continue
        blast = (finding.get("blast_radius") or "").strip()
        title = finding.get("title", "?")
        if not blast:
            warnings.append(
                f"[{finding['severity']}] '{title}' has NO blast_radius — "
                "downgrade it or write one."
            )
            continue
        if len(blast) < MIN_BLAST_RADIUS_CHARS:
            warnings.append(
                f"[{finding['severity']}] '{title}' has a very short blast_radius "
                f"({len(blast)} chars) — check it names a real scenario."
            )
        hits = [p for p in VAGUE_PATTERNS if re.search(p, blast, re.IGNORECASE)]
        if hits:
            warnings.append(
                f"[{finding['severity']}] '{title}' has a hedged blast_radius "
                f"(matched {hits[0]!r}) — concrete or demote."
            )
    return warnings


def default_action_class(finding: dict) -> str:
    """Fallback when the caller did not classify a finding.

    Deliberately crude — the real call needs merge context (is this a stacked
    draft PR? is the feature flag-gated?) that only the orchestrating agent has.
    This exists so an unclassified finding lands somewhere sane instead of being
    dropped, and the warning tells the caller to classify it properly.
    """
    severity = finding.get("severity")
    category = (finding.get("category") or "").lower()
    if severity in ("critical", "high"):
        return "blocks-merge"
    if "test" in category or "coverage" in category:
        return "verification"
    if severity == "medium":
        return "before-enablement"
    return "cleanup"


def apply_action_classes(findings: list[dict]) -> list[str]:
    warnings = []
    for finding in findings:
        raw = (finding.get("action_class") or "").strip().lower()
        if raw in ACTION_RANK:
            finding["action_class"] = raw
            continue
        guess = default_action_class(finding)
        finding["action_class"] = guess
        finding["action_class_inferred"] = True
        warnings.append(
            f"'{finding.get('title', '?')}' had no valid action_class "
            f"(got {raw or 'nothing'!r}) — guessed {guess!r}. Classify it "
            "explicitly: the grouping is what makes the document actionable."
        )
    return warnings


def sort_findings(findings: list[dict]) -> list[dict]:
    return sorted(
        findings,
        key=lambda f: (
            ACTION_RANK.get(f.get("action_class"), 9),
            SEVERITY_RANK.get(f.get("severity"), 9),
            normalize_file(f.get("file", "")),
            f.get("line") if isinstance(f.get("line"), int) else 10**9,
        ),
    )


def assign_ids(findings: list[dict]) -> None:
    counters: dict[str, int] = defaultdict(int)
    for finding in findings:
        severity = finding.get("severity", "info")
        counters[severity] += 1
        finding["display_id"] = f"{ID_PREFIX.get(severity, 'X')}{counters[severity]}"


# ---------------------------------------------------------------- rendering


def render_finding(finding: dict, condensed: bool) -> str:
    file = (finding.get("file") or "?").replace("\\", "/")
    line = finding.get("line")
    loc = f"{file}:{line}" if line is not None else file
    fid = finding["display_id"]
    title = finding.get("title", "(untitled)")
    severity = finding.get("severity", "info")

    if condensed:
        # One line, and severity stays visible because the group heading no
        # longer carries it.
        return f"- **[{fid}]** {title} — `{loc}` · {SEVERITY_LABEL[severity]}"

    reviewers = finding.get("reviewers", [])
    meta = f"`{loc}` · {SEVERITY_LABEL[severity]} · {finding.get('category', 'n/a')}"
    if len(reviewers) > 1:
        meta += f" · flagged by {', '.join(reviewers)}"

    parts = [f"#### [{fid}] {title}", meta, ""]
    description = (finding.get("description") or "").strip()
    if description:
        parts.append(description)
    if finding.get("blast_radius"):
        parts.append(f"\n**Impact:** {finding['blast_radius'].strip()}")
    if finding.get("suggestion"):
        parts.append(f"\n**Fix:** {finding['suggestion'].strip()}")
    snippet = finding.get("code_snippet")
    if snippet:
        parts.append(f"\n```\n{snippet.strip()}\n```")
    return "\n".join(parts)


def render_outcome(findings: list[dict]) -> str:
    """The one-line answer, for the top of the document.

    A reader opens a review to learn whether they can merge and what they owe
    before shipping. Making them read the findings to reconstruct that is the
    single biggest cost in a long review, so it is stated first and the rest of
    the document becomes supporting evidence.
    """
    by_class = defaultdict(list)
    for finding in findings:
        by_class[finding["action_class"]].append(finding)

    clauses = []
    for action in ACTION_ORDER:
        group = by_class.get(action)
        if group:
            clauses.append(f"**{len(group)}** {ACTION_PHRASE[action]}")
    if not clauses:
        return "No findings."
    if not by_class.get("blocks-merge"):
        clauses.append("nothing blocking merge")
    return " · ".join(clauses)


def render(findings: list[dict], summaries: list[tuple], budgets: list[tuple]) -> str:
    counts = {s: 0 for s in SEVERITY_ORDER}
    for finding in findings:
        severity = finding.get("severity", "info")
        if severity in counts:
            counts[severity] += 1

    out: list[str] = [render_outcome(findings), ""]

    if budgets:
        # A coverage gap qualifies the outcome above, so it belongs with it
        # rather than buried in the appendix.
        out.append("> ⚠️ **Not fully checked** (reviewer tool budget exhausted):")
        for name, areas in budgets:
            out.append(f"> {name}: {', '.join(areas)}")
        out.append("")

    for action in ACTION_ORDER:
        group = [f for f in findings if f.get("action_class") == action]
        if not group:
            continue
        out.append(f"## {ACTION_HEADING[action]}\n")
        # Detail where the reader has work to do; one-liners elsewhere. A
        # critical or high finding always gets detail wherever it was filed.
        condensed_group = action not in DETAILED_CLASSES
        rendered = [
            render_finding(
                f,
                condensed=condensed_group
                and f.get("severity") not in ("critical", "high"),
            )
            for f in group
        ]
        if condensed_group:
            out.append("\n".join(rendered))
        else:
            out.append("\n\n".join(rendered))
        out.append("")

    # Reference material last: useful for auditing the review, not for acting on it.
    out.append("---\n")
    out.append("<details>\n<summary>Review metadata</summary>\n")
    out.append("| Severity | Count |")
    out.append("|---|---|")
    for severity in SEVERITY_ORDER:
        out.append(f"| {SEVERITY_LABEL[severity]} | {counts[severity]} |")
    out.append("")
    if summaries:
        for name, summary in summaries:
            out.append(f"- *{name}*: {summary}")
        out.append("")
    out.append("</details>")

    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", help="Directory of reviewer *.json files")
    parser.add_argument("--json-out", help="Where to write aggregated.json")
    parser.add_argument("--md-out", help="Where to write the rendered findings body")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    files = sorted(input_dir.glob("*.json"))
    files = [f for f in files if f.name not in ("aggregated.json",)]
    if not files:
        print(f"No reviewer JSON found in {input_dir}", file=sys.stderr)
        return 1

    all_findings: list[dict] = []
    summaries: list[tuple] = []
    budgets: list[tuple] = []

    for path in files:
        try:
            data = load_reviewer(path)
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"WARNING: skipping {path.name}: {exc}", file=sys.stderr)
            continue
        reviewer = data.get("reviewer") or path.stem
        if data.get("reviewer_summary"):
            summaries.append((reviewer, data["reviewer_summary"]))
        if data.get("budget_exceeded"):
            budgets.append((reviewer, data["budget_exceeded"]))
        for finding in data.get("findings") or []:
            finding.setdefault("reviewer", reviewer)
            severity = (finding.get("severity") or "info").lower()
            finding["severity"] = severity if severity in SEVERITY_RANK else "info"
            all_findings.append(finding)

    merged, dup_warnings = dedupe(all_findings)
    blast_warnings = check_blast_radius(merged)
    class_warnings = apply_action_classes(merged)
    merged = sort_findings(merged)
    assign_ids(merged)

    body = render(merged, summaries, budgets)

    if args.md_out:
        Path(args.md_out).write_text(body, encoding="utf-8")
    else:
        print(body)

    counts = {s: sum(1 for f in merged if f["severity"] == s) for s in SEVERITY_ORDER}
    action_counts = {
        a: sum(1 for f in merged if f["action_class"] == a) for a in ACTION_ORDER
    }
    payload = {
        "reviewers": [name for name, _ in summaries],
        "reviewer_summaries": dict(summaries),
        "budget_exceeded": dict(budgets),
        "counts": counts,
        "action_counts": action_counts,
        "outcome_line": render_outcome(merged),
        "total_raw": len(all_findings),
        "total_after_dedupe": len(merged),
        "findings": merged,
        "warnings": blast_warnings + class_warnings + dup_warnings,
    }
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print(
        f"\n{len(all_findings)} raw findings -> {len(merged)} after dedupe  "
        + "  ".join(f"{s}={counts[s]}" for s in SEVERITY_ORDER)
        + "\n"
        + "  ".join(f"{a}={action_counts[a]}" for a in ACTION_ORDER),
        file=sys.stderr,
    )
    for warning in blast_warnings + class_warnings + dup_warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
