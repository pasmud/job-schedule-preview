import json
import subprocess
import sys

import pytest


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "job_schedule_preview", *args],
        capture_output=True, text=True, timeout=10, check=False,
    )


def test_text_output_disambiguates_two_folded_minutes():
    result = run_cli(
        "30 1 * * *", "--zone", "America/New_York",
        "--after", "2024-11-03T00:00:00-04:00", "--count", "2",
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "2024-11-03T01:30:00-04:00\t2024-11-03T05:30:00Z",
        "2024-11-03T01:30:00-05:00\t2024-11-03T06:30:00Z",
    ]


def test_json_output_with_partial_results_and_normalized_start():
    result = run_cli(
        "0 0 * * *", "--zone", "UTC", "--after", "2030-01-01T00:30:01.250+01:00",
        "--search-days", "1", "--count", "2", "--format", "json",
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "zone": "UTC",
        "after_utc": "2029-12-31T23:30:01.250000Z",
        "requested_count": 2,
        "search_days": 1,
        "complete": False,
        "occurrences": [{"local": "2030-01-01T00:00:00+00:00", "utc": "2030-01-01T00:00:00Z"}],
    }


def test_empty_text_preview_is_successful_with_stderr_notice():
    result = run_cli("0 9 29 2 *", "--zone", "UTC", "--after", "2030-01-01T00:00Z", "--search-days", "30")
    assert result.returncode == 0
    assert result.stdout == ""
    assert "Found 0 of 5 requested occurrences" in result.stderr


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("--after", "2030-01-01T00:00Z"), "arguments are required: --zone"),
        (("--zone", "UTC"), "arguments are required: --after"),
        (("--zone", "Example/NoSuchZone"), "unknown IANA time zone"),
        (("--zone", "localtime"), "unknown IANA time zone"),
        (("--after", "2030-01-01T00:00"), "with Z or"),
        (("--after", "2030-01-01T00:00+00:60"), "with Z or"),
        (("--after", "2030-02-30T00:00Z"), "invalid date or time"),
    ],
)
def test_rejects_missing_or_invalid_time_inputs(args, message):
    result = run_cli("* * * * *", *args)
    assert result.returncode == 2
    assert result.stdout == ""
    assert message in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("expression", "extra", "message"),
    [
        ("60 * * * *", (), "minute:"),
        ("* * * * *", ("--count", "101"), "count must be"),
        ("* * * * *", ("--search-days", "0"), "search_days must be"),
        ("* * * * *", ("--format", "csv"), "invalid choice"),
    ],
)
def test_rejects_invalid_expression_or_options(expression, extra, message):
    result = run_cli(expression, "--zone", "UTC", "--after", "2030-01-01T00:00Z", *extra)
    assert result.returncode == 2
    assert result.stdout == ""
    assert message in result.stderr
    assert "Traceback" not in result.stderr
