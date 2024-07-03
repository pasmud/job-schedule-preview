"""Parse cron expressions and select matching wall-clock times."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, time

_FIELDS = (
    ("minute", 0, 59),
    ("hour", 0, 23),
    ("day of month", 1, 31),
    ("month", 1, 12),
    ("day of week", 0, 7),
)


class CronError(ValueError):
    """An expression is outside the supported cron syntax."""


@dataclass(frozen=True)
class _Field:
    values: tuple[int, ...]
    wildcard: bool


@dataclass(frozen=True)
class CronExpression:
    """An immutable five-field schedule returned by parse_cron."""

    minute: _Field
    hour: _Field
    day_of_month: _Field
    month: _Field
    day_of_week: _Field

    def wall_times(self, day: date) -> Iterator[datetime]:
        """Yield matching naive datetimes for one local calendar day."""
        if day.month not in self.month.values:
            return

        dom = day.day in self.day_of_month.values
        dow = (day.weekday() + 1) % 7 in self.day_of_week.values
        if self.day_of_month.wildcard or self.day_of_week.wildcard:
            matches = dom and dow
        else:
            matches = dom or dow
        if matches:
            for hour in self.hour.values:
                for minute in self.minute.values:
                    yield datetime.combine(day, time(hour, minute))


def _parse_field(text: str, name: str, low: int, high: int) -> _Field:
    if text == "*":
        values = tuple(range(low, high + 1))
    elif re.fullmatch(r"[0-9]{1,2}", text) and low <= int(text) <= high:
        values = (int(text),)
    else:
        raise CronError(f"{name}: expected '*' or a number from {low} to {high}; got {text!r}")

    if name == "day of week":
        values = tuple(sorted({value % 7 for value in values}))
    return _Field(values, wildcard=text == "*")


def parse_cron(expression: str) -> CronExpression:
    """Parse exactly five whitespace-separated cron fields."""
    fields = expression.split()
    if len(fields) != len(_FIELDS):
        raise CronError(f"expected five cron fields, got {len(fields)}")
    return CronExpression(*(_parse_field(text, *spec) for text, spec in zip(fields, _FIELDS)))
