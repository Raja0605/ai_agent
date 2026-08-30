from datetime import datetime, timezone

from app.services.job_service import _database_datetime


def test_database_datetime_converts_aware_timestamp_to_naive_utc():
    result = _database_datetime(datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc))
    assert result == datetime(2026, 8, 27, 12, 0)
    assert result.tzinfo is None


def test_database_datetime_keeps_naive_timestamp():
    value = datetime(2026, 8, 27, 12, 0)
    assert _database_datetime(value) is value
