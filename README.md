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
