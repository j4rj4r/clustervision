import csv
import io
from datetime import UTC, datetime


def rows_to_csv(rows: list[dict], columns: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def as_utc(value: datetime | None) -> datetime | None:
    """Query-param datetimes may arrive naive (no offset) — assume UTC rather
    than comparing naive-vs-aware against the tz-aware DB columns, which
    raises on some backends and silently misbehaves on others."""
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
