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
    [({"count": 0}, "count"), ({"search_days": 3661}, "search_days")],
)
def test_search_limits(kwargs, message):
    with pytest.raises(ValueError, match=message):
        next_occurrences(parse_cron("* * * * *"), after=datetime(2030, 1, 1, tzinfo=UTC), **kwargs)


def test_naive_start_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        next_occurrences(parse_cron("* * * * *"), after=datetime(2030, 1, 1))
