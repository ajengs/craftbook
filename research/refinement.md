- while working on P2 M2, somehow verification contract creation is blocked 
    ```
    Recorded the M2 P2 checkpoint in initiative STATE revision 53 and M2 STATE revision 8. There are no remaining M2 design blockers. The implementation handoff and later verification artifacts await umbrella confirmation that M1’s API/contracts are stable and an M2 base is safe.
    ```
    I think it's good that the agent successfully detect dependency. but the default behavior should be escalate to user. 
    in this particular case, it is correct though. since frontend needs API contract. it was more like planning issue. before starting M1 on backend, we should define API contract first to remove hard dependency.
- umbrella session works well on codex though. approval is done centralized on umbrella, even though the requested permissions are for other sessions. though funnily, it is not really necessary for codex since I don't need status page anyway. I can control the sessions just fine on phone.
- lol why the fuck does P3 relays the PR feedback from its polling to umbrella first? 
    oohhh it's holding edits since P4 round 3 is still running. And it queued the requested edits until P4 is done. This round had no findings and gave a pass. So idk if the PR feedback fix will be queued before, after, or together with P4 findings.
    after the PR feedback fix though, P4 incremental review was triggered again. I guess this is excluded from the max 3 rounds review.


Known issues: 

permissions 
On codex somehow umbrella always fails to listen to its subagents
Sometimes sub session failed to send messages to umbrella because permission issue
I need to review the transcript on sub sessions and sub agents. Via GUI ofc


artifex 
for debugging
- create a document that can be annotated on side viewer for diagnosis, if no side viewer annotation is possible (claude), crate an artifact document
- on evidence, mention the sources (artifacts, metrics, logs, traces, P5 reports, etc)

on benchmark

one new contract document
- blocking inputs from me
- covering ver 9-12
- the question
- schedule (column: step, config and workload, concrete actions (API, scripts, browser interactions, etc), evidence, estimated time)
  - preparation
  - rehearsal
  - measure empty baseline M0
  - measure load almost limit M1
  - measure load over limit m2
  - sweep and park
  - collector hold
  - refill M4
  - completion M5
  - restore
  - report
- decision rule table: observation, decision
- measurements: output, exact source and concrete methods,  purpose
- env and control:
  - target TBD
  - required/recommended capacity (measured based on planned workload and past measurement on https://link.orangelogic.com/Tasks/42CVRA
  - build: which branch and commit
  - fixture/data needed (seeded or uploaded)
  - configuration changes
  - consumers/indexing pause
  - port forwards
  - noise/Shared / uncontrolled conditions
- validity and limitations
- human actions
- permission needed for autonomous runs



