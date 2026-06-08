"""Identity and market data models.

Design reference: "Data Models" -> "Identity & Market". Covers
:class:`Network`, :class:`Token`, :class:`TradingPair`, :class:`WatchlistEntry`,
:class:`PairSnapshot`, and the shared :class:`AuditInfo` value object.

All models are immutable (frozen) dataclasses, consistent with the Task 1 style.
``TradingPair.quote_asset`` is constrained to the supported quote assets for the
initial Solana deployment (SOL and USDC, see "External Integrations" -> "Scope");
the :func:`make_trading_pair` factory is the validation point and returns a
:class:`~dex_agent.result.Result` so construction can fail without raising.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from dex_agent.errors import NotFound
from dex_agent.result import Err, Ok, Result


class Network(Enum):
    """Chain identifier for a Token.

    The initial deployment targets Solana (see "External Integrations" ->
    "Scope"); the abstraction is retained so additional chains can be wired
    later without architectural change.
    """

    SOLANA = "solana"


# Supported quote assets for the initial Solana deployment. ``TradingPair`` is
# constrained to these (design "External Integrations" -> "Scope").
SUPPORTED_QUOTE_ASSETS: frozenset[str] = frozenset({"SOL", "USDC"})


class WatchlistSource(Enum):
    """How a watchlist entry was added."""

    MANUAL = "MANUAL"
    AUTO_DISCOVERY = "AUTO_DISCOVERY"


@dataclass(frozen=True)
class AuditInfo:
    """Optional third-party audit / security metadata for a Token.

    Design "Data Models": ``AuditInfo { provider, result, audit_date }``. Used
    by :class:`PairSnapshot` and by the Metrics_Tracker (Requirement 4.5).
    """

    provider: str
    result: str
    audit_date: date


@dataclass(frozen=True)
class Token:
    """A tradable on-chain asset identified by a contract address.

    ``address`` is unique per ``network``.
    """

    address: str
    network: Network
    symbol: str
    name: str
    total_supply: Decimal


@dataclass(frozen=True)
class TradingPair:
    """A market pairing a :class:`Token` with a quote asset on a DEX.

    Construct via :func:`make_trading_pair` to enforce the supported quote-asset
    constraint. ``created_at`` is the first-listed time, used for the <24h
    auto-discovery filter (Requirement 1.5).
    """

    id: str
    token: Token
    quote_asset: str
    dex: str
    created_at: datetime


@dataclass(frozen=True)
class WatchlistEntry:
    """A Trading_Pair entry on the user's Watchlist.

    ``active`` becomes ``False`` after removal while the collected data is
    retained (Requirement 1.4).
    """

    pair_id: str
    added_at: datetime
    source: WatchlistSource
    active: bool = True


@dataclass(frozen=True)
class PairSnapshot:
    """One ingestion sample of a Trading_Pair's market state.

    ``fetched_at`` is recorded to second-level precision. ``is_stale`` is
    ``True`` when the snapshot is the last-good value served after a fetch
    failure (Requirements 1.8, 1.9).
    """

    pair_id: str
    price: Decimal
    liquidity: Decimal
    market_cap: Decimal
    fdv: Decimal
    buy_count: int
    sell_count: int
    buy_volume: Decimal
    sell_volume: Decimal
    fetched_at: datetime
    audit: AuditInfo | None = None
    is_stale: bool = False


def make_trading_pair(
    *,
    id: str,
    token: Token,
    quote_asset: str,
    dex: str,
    created_at: datetime,
) -> Result[TradingPair]:
    """Construct a :class:`TradingPair`, validating the quote asset.

    For the initial Solana deployment the quote asset must be one of
    :data:`SUPPORTED_QUOTE_ASSETS` (``SOL`` or ``USDC``). An unsupported quote
    asset yields an :class:`~dex_agent.errors.NotFound` error (the asset is not
    present in the supported-quote-asset registry), reusing the Task 1 error
    taxonomy rather than introducing a parallel one.

    Returns:
        ``Ok(TradingPair)`` when the quote asset is supported, otherwise
        ``Err(NotFound)`` identifying the offending quote asset.
    """
    if quote_asset not in SUPPORTED_QUOTE_ASSETS:
        return Err(
            NotFound(
                "unsupported quote asset for the initial Solana deployment "
                f"(supported: {sorted(SUPPORTED_QUOTE_ASSETS)})",
                identifier=quote_asset,
            )
        )
    return Ok(
        TradingPair(
            id=id,
            token=token,
            quote_asset=quote_asset,
            dex=dex,
            created_at=created_at,
        )
    )


__all__ = [
    "Network",
    "SUPPORTED_QUOTE_ASSETS",
    "WatchlistSource",
    "AuditInfo",
    "Token",
    "TradingPair",
    "WatchlistEntry",
    "PairSnapshot",
    "make_trading_pair",
]
