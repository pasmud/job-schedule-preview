from datetime import date, time

import pytest

from job_schedule_preview import CronError, parse_cron


def test_lists_ranges_and_steps_expand_in_order_without_duplicates():
    schedule = parse_cron("  50,10-30/10,20   06-08/2  *  *  * ")
    assert [wall.time() for wall in schedule.wall_times(date(2030, 1, 1))] == [
        time(6, 10), time(6, 20), time(6, 30), time(6, 50),
        time(8, 10), time(8, 20), time(8, 30), time(8, 50),
    ]


@pytest.mark.parametrize(
    ("expression", "expected_days"),
    [
        ("0 9 15 4 1", [1, 8, 15, 22, 29]),  # April 15 is also Monday; emitted once.
        ("0 9 16 4 1", [1, 8, 15, 16, 22, 29]),
        ("0 9 */2 4 1", [1, 15, 29]),
        ("0 9 16 4 *", [16]),
        ("0 9 * 4 1", [1, 8, 15, 22, 29]),
        ("0 9 1-31 4 1", list(range(1, 31))),  # A full range is not syntactically '*'.
        ("0 9 * 4 0,7", [7, 14, 21, 28]),
        ("0 9 * 4 6-7", [6, 7, 13, 14, 20, 21, 27, 28]),
    ],
)
def test_day_fields_and_sunday_alias(expression, expected_days):
    schedule = parse_cron(expression)
    assert not list(schedule.wall_times(date(2030, 5, 1)))
    actual_days = [
        wall.day for day in range(1, 31) for wall in schedule.wall_times(date(2030, 4, day))
    ]
    assert actual_days == expected_days


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("0 24 * * *", "hour"),
        ("0 0 0 * *", "day of month"),
        ("0 0 * 13 *", "month"),
        ("0 0 * * 8", "day of week"),
        ("0 0 * * 5-1", "ascending"),
        ("0 0 * * MON", "day of week"),
        ("0 0 L * *", "day of month"),
        ("0 0 * * 2#3", "day of week"),
        ("0 0 * * ?", "day of week"),
        ("1,,4 * * * *", "minute"),
        ("1, * * * *", "minute"),
        ("1,* * * * *", "wildcard"),
        ("*/0 * * * *", "positive"),
        ("1/2 * * * *", "explicit range"),
        ("*-2 * * * *", "minute"),
        ("٠ * * * *", "minute"),
        ("* * * * * *", "five"),
        ("@daily", "five"),
    ],
)
def test_rejects_unsupported_and_invalid_syntax(expression, message):
    with pytest.raises(CronError, match=message):
        parse_cron(expression)
