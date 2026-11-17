# Verification tools and evidence planning

Read during P2/D1 verification planning and before each P5/P6 run. The catalog supplies user-defined candidates; the approved contract selects what a run needs.

## Resolve the local catalog

During **planning**, run the read-only resolver:

```text
python <skill>/scripts/artifex_tools.py resolve --workdir <implementation directory> [--catalog <explicit file>]
```

The resolver uses the implementation Git repository/worktree root (`git rev-parse --show-toplevel`), not the phase chat's current directory. Outside Git, or when Git is unavailable, `--workdir` itself is the root. The directory must exist. Selection order is:

1. An explicitly supplied catalog file. Expand `~`; resolve relative paths against the implementation root. A missing, unreadable or non-file explicit selection is a blocker, never a reason to fall back.
2. `artifex-tools.local.md` at that implementation root.
3. `~/.agents/artifex-tools.local.md` for the executing user.
4. The bundled [tools-catalog.example.md](tools-catalog.example.md), as an unchecked starter only.

Only an absent default file permits fallback. An existing but unreadable or non-file default selection is also a blocker. Resolve one catalog; never merge catalogs silently. Record the returned absolute `path`, `source` and full `sha256` in the contract and handoff. Relative file references *inside* a catalog use the selected catalog's parent directory; resolve selected tool/runbook/skill file references to absolute paths in the handoff. Skill/tool names are capability identifiers, not relative file paths: discover their exact executable references before use. No catalog is required for a self-contained scenario; explicitly record catalog use as not applicable rather than inventing a personal file.

During **execution**, consume the approved pinned identity, without rerunning discovery or selecting a different user's catalog:

```text
python <skill>/scripts/artifex_tools.py check --path <approved absolute path> --sha256 <approved hash>
```

If the file changed, disappeared, or is unreadable, hold affected scenarios and reconcile the selected capabilities and evidence plan. Copying identical bytes to a reachable path is a recorded relocation; a material change in tools, evidence sufficiency or user responsibility needs renewed approval. A new higher-precedence local file does not override an existing approved selection. The helper checks file identity and readability, not Markdown structure or catalog contents. The planning agent must read the selected file and confirm it supplies the capabilities the run needs; an empty or unusable catalog is a planning gap. No fixed Markdown schema is required, and a successful identity check does not prove tool readiness. The user may copy the bundled starter to either local location and add, remove or replace rows.

Local catalogs belong to the user, outside the installed skill. Preserve user edits. Do not require catalog changes to install a skill, and do not overwrite a local file during updates. The craftbook repo ignores its root local catalog; other repositories can keep theirs outside version control or explicitly share one. Catalog references do not grant permission, install software, execute commands, or prove readiness. Read the actual selected skill before invoking it and preserve its prerequisites and scope.

## Plan each run

Use the contract's Tools and evidence by run table, including separate rows when scenarios need different tools or artifacts. Record:

- Category and scenario IDs: `auto_agent`, `manual_agent`, or `manual_user`.
- Exact tool/skill reference (local skill path, connector tool name, executable or documented entry point), target instance/environment and why it is needed.
- Artifacts and why each is needed to evaluate the pass condition; mark required or optional. Select evidence that distinguishes the expected behavior from failure, rather than collecting everything in the catalog.
- Readiness status, evidence of the check, when/where it was checked, and gap action/owner. Separate collector readiness from analyzer readiness: a working profiler does not prove its snapshot can be analyzed.
- For user interactions: agent preparation, exact user action/observation, collection start/stop responsibility, resume signal and verification check. A manual agent run needs only the explicit start trigger, not user operation of the workload.

The handoff adds executable steps, collector timing, output paths and cleanup. Start collectors early enough to cover the measured action. Correlate captures using scenario, head/build, instance, timestamps/timezone and workload. Preserve raw files separately from derived tables. Dumps and traces can be large or contain secrets: keep them in the agreed evidence location with appropriate access, redact exported HAR credentials, and record retention/transfer constraints when relevant.

## Readiness statuses

| Status | Meaning / next action |
|---|---|
| Available and ready to use | Selected capability exists; required target access, runtime, permissions, fixture/output location and a proportionate non-destructive preflight have been checked. Cite the check. This is not a successful scenario run. |
| Needs adjustment | Capability exists but needs named configuration, adaptation or setup. Record action and owner. |
| Missing / need to be added | Required skill, tool, analyzer or supported capability was not found. Name what must be added or propose an equivalent fallback. |
| Blocked | Capability exists but access, environment, dependency or authorization prevents this run. State the blocker and owner. |
| Unchecked | Not verified in the target environment. An installed skill's name is insufficient evidence of readiness. |

Recheck selected dependencies before execution, especially after environment or tool changes. An unready required dependency prevents that scenario from passing; resolve it, use an approved equivalent, or report blocked/inconclusive. An optional collector failure is a reported limitation unless its evidence was needed for the pass condition. Do not silently downgrade required evidence or change categories to bypass a blocker. Material changes to workload, pass conditions, evidence sufficiency or user responsibility require reconciliation and approval of the affected contract.

## Record the run

Update the verification report with planned versus actually used tools, current readiness, artifact paths/query links and collection status (`collected`, `partial`, `missing`, or `not applicable` with reason). Readiness and collection are separate: ready does not mean collected. Explain what missing evidence prevents concluding; do not call it a pass on confidence. Resume manual user scenarios only after the requested interaction is actually observed or supplied, attributed to its source. Return the existing router outcomes; a blocked/incomplete scenario is inconclusive rather than a fabricated pass.
