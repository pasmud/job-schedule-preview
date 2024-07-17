"""Command-line interface for bounded, offline schedule previews."""

import argparse
import json
import re
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .cron import parse_cron
from .preview import (
    DEFAULT_COUNT,
    DEFAULT_SEARCH_DAYS,
    MAX_COUNT,
    MAX_SEARCH_DAYS,
    next_occurrences,
)

_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}"
    r"(?::[0-9]{2}(?:\.[0-9]{1,6})?)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


def _parse_after(value: str) -> datetime:
    if not _TIMESTAMP.fullmatch(value):
        raise argparse.ArgumentTypeError("use YYYY-MM-DDTHH:MM[:SS[.ffffff]] with Z or ±HH:MM")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date or time: {value!r}") from exc


def _parse_zone(value: str) -> ZoneInfo:
    # These zoneinfo filesystem entries are not IANA schedule identifiers.
    message = f"unknown IANA time zone: {value!r}"
    if value in {"localtime", "posixrules"} or value.startswith(("posix/", "right/")):
        raise argparse.ArgumentTypeError(message)
    try:
        return ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise argparse.ArgumentTypeError(message) from exc


def _utc_text(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat().removesuffix("+00:00") + "Z"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-schedule-preview",
        description="Preview five-field cron occurrences offline; never execute jobs.",
        allow_abbrev=False,
    )
    parser.add_argument("expression", help="quoted five-field cron expression (month/day names allowed)")
    parser.add_argument("--zone", required=True, type=_parse_zone, help="IANA time zone (e.g. UTC)")
    parser.add_argument(
        "--after", required=True, type=_parse_after, help="start timestamp with offset (exclusive by default)",
    )
    parser.add_argument(
        "--include-start", action="store_true", help="include a match exactly at --after",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"maximum occurrences (1–{MAX_COUNT}, default: %(default)s)",
    )
    parser.add_argument(
        "--search-days",
        type=int,
        default=DEFAULT_SEARCH_DAYS,
        help=f"search horizon in elapsed 24-hour days (1–{MAX_SEARCH_DAYS}, default: %(default)s)",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text", help="output format")
    args = parser.parse_args(argv)

    try:
        instants = next_occurrences(
            parse_cron(args.expression),
            after=args.after,
            zone=args.zone,
            count=args.count,
            search_days=args.search_days,
            include_start=args.include_start,
        )
    except ValueError as exc:
        parser.error(str(exc))

    occurrences = [
        {"local": instant.astimezone(args.zone).isoformat(), "utc": _utc_text(instant)}
        for instant in instants
    ]
    complete = len(occurrences) == args.count
    if args.format == "json":
        report = {
            "zone": args.zone.key,
            "after_utc": _utc_text(args.after),
            "requested_count": args.count,
            "search_days": args.search_days,
            "complete": complete,
            "occurrences": occurrences,
        }
        if args.include_start:
            report["include_start"] = True
        print(json.dumps(report, indent=2))
    else:
        for occurrence in occurrences:
            print(occurrence["local"], occurrence["utc"], sep="\t")
        if not complete:
            print(
                f"Found {len(occurrences)} of {args.count} requested occurrences "
                f"within {args.search_days} search day(s).",
                file=sys.stderr,
            )
    return 0
