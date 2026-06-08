"""Position and risk-profile models.

Design reference: "Data Models" -> "Positions & Risk". Covers
:class:`PositionStatus`, :class:`Position`, :class:`PerOrderSizeKind`,
:class:`PerOrderSize`, and :class:`RiskProfile`.

:class:`PerOrderSize` is a discriminated value (Requirement 6.9): a
``FIXED_QUOTE`` carries a Quote_Asset amount, a ``PERCENT_BALANCE`` carries a
percentage of available Quote_Asset balance. It drives order sizing in the
Trade_Executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from dex_agent.models.severity import Severity


class PositionStatus(Enum):
    """Lifecycle state of a Position."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class Position:
    """An open (or closed) holding of a Token resulting from an executed buy.

    ``notional_cost`` is the position's contribution to total exposure.
    """

    pair_id: str
    token_address: str
    quantity: Decimal
    avg_entry_price: Decimal
    notional_cost: Decimal
    opened_at: datetime
    status: PositionStatus


class PerOrderSizeKind(Enum):
    """Discriminator for :class:`PerOrderSize`.

    * ``FIXED_QUOTE``     - ``value`` is a Quote_Asset amount (``>= 0``).
    * ``PERCENT_BALANCE`` - ``value`` is a percent of available Quote_Asset
      balance, in ``(0, 100]``.
    """

    FIXED_QUOTE = "FIXED_QUOTE"
    PERCENT_BALANCE = "PERCENT_BALANCE"


@dataclass(frozen=True)
class PerOrderSize:
    """The amount allocated to a single buy order (Requirement 6.9).

    Interpretation of ``value`` is governed by ``kind``:

    * :attr:`PerOrderSizeKind.FIXED_QUOTE` - a fixed Quote_Asset amount.
    * :attr:`PerOrderSizeKind.PERCENT_BALANCE` - a percentage of the available
      Quote_Asset balance.

    Use :meth:`fixed_quote` / :meth:`percent_balance` for clarity at call sites.
    """

    kind: PerOrderSizeKind
    value: Decimal

    @classmethod
    def fixed_quote(cls, amount: Decimal) -> "PerOrderSize":
        """A fixed Quote_Asset amount per order (``amount >= 0``)."""
        return cls(kind=PerOrderSizeKind.FIXED_QUOTE, value=amount)

    @classmethod
    def percent_balance(cls, percent: Decimal) -> "PerOrderSize":
        """A percentage of available Quote_Asset balance per order (``(0, 100]``)."""
        return cls(kind=PerOrderSizeKind.PERCENT_BALANCE, value=percent)


@dataclass(frozen=True)
class RiskProfile:
    """User-configured position sizing, exposure, and risk thresholds.

    ``per_order_size`` drives order sizing (Requirements 7.1, 7.2, 6.9);
    ``max_position_per_token`` and ``max_total_exposure`` are ``>= 0``;
    ``max_acceptable_severity`` gates entry; ``stop_loss_pct`` is in
    ``0.01..100``.
    """

    per_order_size: PerOrderSize
    max_position_per_token: Decimal
    max_total_exposure: Decimal
    max_acceptable_severity: Severity
    stop_loss_pct: Decimal


__all__ = [
    "PositionStatus",
    "Position",
    "PerOrderSizeKind",
    "PerOrderSize",
    "RiskProfile",
]
