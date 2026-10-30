- when P5 or P6 fails, send report to umbrella. it should create a new session P7-debugging with references to verification report and findings.
- considering to use one session for all. just auto compact often.
- I still kinda like it that we can do parallel work on different sessions though. currently working on P2 for M2 while M1 is being worked on by its P3.
- actually it might not matter for P3-P5 to be done on umbrella's subagents. just need to keep P1 and P2 separate by default for now. and maybe P6. and debugging session.
- ensure no worktree creation unless requested
- p2 could also propose code architecture/design when new entity is introduced, or changes are big.
- might need to introduce another phase for UI elements design
- should p2 that has UI elements also create and record mockup? currently it is stored on codex temp
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
- ah the feedback thread on the PR remains unresolved. somehow P3 got instruction to keep it that way?
- somehow push and open PR are not authorized on P3. not sure if it's Codex quirks
- P3 also got "Git branch creation hit the session’s read-only .git restriction;"
    oh but then it went immediately to "I’ll request elevated execution for that authorized step so it can proceed from the approved base." and worked
