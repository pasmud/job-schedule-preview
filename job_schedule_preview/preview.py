"""Bounded searches for occurrences on the UTC timeline."""

from calendar import monthrange
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta, tzinfo
from functools import lru_cache

from .cron import CronExpression

DEFAULT_COUNT = 5
DEFAULT_SEARCH_DAYS = 366
MAX_COUNT = 100
MAX_SEARCH_DAYS = 3660


def _utc_instants(wall: datetime, zone: tzinfo) -> Iterator[datetime]:
    """Project a wall minute to zero, one, or two distinct UTC instants."""
    previous = None
    for fold in (0, 1):
        instant = wall.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if instant != previous and instant.astimezone(zone).replace(tzinfo=None) == wall:
            yield instant
        previous = instant


def _candidate_utc_days(first: int, last: int, months: tuple[int, ...]) -> Iterator[int]:
    if len(months) == 12:
        yield from range(first, last + 1)
        return

    # An offset is less than 24 hours, so an allowed local month can
    # contribute matches to the UTC date just before or after that month.
    first_year = date.fromordinal(first - 1).year
    last_year = date.fromordinal(last + 1).year
    next_day = first
    for year in range(first_year, last_year + 1):
        for month in months:
            month_start = date(year, month, 1).toordinal()
            lo = max(next_day, month_start - 1)
            hi = min(last, month_start + monthrange(year, month)[1])
            if lo <= hi:
                yield from range(lo, hi + 1)
                next_day = hi + 1  # Adjacent allowed months can overlap after padding.


def next_occurrences(
    schedule: CronExpression,
    *,
    after: datetime,
    zone: tzinfo = UTC,
    count: int = DEFAULT_COUNT,
    search_days: int = DEFAULT_SEARCH_DAYS,
    include_start: bool = False,
) -> tuple[datetime, ...]:
    """Return up to count UTC matches in an elapsed window with an inclusive end.

    The start is exclusive unless include_start is True.
    """
    if type(count) is not int or not 1 <= count <= MAX_COUNT:
        raise ValueError(f"count must be an integer from 1 to {MAX_COUNT}")
    if type(search_days) is not int or not 1 <= search_days <= MAX_SEARCH_DAYS:
        raise ValueError(f"search_days must be an integer from 1 to {MAX_SEARCH_DAYS}")
    if type(include_start) is not bool:
        raise ValueError("include_start must be a boolean")
    if after.utcoffset() is None:
        raise ValueError("after must be a timezone-aware datetime")

    try:
        start = after.astimezone(UTC)
        end = start + timedelta(days=search_days)
    except OverflowError as exc:
        raise ValueError("search window must stay within UTC years 0002–9998") from exc
    if start.year < 2 or end.year > 9998:
        raise ValueError("search window must stay within UTC years 0002–9998")

    @lru_cache(maxsize=3)
    def local_day_instants(ordinal: int) -> tuple[datetime, ...]:
        return tuple(
            instant
            for wall in schedule.wall_times(date.fromordinal(ordinal))
            for instant in _utc_instants(wall, zone)
        )

    matches: list[datetime] = []
    for ordinal in _candidate_utc_days(
        start.date().toordinal(), end.date().toordinal(), schedule.month.values,
    ):
        utc_day = date.fromordinal(ordinal)
        # Offsets are less than 24 hours in magnitude. A UTC date can only
        # overlap these three local dates, even across a date-line transition.
        # Sorting in UTC keeps folds in order, even when they span midnight.
        candidates = sorted(
            instant
            for local_day in range(ordinal - 1, ordinal + 2)
            for instant in local_day_instants(local_day)
            if instant.date() == utc_day
            and start <= instant <= end
            and (include_start or instant != start)
        )
        matches.extend(candidates[: count - len(matches)])
        if len(matches) == count:
            break
    return tuple(matches)
