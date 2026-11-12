# Google Chat notifications

Notifications are optional and best effort. Set `ARTIFEX_GOOGLE_CHAT_WEBHOOK_URL` in the process environment that runs the router. The value must be a Google Chat incoming webhook URL on `chat.googleapis.com`; do not put it in an argument, repository file, `state.json`, or a transcript. Unset the variable to disable notifications. Disabled calls do not create a delivery database.

The router sends lifecycle notices only after it commits a confirmed `started` event or a validated terminal result. Spawn dispatches, dry runs, `next`, reads, and replay do not send. A blocked or decision-needed terminal result produces its outcome notice and a separate blocker notice. Existing history is not backfilled. P1, P2, and D1 are not observed by the router; the umbrella sends their explicit lifecycle notices.

The umbrella can send a planning, approval, or blocker notice explicitly. The key is the semantic event identity and must stay the same when the same request is repeated. Approval keys should include artifact identity and revision; blocker keys should identify the issue episode. Do not use timestamps or changing prose as keys.

```powershell
$env:ARTIFEX_GOOGLE_CHAT_WEBHOOK_URL = '<Google Chat incoming webhook URL>'
python skills/artifex/scripts/artifex_notify.py --dir 'D:/Notes/Craftbook/ART-20' --ticket ART-20 --milestone M1 --key 'p2/run-abc/started' --kind started --task 'P2 analysis' --summary 'Analysis session started'
python skills/artifex/scripts/artifex_notify.py --dir 'D:/Notes/Craftbook/ART-20' --ticket ART-20 --milestone M1 --key 'approval/specs-r3' --kind approval-needed --task 'specs approval' --summary 'Review and approve specs revision r3' --source 'https://example.invalid/specs'
python skills/artifex/scripts/artifex_notify.py --dir 'D:/Notes/Craftbook/ART-20' --ticket ART-20 --milestone M1 --key 'blocker/database-access/episode-1' --kind blocker --task 'P2 analysis' --summary 'Database access is blocked; provide a test account'
Remove-Item Env:ARTIFEX_GOOGLE_CHAT_WEBHOOK_URL
```

Each initiative artifact folder owns one `notifications.sqlite3`. Event keys are reserved transactionally before HTTP; a failure, crash, restart, or ambiguous timeout does not create a new budget for the same key. Delivery allows at most two attempts, uses a two-second socket timeout and a six-second total wall budget, spaces attempts by at least one second, and limits the initiative to ten attempts per rolling minute. A retry honors a fitting `Retry-After` value. Redirects are refused. Suppressed events are recorded, not queued.

SQLite failure skips sending and emits a short sanitized warning; it never changes workflow authority or `run.jsonl`. Missing configuration performs no network or database work. A crash after reservation can lose an alert. A timeout followed by the one retry can duplicate a message if Chat accepted the first request. Rate limits shared with other senders can still drop alerts. These rules bound duplicates and load; they do not promise delivery or exactly-once behavior.

Messages contain the event kind, ticket, milestone, task, explicitly supplied summary, and UTC plus machine-local time with numeric offset and timezone label. They are capped at 4 KiB. Webhook credentials, response bodies, and raw exception strings are not included in messages or diagnostics. No transcript scraping, stall detection, background scheduler, resend queue, interactive approvals, or other provider is involved.
