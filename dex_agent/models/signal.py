"""Signal models.

Design reference: "Data Models" -> "Signals". Covers :class:`SignalType`,
:class:`ExitClass`, and :class:`Signal`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping


class SignalType(Enum):
    """Whether a signal recommends entering or exiting a position."""

    ENTRY = "ENTRY"
    EXIT = "EXIT"


class ExitClass(Enum):
    """Classification of an EXIT signal (Requirements 5.3, 5.4, 7.5)."""

    RUG_PULL = "RUG_PULL"
    DUMP = "DUMP"
    STOP_LOSS = "STOP_LOSS"
    MANUAL = "MANUAL"


@dataclass(frozen=True)
class Signal:
    """A computed entry/exit signal for a Trading_Pair.

    ``score`` is the entry score (entry signals); ``eligible`` is set for entry
    signals only; ``exit_class`` is set for exit signals only.
    ``contributing_metrics`` records the inputs that produced the signal
    (Requirement 5.6).
    """

    pair_id: str
    type: SignalType
    score: Decimal
    eligible: bool
    generated_at: datetime
    exit_class: ExitClass | None = None
    contributing_metrics: Mapping[str, object] = field(default_factory=dict)


__all__ = [
    "SignalType",
    "ExitClass",
    "Signal",
]
