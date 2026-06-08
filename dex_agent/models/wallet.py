"""Wallet / backend analysis models.

Design reference: "Data Models" -> "Wallet / Backend". Covers
:class:`WalletClassification`, :class:`WalletAnalysis`, and
:class:`HolderBalance`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class WalletClassification(Enum):
    """A wallet is classified as exactly one of these (Requirement 3.2)."""

    BOT = "BOT"
    NON_BOT = "NON_BOT"


@dataclass(frozen=True)
class WalletAnalysis:
    """Backend analysis result for a Trading_Pair over a measurement window.

    ``window_minutes`` is in ``1..1440``; ``distinct_wallet_count >= 0``;
    ``bot_tx_percentage`` and ``holder_concentration_pct`` are in ``0..100``.
    ``data_unavailable`` is ``True`` when provider data could not be obtained,
    in which case prior results are retained and no new classification is
    produced (Requirement 3.9).
    """

    pair_id: str
    window_minutes: int
    distinct_wallet_count: int
    bot_tx_percentage: Decimal
    holder_concentration_pct: Decimal
    concentration_risk_flag: bool
    data_unavailable: bool
    analyzed_at: datetime


@dataclass(frozen=True)
class HolderBalance:
    """A single holder's balance, used for top-10 concentration math (Req 3.6)."""

    wallet: str
    balance: Decimal


__all__ = [
    "WalletClassification",
    "WalletAnalysis",
    "HolderBalance",
]
