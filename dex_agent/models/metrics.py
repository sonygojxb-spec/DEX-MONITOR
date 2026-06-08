"""Time-series metric models.

Design reference: "Data Models" -> "Metrics (time series)". Covers
:class:`MetricKind`, the :data:`MISSING` sentinel, and :class:`MetricEntry`.

A metric value is either a :class:`~decimal.Decimal` or :data:`MISSING` (when
the value was unavailable at record time; Requirement 4.10). :data:`MISSING` is
a distinct singleton so it is never confused with ``0`` or ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Union


class MetricKind(Enum):
    """Kinds of recorded time-series metrics (Requirements 4.1-4.3)."""

    LIQUIDITY = "LIQUIDITY"
    MARKET_CAP = "MARKET_CAP"
    FDV = "FDV"
    BUY_COUNT = "BUY_COUNT"
    SELL_COUNT = "SELL_COUNT"
    BUY_VOLUME = "BUY_VOLUME"
    SELL_VOLUME = "SELL_VOLUME"


class _MissingType(Enum):
    """The type of the :data:`MISSING` sentinel (a singleton enum member)."""

    MISSING = "MISSING"

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "MISSING"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return "MISSING"


# Sentinel recorded when a metric value is unavailable (design ``MISSING``).
MISSING = _MissingType.MISSING

# A metric value is a Decimal or the MISSING sentinel.
MetricValue = Union[Decimal, _MissingType]


@dataclass(frozen=True)
class MetricEntry:
    """One time-series entry for a Trading_Pair metric.

    ``value`` is a :class:`~decimal.Decimal` or :data:`MISSING`. ``recorded_at``
    is to second-level precision; a series is ordered ascending by it
    (Requirement 4.4).
    """

    pair_id: str
    kind: MetricKind
    value: MetricValue
    recorded_at: datetime


__all__ = [
    "MetricKind",
    "MISSING",
    "MetricValue",
    "MetricEntry",
]
