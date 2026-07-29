from datetime import UTC, datetime

from app.core.csv_export import as_utc, rows_to_csv


def test_rows_to_csv_writes_header_and_rows():
    csv_text = rows_to_csv(
        [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}],
        columns=["a", "b"],
    )
    lines = csv_text.strip().splitlines()
    assert lines[0] == "a,b"
    assert lines[1] == "1,2"
    assert lines[2] == "3,4"


def test_rows_to_csv_ignores_extra_keys_not_in_columns():
    csv_text = rows_to_csv([{"a": "1", "secret": "shh"}], columns=["a"])
    assert "shh" not in csv_text


def test_rows_to_csv_empty_rows_still_has_header():
    csv_text = rows_to_csv([], columns=["a", "b"])
    assert csv_text.strip() == "a,b"


def test_as_utc_none_stays_none():
    assert as_utc(None) is None


def test_as_utc_leaves_aware_datetime_unchanged():
    dt = datetime(2026, 1, 1, tzinfo=UTC)
    assert as_utc(dt) == dt


def test_as_utc_assumes_utc_for_naive_datetime():
    naive = datetime(2026, 1, 1)
    result = as_utc(naive)
    assert result.tzinfo is UTC
    assert result.replace(tzinfo=None) == naive
