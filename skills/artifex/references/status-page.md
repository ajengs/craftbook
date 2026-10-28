# Remote status page

Create this **only when the user asks for a remote status page**. It is not part of the default flow. It gives the user phone access to the umbrella when Remote Control isn't available: a cloud session can't reach local notes or local sessions, so the page is a Claude Doc the user comments on and the umbrella polls.

## 1. Status page

- Create a Claude Doc titled "<ticket id> status" and open it for the user.
- Add a line under the title: "Last checked: <YYYY-MM-DD HH:MM> UTC (<mode>)".
- Sections, in order:
  - **Now:** the phase, then what's waiting on the user as a checklist, what's in progress, and what's waiting on others.
  - **Sessions:** a table of session | role | state.
  - **Artifacts:** a table of artifact | version | state, with links to the ticket, PR and Claude Docs, plus the path to the local `STATE.md`.
  - **Using this page from your phone:** how to comment and the check cadence below.
- Update the page every time you update `STATE.md`, in the same step. Change only the blocks that changed.
- Record the page URL in the initiative `STATE.md` under decisions.

## 2. Comment polling

The user comments **without @Claude**. An @Claude comment is answered by the phone's own Claude, which can't see `STATE.md` and wanders off searching tools and history. The umbrella picks up plain comments itself.

- Keep a state file next to the rules file, `<scratchpad>/status-page-state.json`, shaped `{"lastSeq": <int>, "lastAnsweredUtc": "<ISO 8601 UTC>", "lastCheckedText": "<text>"}`. When you create it, set `lastSeq` to the doc's current highest comment seq, so old comments aren't replayed.
- Write the polling rules below to `<scratchpad>/status-page-check.md`:
  a. Query utterances under the doc's body node with payload `{"under": <body node>, "afterSeq": lastSeq}`. Take only rows where `actor.via` = "frame" and `payload.value.kind` = "message". Those are comments the user typed. Replies from any Claude, this one or the phone's, show `via` = "mcp" under the user's name, and resolves aren't messages. Ignore the `to` and `answered` fields: the phone's Claude can mark a comment answered. Save `lastSeq` as the highest seq returned, even when nothing qualifies.
  b. None:
     - HOURLY: do nothing and say nothing.
     - FAST: if `lastAnsweredUtc` is unknown or 30 minutes or more ago, switch to HOURLY quietly (step d). Otherwise do nothing.
  c. For each row: if it asks to go back to hourly ("go back to 1 hour", "back to hourly", "slow down"), reply that checks are back to hourly and mark SWITCH_TO=HOURLY. Otherwise act as the umbrella would and reply with a Claude Docs `create` utterance whose parent is the row id. Answer status from `STATE.md` and the linked sessions, and pass instructions to sessions with SendMessage. Ask the user before anything that starts a session, is destructive, or posts to Link or a PR. Keep replies short. After each reply, write the current UTC time to `lastAnsweredUtc`.
  d. Mode switch, keeping exactly one polling job:
     - FAST to HOURLY (a go-back request or the 30-minute quiet drop): CronDelete the fast job and CronCreate "0 * * * *" with the prompt "Read and follow <file>. Mode: HOURLY."
     - HOURLY to FAST (after answering a non-go-back comment): CronDelete the hourly job and CronCreate "*/5 * * * *" with the prompt "Read and follow <file>. Mode: FAST."
  e. After any switch, CronList and delete any duplicate polling job.
- Start in HOURLY mode: CronCreate "0 * * * *", recurring, prompt "Read and follow <file>. Mode: HOURLY."
- Keep each check cheap: one query, plus one write of the last-check time, and nothing else when there's nothing new. These checks run as turns in the umbrella session, and while one runs it delays everything else, including messages from child sessions.
- After every query, replace the "Last checked: ..." line under the page title with "Last checked: <YYYY-MM-DD HH:MM> UTC (<mode>)", by quoting the previous text kept in `lastCheckedText`, so no read is needed. If someone has edited or deleted the line, don't recreate it.

## 3. Keep awake

Call `request_keep_awake` with until "session_idle".

## 4. Tell the user the limits, in one short list

- Cron jobs are session-only, expire after 7 days, and fire only while the session is idle, so replies can lag.
- Keep-awake lets go after about 5 idle minutes, so set Windows sleep to Never while away. A closed lid still sleeps.
- A comment turn can't start a new session; that still needs a card click on the laptop.
- Send one test comment from the phone and confirm a reply before relying on it.
