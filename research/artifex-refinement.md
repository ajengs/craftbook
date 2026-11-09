# Artifex Refinement
## Token efficiency
- Create PR somehow uses lots of token?

## Sessions/Agents coordination & management
- Consider use one session for all, just auto compact often.
- I need to ensure that Artifex can continue on an entirely new session or even provider change. Tested once, it worked so far. Needs more verification.
- On status page skill, ensure that timestamp also shows GMT+7. Also how many ticks on fast mode before it goes back to hourly. (still need to calibrate token efficiency on status page)
- Need to decide  which session is responsible for checking and addressing PR feedback. In current working model, P3 will poll and address them. But it might cause bloated context. Though a fresh subagent without proper context would be costly too since he would try to build the context probably from scratch. P2 is a candidate. Or an entirely separate session. 
- It might be a good idea to ensure that we have a little bit more state recorded so feedback handler do not start from scratch, knows the design background, but preferably independent of P3 and P4. 

## Workflow
- When P5 or P6 fails, send report to umbrella. It should create a new session D1-debugging with references to verification report and findings.
- Refine  simplified workflows for debugging/investigation.
- P2 could also propose code architecture/design when new entity is introduced, or changes are big. Or separate phase for codebase design. Or we can also include that in P2, after specs. 
- Might need to introduce another phase for UI elements design.
- Should P2 that has UI elements also create and record mockup? Currently it is stored on Codex temp.
- What would define phase closure? 
    > I’ll follow the Artifex closure process, verify the initiative’s final state and artifacts, then write a concise closure report in the existing ART-1 folder.
- Need to check PR review handler. Who's going to monitor it? P3? P4?
- On code change caused by additional/manual review round, only trigger iterative P4 once, and scoped P5 once without full code review.
- Over time, we can have verification scenarios repository so agent can detect which module changes need what scenarios.
- Review P4 flow.

## Policy
- Ensure no worktree creation unless requested.
- Somehow push and open PR are not authorized on P3, not sure if it's Codex quirks. Ensure explicit permissions are granted during initialization. Including git branch creation and commit. Also build and test ofc. PR CI pipelines reads, thread reads, thread writes, resolve threads, add or remove reviewers.
- Need to ensure we agree on the skills to be used during the execution, especially auto verification and benchmark. Also if possible, reviewer, feedback handler. First, it is to ensure choose the most appropriate tools. Also to reduce the cost of tools exploration by agents. We could also have a local .tools file that Artifex can refer.
- For P2, needs an agent that knows how to write specs in GWT formats. Probably can use "42D1VO milestone 1 specs: Redis queue overflow to SQL" older version vs latest as examples.

