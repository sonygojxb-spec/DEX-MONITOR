"""Shared, reusable query primitives for repository implementations.

Design reference: "Persistence Layer" (time-series range queries, retention) and
"Concurrency / Idempotent persistence". Both the Metrics time-series repository
(Requirements 4.4, 4.6) and the Audit-trail repository (Requirement 10.2) need
the *same* two operations:

* :func:`entries_in_range` - return the entries whose timestamp falls within an
  **inclusive** ``[start, end]`` range, ordered by **ascending** timestamp.
* :func:`older_than` - return the entries that are **strictly older** than a
  retention boundary, used to drive deletion of expired records
  (Requirements 1.4 data retention, 10.5-10.6).

Keeping these in one module means Metrics and Audit share a single, tested
definition of "in range" and "expired" rather than re-deriving the boundary
semantics independently.

The primitives are pure functions over any iterable of timestamped items. By
default the timestamp is read from an item's ``recorded_at`` attribute (the
field both :class:`~dex_agent.models.metrics.MetricEntry` and
:class:`~dex_agent.models.audit.AuditRecord` use); a custom ``key`` callable can
be supplied for items that timestamp under a different field.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Iterable, TypeVar

from dex_agent.models.timestamps import utc_now

T = TypeVar("T")

# A timestamp accessor over a stored item.
TimestampKey = Callable[[T], datetime]


def _recorded_at(item: object) -> datetime:
    """Default timestamp accessor: an item's ``recorded_at`` field.

    Both :class:`~dex_agent.models.metrics.MetricEntry` and
    :class:`~dex_agent.models.audit.AuditRecord` timestamp under ``recorded_at``,
    so this default lets a single primitive serve both repositories.
    """
    return item.recorded_at  # type: ignore[attr-defined]


def entries_in_range(
    items: Iterable[T],
    start: datetime,
    end: datetime,
    *,
    key: TimestampKey = _recorded_at,
) -> list[T]:
    """Return the items whose timestamp is within ``[start, end]``, ascending.

    The range is **inclusive of both bounds** (an item whose timestamp equals
    ``start`` or ``end`` is included; Requirements 4.6, 10.2). The result is
    ordered by **ascending** timestamp (Requirement 4.4).

    This primitive is intentionally pure and does not itself reject an inverted
    range (``start > end``): per the design, the invalid-time-range rejection
    (Requirements 4.7, 10.4) is performed by the calling component before the
    primitive runs. When ``start > end`` no item can satisfy the inclusive
    bounds, so the primitive simply yields an empty list.

    Args:
        items: Any iterable of timestamped items.
        start: Inclusive lower bound.
        end: Inclusive upper bound.
        key: Accessor returning an item's timestamp (defaults to ``recorded_at``).

    Returns:
        A new list of the matching items, ordered by ascending timestamp.
    """
    selected = [item for item in items if start <= key(item) <= end]
    selected.sort(key=key)
    return selected


def older_than(
    items: Iterable[T],
    period: timedelta,
    *,
    now: datetime | None = None,
    key: TimestampKey = _recorded_at,
) -> list[T]:
    """Return the items strictly older than the retention boundary.

    The retention boundary is ``now - period``. An item is "expired" when its
    age exceeds ``period`` - i.e. its timestamp is **strictly older** than the
    boundary (``timestamp < now - period``). This matches Requirement 10.6 ("when
    a record's age *exceeds* the configured retention period, delete it") and the
    data-retention requirement (1.4 / 10.5): an item exactly at the boundary is
    still within retention and is therefore **not** returned.

    Args:
        items: Any iterable of timestamped items.
        period: The retention period (an item older than this is expired).
        now: Reference "current" time; defaults to :func:`utc_now`. Injectable so
            retention is deterministically testable.
        key: Accessor returning an item's timestamp (defaults to ``recorded_at``).

    Returns:
        A new list of the expired items, ordered by ascending timestamp.
    """
    reference = now if now is not None else utc_now()
    boundary = reference - period
    expired = [item for item in items if key(item) < boundary]
    expired.sort(key=key)
    return expired


__all__ = [
    "TimestampKey",
    "entries_in_range",
    "older_than",
]
