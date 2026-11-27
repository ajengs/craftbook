# Google Chat notifications

Notifications are optional and best effort. Two things must hold before anything is sent:

1. `ARTIFEX_GOOGLE_CHAT_WEBHOOK_URL` is set in the process environment that runs the router and the umbrella's commands. The value must be a Google Chat incoming webhook URL on `chat.googleapis.com`; do not put it in an argument, repository file, `state.json`, or a transcript.
2. The user authorized notifications for **this** initiative, recorded in its `state.json` with `artifex_state.py notifications --status authorized` (`SKILL.md`, Notification authorization). The sender reads the record from the initiative folder on every send and returns `not_authorized` without network or database work when it is missing or `declined`. The variable is machine-wide, so it never stands for consent, and a yes recorded for one initiative does not carry over to another.

Unset the variable, or record `notifications --status declined`, to stop notifications. Disabled and unauthorized calls do not create a delivery database.

## Who sends what

The router sends lifecycle notices only after it commits a confirmed `started` event or a validated terminal result. Spawn dispatches, dry runs, `next`, reads, and replay do not send. A blocked or decision-needed terminal result produces its outcome notice and a separate blocker notice. Existing history is not backfilled.

The router only sees P3–P6 runs, so the umbrella covers everything else. While notifications are authorized, the umbrella sends a notice, in the same turn and before acting on it, for:

- every session it starts that the router does not record: P1, P2 and D1 (`--kind started`);
- every message it receives from another session that does not end in a router `result` call: P1, P2 and D1 checkpoints (`--kind checkpoint`), approval requests (`--kind approval-needed`), blockers and requests for the user's input (`--kind blocker`), and P3–P6 messages other than a finalized result path, such as a pushed-tests notice or a worker asking for the user;
- an approval or blocker the umbrella itself raises to the user.

A result path the umbrella passes to `result` is already notified by the router; don't send it again. Use the sending session's name in `--task`, and put what the message asks or reports in `--summary` in one sentence, with the document link in `--source` when there is one.

The key is the semantic event identity and must stay the same when the same message is reconciled again: `<session name>/<kind>/<artifact and revision, or issue episode>`. Approval keys include artifact identity and revision; blocker keys identify the issue episode. Do not use timestamps or changing prose as keys. A planning session with no milestone yet uses `--milestone none`.

```powershell
$initiative = '<initiative artifact folder>'
python skills/artifex/scripts/artifex_notify.py --dir $initiative --ticket TICKET --milestone none --key 'TICKET P1 research/started' --kind started --task 'TICKET P1 research' --summary 'Research session started'
python skills/artifex/scripts/artifex_notify.py --dir $initiative --ticket TICKET --milestone M1 --key 'TICKET M1 P2/checkpoint/implementation-handoff/revision-2' --kind checkpoint --task 'TICKET M1 P2' --summary 'Implementation handoff revision 2 written; implementation starting'
python skills/artifex/scripts/artifex_notify.py --dir $initiative --ticket TICKET --milestone M1 --key 'TICKET M1 P2/approval/specifications/revision-3' --kind approval-needed --task 'TICKET M1 P2' --summary 'Review and approve specification revision 3' --source 'https://example.invalid/specifications'
python skills/artifex/scripts/artifex_notify.py --dir $initiative --ticket TICKET --milestone M1 --key 'TICKET D1/blocker/database-access/episode-1' --kind blocker --task 'TICKET D1' --summary 'Database access is blocked; provide a test account'
```

A `not_authorized` or `disabled` output is expected when the user said no or the variable is unset; don't retry or ask again because of it.

## Delivery limits

Each initiative artifact folder owns one `notifications.sqlite3`. Event keys are reserved transactionally before HTTP; a failure, crash, restart, or ambiguous timeout does not create a new budget for the same key. Delivery allows at most two attempts, uses a two-second socket timeout and a six-second total wall budget, spaces attempts by at least one second, and limits the initiative to ten attempts per rolling minute. A retry honors a fitting `Retry-After` value. Redirects are refused. Suppressed events are recorded, not queued.

SQLite failure skips sending and emits a short sanitized warning; it never changes workflow authority or `run.jsonl`. Missing configuration or authorization performs no network or database work. A crash after reservation can lose an alert. A timeout followed by the one retry can duplicate a message if Chat accepted the first request. Rate limits shared with other senders can still drop alerts. These rules bound duplicates and load; they do not promise delivery or exactly-once behavior.

Messages contain the event kind, ticket, milestone, task, explicitly supplied summary, and UTC plus machine-local time with numeric offset and timezone label. They are capped at 4 KiB. Webhook credentials, response bodies, and raw exception strings are not included in messages or diagnostics. No transcript scraping, stall detection, background scheduler, resend queue, interactive approvals, or other provider is involved.
