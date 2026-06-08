"""UTC timestamp helpers at the precision levels the design specifies.

The data models carry timezone-aware :class:`datetime.datetime` values. The
design pins two precisions:

* **second-level precision** - security evaluations, pair snapshots, and
  metric series entries (``timestamp(seconds, UTC)`` / ``timestamp(seconds)``).
* **millisecond-level precision** - audit records (``timestamp(millis, UTC)``).

These helpers produce / truncate tz-aware UTC datetimes so the components that
build records (later tasks) record timestamps at exactly the required
precision. Keeping them here means the precision contract lives next to the
models rather than being re-derived at each call site.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC ``datetime``."""
    return datetime.now(timezone.utc)


def to_second_precision(dt: datetime) -> datetime:
    """Truncate a datetime to whole seconds, preserving UTC awareness."""
    return dt.replace(microsecond=0)


def to_millis_precision(dt: datetime) -> datetime:
    """Truncate a datetime to whole milliseconds, preserving UTC awareness."""
    millis = dt.microsecond // 1000
    return dt.replace(microsecond=millis * 1000)


def utc_now_seconds() -> datetime:
    """Current UTC time truncated to second-level precision."""
    return to_second_precision(utc_now())


def utc_now_millis() -> datetime:
    """Current UTC time truncated to millisecond-level precision."""
    return to_millis_precision(utc_now())


__all__ = [
    "utc_now",
    "utc_now_seconds",
    "utc_now_millis",
    "to_second_precision",
    "to_millis_precision",
]
