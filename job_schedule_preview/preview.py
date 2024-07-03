"""Bounded searches for occurrences on the UTC timeline."""

from datetime import UTC, datetime, timedelta

from .cron import CronExpression

DEFAULT_COUNT = 5
DEFAULT_SEARCH_DAYS = 366
MAX_COUNT = 100
MAX_SEARCH_DAYS = 3660


def next_occurrences(
    schedule: CronExpression,
    *,
    after: datetime,
    count: int = DEFAULT_COUNT,
    search_days: int = DEFAULT_SEARCH_DAYS,
) -> tuple[datetime, ...]:
    """Return up to count UTC instants in (after, after + search_days]."""
    if type(count) is not int or not 1 <= count <= MAX_COUNT:
        raise ValueError(f"count must be an integer from 1 to {MAX_COUNT}")
    if type(search_days) is not int or not 1 <= search_days <= MAX_SEARCH_DAYS:
        raise ValueError(f"search_days must be an integer from 1 to {MAX_SEARCH_DAYS}")
    if after.utcoffset() is None:
        raise ValueError("after must be a timezone-aware datetime")

    try:
        start = after.astimezone(UTC)
        end = start + timedelta(days=search_days)
    except OverflowError as exc:
        raise ValueError("search window is outside the supported calendar") from exc

    matches: list[datetime] = []
    for ordinal in range(start.date().toordinal(), end.date().toordinal() + 1):
        day = start.date().fromordinal(ordinal)
        for wall in schedule.wall_times(day):
            instant = wall.replace(tzinfo=UTC)
            if start < instant <= end:
                matches.append(instant)
                if len(matches) == count:
                    return tuple(matches)
    return tuple(matches)
