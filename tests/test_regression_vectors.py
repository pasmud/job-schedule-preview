import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from job_schedule_preview import next_occurrences, parse_cron

VECTORS = sorted(Path(__file__).with_name("regression_vectors").glob("*.json"))


@pytest.mark.parametrize("path", VECTORS, ids=lambda path: path.stem)
def test_regression_vector(path):
    vector = json.loads(path.read_text(encoding="utf-8"))
    expected = tuple(map(datetime.fromisoformat, vector["expected_utc"]))
    actual = next_occurrences(
        parse_cron(vector["expression"]),
        after=datetime.fromisoformat(vector["after"]),
        zone=ZoneInfo(vector["zone"]),
        count=vector["count"],
        search_days=vector["search_days"],
        include_start=vector.get("include_start", False),
    )

    assert actual == expected, vector["title"]
    assert all(instant.utcoffset() == timedelta(0) for instant in actual)
