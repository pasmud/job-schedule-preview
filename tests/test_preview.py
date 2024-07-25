from datetime import UTC, datetime, timedelta, timezone

import pytest

from job_schedule_preview import CronError, next_occurrences, parse_cron


def test_next_occurrences_excludes_start_and_normalizes_offset():
    offset = timezone(timedelta(hours=2))
    after = datetime(2030, 1, 1, 10, 15, tzinfo=offset)
    assert next_occurrences(parse_cron("15 8 * * *"), after=after, count=2) == (
        datetime(2030, 1, 2, 8, 15, tzinfo=UTC),
        datetime(2030, 1, 3, 8, 15, tzinfo=UTC),
    )


def test_inclusive_end_can_return_fewer_than_requested():
    after = datetime(2030, 1, 1, 0, 0, tzinfo=UTC)
    assert next_occurrences(parse_cron("0 0 * * *"), after=after, search_days=1) == (
        datetime(2030, 1, 2, 0, 0, tzinfo=UTC),
    )


def test_impossible_calendar_date_returns_no_matches():
    after = datetime(2030, 1, 1, tzinfo=UTC)
    assert next_occurrences(parse_cron("0 0 31 2 *"), after=after) == ()


@pytest.mark.parametrize(("expression", "message"), [("* * *", "five"), ("60 * * * *", "minute")])
def test_invalid_expression(expression, message):
    with pytest.raises(CronError, match=message):
        parse_cron(expression)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"count": 0}, "count"), ({"search_days": 3661}, "search_days"),
     ({"include_start": "false"}, "include_start")],
)
def test_search_limits(kwargs, message):
    with pytest.raises(ValueError, match=message):
        next_occurrences(parse_cron("* * * * *"), after=datetime(2030, 1, 1, tzinfo=UTC), **kwargs)


def test_naive_start_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        next_occurrences(parse_cron("* * * * *"), after=datetime(2030, 1, 1))


@pytest.mark.parametrize("after", [datetime(1, 1, 1, tzinfo=UTC), datetime(9998, 12, 31, tzinfo=UTC)])
def test_window_must_stay_in_supported_utc_years(after):
    with pytest.raises(ValueError, match="years 0002–9998"):
        next_occurrences(parse_cron("* * * * *"), after=after, search_days=1)


def test_leap_day_is_found_with_a_longer_horizon():
    schedule = parse_cron("0 0 29 2 *")
    after = datetime(2029, 1, 1, tzinfo=UTC)
    assert next_occurrences(schedule, after=after) == ()
    assert next_occurrences(schedule, after=after, count=1, search_days=1200) == (
        datetime(2032, 2, 29, tzinfo=UTC),
    )


def test_sparse_search_skips_off_months_over_the_maximum_horizon(monkeypatch):
    schedule = parse_cron("0 9 29 FEB *")
    schedule_type = type(schedule)
    wall_times = schedule_type.wall_times
    days_examined = 0

    def track_wall_times(self, day):
        nonlocal days_examined
        days_examined += 1
        return wall_times(self, day)

    monkeypatch.setattr(schedule_type, "wall_times", track_wall_times)
    assert next_occurrences(
        schedule, after=datetime(2096, 3, 1, tzinfo=UTC), search_days=3660,
    ) == (datetime(2104, 2, 29, 9, tzinfo=UTC),)
    assert days_examined < 365  # Less than a year's worth of dates in a ten-year search.
