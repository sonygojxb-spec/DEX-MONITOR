"""Order / execution models and the in-flight order registry.

Design reference: "Data Models" -> "Orders / Execution" and "In-Flight Order
Tracking (Trade Idempotency, Req 12)". Covers :class:`OrderKind`,
:class:`OrderStatus`, :class:`OrderRecord`, the :data:`TERMINAL_ORDER_STATUS`
set, and the :class:`InFlightRegistry`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class OrderKind(Enum):
    """Direction of an order."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Lifecycle state of an order.

    ``SUBMITTED`` is the sole non-terminal (in-flight) state; the remaining
    members are terminal (see :data:`TERMINAL_ORDER_STATUS`).
    """

    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"

    def is_terminal(self) -> bool:
        """True iff this status is terminal (Requirement 12.4)."""
        return self in TERMINAL_ORDER_STATUS


# A terminal OrderStatus is one of these; SUBMITTED is the sole non-terminal
# (in-flight) state (design "In-Flight Order Tracking").
TERMINAL_ORDER_STATUS: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.CONFIRMED,
        OrderStatus.CANCELLED,
        OrderStatus.FAILED,
        OrderStatus.TIMED_OUT,
    }
)


@dataclass(frozen=True)
class OrderRecord:
    """A submitted order and its execution outcome.

    Execution fields (``executed_price``, ``executed_qty``, ``fee``, ``tx_id``)
    are populated on confirmation; ``reason`` carries the cancellation/failure
    reason when applicable.
    """

    pair_id: str
    kind: OrderKind
    requested_qty: Decimal
    notional: Decimal
    max_slippage: Decimal
    status: OrderStatus
    recorded_at: datetime
    executed_price: Decimal | None = None
    executed_qty: Decimal | None = None
    fee: Decimal | None = None
    tx_id: str | None = None
    reason: str | None = None


class InFlightRegistry:
    """Tracks at most one in-flight (non-terminal) order per ``pair_id``.

    The in-memory projection of the trade-idempotency invariant
    (Requirements 12.1-12.4): a pair is present iff it has a non-terminal
    (``SUBMITTED``) order in flight. A marker is set on submit
    (:meth:`mark`) and cleared exactly when the order reaches a terminal
    status (:meth:`clear`).
    """

    def __init__(self) -> None:
        self._by_pair: dict[str, OrderRecord] = {}

    def mark(self, pair_id: str, order: OrderRecord) -> None:
        """Record ``order`` as the in-flight order for ``pair_id`` (Req 12.1)."""
        self._by_pair[pair_id] = order

    def clear(self, pair_id: str) -> None:
        """Remove the in-flight marker for ``pair_id`` (Req 12.4).

        A no-op when no marker is present.
        """
        self._by_pair.pop(pair_id, None)

    def has_in_flight(self, pair_id: str) -> bool:
        """True iff a non-terminal order is currently in flight for ``pair_id``."""
        return pair_id in self._by_pair

    def get(self, pair_id: str) -> OrderRecord | None:
        """Return the in-flight order for ``pair_id`` if any, else ``None``."""
        return self._by_pair.get(pair_id)


__all__ = [
    "OrderKind",
    "OrderStatus",
    "TERMINAL_ORDER_STATUS",
    "OrderRecord",
    "InFlightRegistry",
]
