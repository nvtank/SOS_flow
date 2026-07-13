from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return an aware UTC timestamp for all domain writes and calculations."""
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Treat legacy naive timestamps as UTC while old SQLite data is migrated."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
