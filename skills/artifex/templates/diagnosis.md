# Diagnosis — <bug>

Source: <ticket link | P5 finding in milestone <id>>
Seen on: <version, head or environment>
Path: <direct | reproduced | confirm>
Status: <draft | root cause approved <revision> | fix approach approved <revision>>

## Symptom
What was reported, and the behavior expected instead.

## Evidence collected
One entry per source, for the reported instance and time window or version:
- <type: ticket | metric | trace | log | debug recording | profiler capture | dump | P5 report | screenshot | other> | <link or path> | <instance, window or head> | <what it showed>

Unavailable or not checked: <list, and why>.

## Reproduction
Run: <command or steps>. Kind: <automatic | manual | none>. Files: <paths in the milestone folder>.
Result: <red, with the exact output that matches the symptom>. Minimised: <what was cut and why the rest is load-bearing>.

## Root cause
What is wrong, where (files, methods) and why it produces the symptom.
Evidence: <observed: the probe or measurement that flips the result, with its link or path | inferred: why, and from which sources above>.
Ruled out: <hypotheses and what disproved each, with sources>.

## Fix approach
The exact change: files and methods, and what stays as it is.
Regression test: <where it asserts the symptom | no correct seam, and why>.
Same cause elsewhere: <sibling entry points, or none>.

## Path criteria
Which conditions for the path are met and how they are shown. Confidence: <high | medium | low> and what would change it. For Confirm: what the user must approve or supply.

## Limitations
What was not reproduced, tried or verified.
