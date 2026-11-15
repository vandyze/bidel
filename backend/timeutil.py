from datetime import datetime, timezone


def utcnow() -> datetime:
    """UTC فعلی به‌صورت naive (سازگار با ستون‌های DateTime بدون timezone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
