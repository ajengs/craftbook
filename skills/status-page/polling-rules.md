# Status page check

Copy this file to `<folder>/status-page-check.md` and fill in the three values below. The cron prompt says which mode this run is in, HOURLY or FAST.

- Doc id: <doc id>
- Body node id: <body node id>
- State file: <folder>/status-page-state.json

Each run:

a. Query comments under the body node with payload `{"under": {"object": "node", "id": <body node id>}, "afterSeq": lastSeq}`. Take only rows where `actor.via` = "frame" and `actor.self` is true and `payload.value.kind` = "message". Those are comments the user typed. Replies from any Claude show `via` = "mcp", and resolves aren't messages. Ignore the `to` and `answered` fields: the phone's Claude can mark a comment answered. Save `lastSeq` as the highest seq returned, even when nothing qualifies.

b. If there are none:
   - HOURLY: do nothing and say nothing.
   - FAST: if `lastAnsweredUtc` is empty or 30 minutes or more ago, switch to HOURLY quietly (step d). Otherwise do nothing.

c. For each row: if it asks to go back to hourly ("go back to 1 hour", "back to hourly", "slow down"), reply that checks are back to hourly and set SWITCH_TO=HOURLY. Otherwise act as the session's owner would and reply in the thread: a docs `create` of an utterance whose parent is the thread's first comment (the row's own id when it starts a thread, its `parent` when it is a reply). Start the reply with the direct answer ("Yes.", "No.", the fact), keep it short, and say nothing in chat. Answer status from the state source. Pass instructions to other sessions with SendMessage. Ask the user, and wait for a yes in a comment, before anything that starts a session, creates or uses a worktree, commits or pushes, deletes, or posts to a ticket or PR. After each reply, write the current UTC time to `lastAnsweredUtc`.

d. Mode switch, keeping exactly one polling job:
   - FAST to HOURLY (a go-back request, or the 30-minute quiet drop): `CronDelete` the fast job and `CronCreate` "0 * * * *" with the prompt "Read and follow <this file>. Mode: HOURLY."
   - HOURLY to FAST (after answering a comment that isn't a go-back request): `CronDelete` the hourly job and `CronCreate` "*/5 * * * *" with the prompt "Read and follow <this file>. Mode: FAST."

e. After any switch, `CronList` and delete any duplicate polling job.

f. After every query, replace the "Last checked: ..." line under the page title with "Last checked: <YYYY-MM-DD HH:MM> UTC (<mode>)", quoting the previous text kept in `lastCheckedText` so no read is needed, then store the new text there. If someone has edited or deleted the line, don't recreate it.

Keep each check cheap: one query, one write of the last-check time, and nothing else when there's nothing new. These checks run as turns in the session, and while one runs it delays everything else, including messages from other sessions.
