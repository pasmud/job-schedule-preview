# job-schedule-preview

Preview the next occurrences of a five-field cron expression. The tool works offline and never executes scheduled jobs.

## Installation

With Python 3.11 or later, install from the repository root in a virtual environment:

```sh
python -m pip install .
```

Installation includes the `tzdata` fallback for systems without an IANA database. After installation, previews need no network access.

## CLI

This fictional report schedule hits 01:30 twice during a fall transition:

```sh
job-schedule-preview '30 1 * * *' --zone America/New_York \
  --after 2024-11-03T00:00:00-04:00 --count 2
```

```text
2024-11-03T01:30:00-04:00	2024-11-03T05:30:00Z
2024-11-03T01:30:00-05:00	2024-11-03T06:30:00Z
```

Quote the cron expression so the shell does not expand `*`. `--zone` requires an IANA identifier such as `UTC` or `America/New_York`; the schedule never uses an implicit machine zone. `--after` requires `YYYY-MM-DDTHH:MM[:SS[.ffffff]]` followed by `Z` or a numeric offset (`±HH:MM`). Neither argument defaults to the machine clock or local time.

By default `--after` is exclusive. Pass `--include-start` to include a match exactly at that instant. During the fall transition above, `--after 2024-11-03T01:30:00-05:00 --include-start` starts with the second 01:30; the first one is already in the past relative to that offset.

`python -m job_schedule_preview` accepts the same arguments and can also be run from the repository root if time-zone data is available.

Text output has no header: one occurrence per line, local timestamp with offset followed by UTC, separated by a tab. `--format json` instead prints one object containing `zone`, `after_utc`, `requested_count`, `search_days`, `complete`, and an `occurrences` array of `{ "local": "...", "utc": "..." }` objects. `complete` means the requested count was reached within the window. With `--include-start`, the JSON also contains `"include_start": true`.

For a fictional job that runs only on leap day, a short preview can legitimately return no matches:

```sh
python -m job_schedule_preview '0 9 29 FEB *' --zone UTC \
  --after 2030-01-01T00:00Z --search-days 30 --format json
```

A longer horizon can find the next leap day. Set `--count 1` when you only need the next occurrence:

```sh
python -m job_schedule_preview '0 9 29 FEB *' --zone UTC \
  --after 2030-01-01T00:00Z --search-days 800 --count 1
```

This previews February 29, 2032 at 09:00 UTC.

A valid preview exits `0`, including empty or partial results. Text mode reports a shortfall on stderr; JSON mode reports it through `complete: false` and the array length. Invalid arguments exit `2` with a diagnostic on stderr and no results on stdout. Use `--help` for argument details.

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

The starting instant is exclusive by default, so the example prints January 2 and 3 at 08:15 UTC. Pass `include_start=True` to include January 1 as the first result.

Pass `zone=ZoneInfo("America/New_York")` (from Python's `zoneinfo` module) to evaluate wall-clock fields in that zone. The start may have any explicit offset; it identifies an instant independently of the schedule zone. The API always returns UTC datetimes.

## Time zones and search limits

- A skipped local minute never fires. A repeated local minute produces two distinct UTC instants, returned in chronological order. This is a preview policy; some cron daemons apply different DST rules.
- Search uses an exclusive start by default and an inclusive end. Opting into start inclusion compares exact instants without rounding, and does not move the end. A search day is exactly 24 elapsed hours, including across DST. The default horizon is 366 days (allowed: 1–3660), and the default count is 5 (allowed: 1–100). The window must stay within UTC years 0002–9998. Fewer results, including none, are valid when the horizon is exhausted.
- For schedules that restrict months, the preview skips UTC dates that cannot overlap a selected local month. An occurrence still counts if its local date and its UTC date fall in different months or years.
- Results use the system IANA database when the zone is available there, or the installed `tzdata` package otherwise. Historical data and future rule projections can differ between database versions.

## Supported cron syntax

Use exactly five whitespace-separated fields, in this order:

| Field | Values |
| --- | --- |
| Minute | 0–59 |
| Hour | 0–23 |
| Day of month | 1–31 |
| Month | 1–12 or `JAN`–`DEC` |
| Day of week | 0–7 or `SUN`–`SAT` (0 and 7 are Sunday, 1 is Monday) |

Each field accepts `*`, a number, an inclusive ascending range (`9-17`), or a comma-separated list of numbers and ranges (`1,3-5`). Steps (`*/15`, `9-17/2`) count from the wildcard's field minimum or the range's start. A stepped range can appear in a list; a wildcard cannot. Use one or two ASCII decimal digits per number, and steps from 1 to 99. Overlapping entries do not create duplicate occurrences.

Month and weekday names are case-insensitive three-letter English abbreviations. They can replace numbers in values, lists, and range endpoints: `0 9 * JAN,MAR MON-FRI` matches weekdays at 09:00 in January and March. Ranges use numeric order: `SUN` means 0, so write `FRI-7` for Friday through Sunday.

Minute, hour and month must all match. If neither day field starts with `*`, **either** day field may match. If either starts with `*` (including `*/n`), **both** must match. For example, a fictional `0 9 15 * 1` schedule runs at 09:00 on the 15th and on Mondays, once if both apply. `0 9 */2 * 1` matches only Mondays on odd-numbered days of the month.

Wraparound ranges, steps on single values, seconds/year fields, macros such as `@daily`, and extensions such as `L`, `W`, `#` or `?` are unsupported. Calendar dates that do not exist never match.

## Development

```sh
python -m pip install '.[dev]'
python -m ruff check .
python -m pytest -q
```
