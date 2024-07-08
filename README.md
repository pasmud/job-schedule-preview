# job-schedule-preview

Preview the next occurrences of a five-field cron expression. The tool works offline and never executes scheduled jobs.

## UTC preview from Python

```python
from datetime import UTC, datetime
from job_schedule_preview import next_occurrences, parse_cron

# Fictional sample report schedule: daily at 08:15 UTC.
schedule = parse_cron("15 8 * * *")
after = datetime(2030, 1, 1, 8, 15, tzinfo=UTC)
for instant in next_occurrences(schedule, after=after, count=2):
    print(instant.isoformat())
```

The starting instant is exclusive, so the example prints January 2 and 3 at 08:15 UTC.

## Supported cron syntax

Use exactly five whitespace-separated fields, in this order:

| Field | Values |
| --- | --- |
| Minute | 0–59 |
| Hour | 0–23 |
| Day of month | 1–31 |
| Month | 1–12 |
| Day of week | 0–7 (0 and 7 are Sunday, 1 is Monday) |

Each field accepts `*`, a number, an inclusive ascending range (`9-17`), or a comma-separated list of numbers and ranges (`1,3-5`). Steps (`*/15`, `9-17/2`) count from the wildcard's field minimum or the range's start. A stepped range can appear in a list; a wildcard cannot. Use one or two ASCII decimal digits per number, and steps from 1 to 99. Overlapping entries do not create duplicate occurrences.

Minute, hour and month must all match. If neither day field starts with `*`, **either** day field may match. If either starts with `*` (including `*/n`), **both** must match. For example, a fictional `0 9 15 * 1` schedule runs at 09:00 on the 15th and on Mondays, once if both apply. `0 9 */2 * 1` matches only Mondays on odd-numbered days of the month.

Named months/weekdays, wraparound ranges, steps on single numbers, seconds/year fields, macros such as `@daily`, and extensions such as `L`, `W`, `#` or `?` are unsupported. Calendar dates that do not exist never match.
