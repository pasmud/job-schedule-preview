from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from job_schedule_preview import next_occurrences, parse_cron


@pytest.mark.parametrize(
    ("zone", "expression", "after", "expected"),
    [
        (
            "America/New_York", "30 2 * * *", "2024-03-10T00:00Z",
            ["2024-03-11T06:30Z", "2024-03-12T06:30Z"],
        ),
        (
            "America/New_York", "15,45 1 * * *", "2024-11-03T00:00Z",
            ["2024-11-03T05:15Z", "2024-11-03T05:45Z", "2024-11-03T06:15Z", "2024-11-03T06:45Z"],
        ),
        (
            "America/New_York", "30 1 * * *", "2024-11-03T01:30-04:00",
            ["2024-11-03T06:30Z"],
        ),
        (
            "Australia/Lord_Howe", "15 2 * * *", "2024-10-05T12:00Z",
            ["2024-10-06T15:15Z"],
        ),
        (
            "Australia/Lord_Howe", "45 1 * * *", "2024-04-06T12:00Z",
            ["2024-04-06T14:45Z", "2024-04-06T15:15Z"],
        ),
        (
            "Asia/Kathmandu", "0 0 2 1 *", "2030-01-01T00:00Z",
            ["2030-01-01T18:15Z"],
        ),
        (
            "Pacific/Apia", "0 12 * * *", "2011-12-29T21:59Z",
            ["2011-12-29T22:00Z", "2011-12-30T22:00Z"],
        ),
        (
            "Africa/Monrovia", "0 12 * * *", "1970-01-01T00:00Z",
            ["1970-01-01T12:44:30Z"],
        ),
    ],
)
def test_matches_on_utc_timeline(zone, expression, after, expected):
    actual = next_occurrences(
        parse_cron(expression),
        after=datetime.fromisoformat(after),
        zone=ZoneInfo(zone),
        count=len(expected),
        search_days=3,
    )
    assert actual == tuple(map(datetime.fromisoformat, expected))


def test_search_days_measure_elapsed_time_during_fall_transition():
    actual = next_occurrences(
        parse_cron("0 12 * * *"),
        after=datetime.fromisoformat("2024-11-02T12:00-04:00"),
        zone=ZoneInfo("America/New_York"),
        search_days=1,
    )
    assert actual == ()  # The next local noon is 25 hours after the start.


@pytest.mark.parametrize(
    ("after", "expected"),
    [
        ("2024-11-03T01:30-04:00", ["2024-11-03T05:30Z", "2024-11-03T06:30Z"]),
        ("2024-11-03T01:30-05:00", ["2024-11-03T06:30Z", "2024-11-04T06:30Z"]),
        ("2024-11-03T01:30:00.000001-04:00", ["2024-11-03T06:30Z"]),
    ],
)
def test_include_start_matches_exact_instant_in_fall_fold(after, expected):
    assert next_occurrences(
        parse_cron("30 1 * * *"),
        after=datetime.fromisoformat(after),
        zone=ZoneInfo("America/New_York"),
        search_days=1,
        include_start=True,
    ) == tuple(map(datetime.fromisoformat, expected))


def test_include_start_does_not_restore_a_skipped_spring_minute():
    assert next_occurrences(
        parse_cron("30 2 * * *"),
        after=datetime.fromisoformat("2024-03-10T02:30-05:00"),
        zone=ZoneInfo("America/New_York"),
        search_days=1,
        include_start=True,
    ) == (datetime.fromisoformat("2024-03-11T06:30Z"),)


@pytest.mark.parametrize(
    ("zone", "expression", "after", "search_days", "expected"),
    [
        ("Pacific/Kiritimati", "0 0 1 JAN *", "2030-12-30T10:00Z", 1, ["2030-12-31T10:00Z"]),
        ("Pacific/Pago_Pago", "0 23 31 DEC *", "2031-01-01T00:00Z", 1, ["2031-01-01T10:00Z"]),
        (
            "Pacific/Kiritimati", "0 0 1 JAN,DEC *", "2030-11-29T00:00Z", 40,
            ["2030-11-30T10:00Z", "2030-12-31T10:00Z"],
        ),
    ],
)
def test_month_restrictions_apply_to_local_dates_not_utc_dates(
    zone, expression, after, search_days, expected,
):
    assert next_occurrences(
        parse_cron(expression),
        after=datetime.fromisoformat(after),
        zone=ZoneInfo(zone),
        search_days=search_days,
    ) == tuple(map(datetime.fromisoformat, expected))
