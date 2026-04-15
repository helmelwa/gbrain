---
version: 1.0.0
---

# HEARTBEAT.md — Operational Cadence

## Active Schedules (Telegram)

### Morning Briefing — 09:00 Munich (07:00 UTC)
- Today's tasks and priorities
- New entries in GBrain since last briefing
- Active reminders and pending items
- Any overnight signals that need attention

### Evening Summary — 17:00 Munich (15:00 UTC)
- What was accomplished today
- What was moved / deferred
- Open threads for tomorrow
- Any new information that should be captured in brain

## Cron Timezone

**Server:** Asia/Shanghai (CST, UTC+8)
**User:** Munich, Germany (CEST, UTC+2)
**Offset calculation:** Munich time - 2 hours = server cron schedule

| User Time | Server Time | Job |
|-----------|-------------|-----|
| 09:00 Munich | 07:00 UTC | Morning briefing |
| 17:00 Munich | 15:00 UTC | Evening summary |

## Cron Expression Reference

```
# Morning briefing (07:00 UTC = 09:00 CEST summer)
0 7 * * *    # 09:00 Munich (CEST) during summer

# Evening summary (15:00 UTC = 17:00 CEST summer)
0 15 * * *   # 17:00 Munich (CEST) during summer
```

## Signal Processing

- Every inbound Telegram message: signal-detector fires in parallel
- Every inbound message: brain-ops lookup → enrich → write loop
- Brain-first: check GBrain before any external API call

## Maintenance

- Weekly (Sunday): `gbrain sync --repo ~/brain && gbrain embed --stale`
- Weekly (Sunday): `gbrain doctor --json` — health check
- Brain grows as a side effect of operations — no separate maintenance sessions
