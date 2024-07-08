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
_ITEM = re.compile(r"(?P<start>\*|[0-9]{1,2})(?:-(?P<end>[0-9]{1,2}))?(?:/(?P<step>[0-9]{1,2}))?")


class CronError(ValueError):
    """An expression is outside the supported cron syntax."""


@dataclass(frozen=True)
class _Field:
    values: tuple[int, ...]
    starts_with_star: bool


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
        if self.day_of_month.starts_with_star or self.day_of_week.starts_with_star:
            matches = dom and dow
        else:
            matches = dom or dow
        if matches:
            for hour in self.hour.values:
                for minute in self.minute.values:
                    yield datetime.combine(day, time(hour, minute))


def _parse_field(text: str, name: str, low: int, high: int) -> _Field:
    items = text.split(",")
    if len(items) > 1 and "*" in text:
        raise CronError(f"{name}: a wildcard cannot appear in a list")

    values: set[int] = set()
    for item in items:
        match = _ITEM.fullmatch(item)
        if not match:
            raise CronError(f"{name}: invalid item {item!r}")
        start, end, step_text = match.group("start", "end", "step")
        step = int(step_text) if step_text is not None else 1
        if step == 0:
            raise CronError(f"{name}: step must be positive")

        if start == "*":
            if end is not None:
                raise CronError(f"{name}: invalid item {item!r}")
            first, last = low, high
        else:
            first, last = int(start), int(end) if end is not None else int(start)
            if not (low <= first <= high and low <= last <= high):
                raise CronError(f"{name}: values must be from {low} to {high}; got {item!r}")
            if first > last:
                raise CronError(f"{name}: range must be ascending; got {item!r}")
            if end is None and step_text is not None:
                raise CronError(f"{name}: steps require '*' or an explicit range")
        values.update(range(first, last + 1, step))

    if name == "day of week":
        values = {value % 7 for value in values}
    return _Field(tuple(sorted(values)), starts_with_star=text.startswith("*"))


def parse_cron(expression: str) -> CronExpression:
    """Parse exactly five whitespace-separated cron fields."""
    fields = expression.split()
    if len(fields) != len(_FIELDS):
        raise CronError(f"expected five cron fields, got {len(fields)}")
    return CronExpression(*(_parse_field(text, *spec) for text, spec in zip(fields, _FIELDS)))
