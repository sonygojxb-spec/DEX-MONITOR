"""Provider interface contracts and their data-transfer objects.

Design reference: "Data Ingestion Strategy" - external data acquisition and
trade execution sit behind these abstractions so the choice of vendor/chain is
a wiring decision, not an architectural one. Business logic (Security_Inspector,
Backend_Analyzer, Data_Ingestor, Trade_Executor, Notifier) depends only on these
interfaces; concrete adapters (:mod:`dex_agent.providers.adapters`) and in-memory
fakes (:mod:`dex_agent.providers.fakes`) are injected.

The interfaces mirror the design's pseudocode signatures, with the `| Error`
union return types realized as the project-wide
:class:`~dex_agent.result.Result` carrying the typed errors from
:mod:`dex_agent.errors` (``NotFound`` / ``ProviderError`` / ``Unverified`` /
``TimedOut``). No method raises across the boundary - failures are values.

The five abstractions are:

* :class:`MarketDataProvider`     - resolve pairs, fetch snapshots, discovery.
* :class:`ChainDataProvider`      - contract/mint state, holders, tx stream.
* :class:`ContractInspectorProvider` - security risk inputs (authority + signals).
* :class:`TradeVenueProvider`     - order submission + confirmation polling.
* :class:`NotificationChannel`    - alert delivery.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Mapping

from dex_agent.models import (
    HolderBalance,
    Network,
    OrderKind,
    PairSnapshot,
    Severity,
)
from dex_agent.result import Result

# ---------------------------------------------------------------------------
# MarketDataProvider DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiscoveryFilters:
    """Filters for :meth:`MarketDataProvider.discover_recent_pairs` (Req 1.5/1.6).

    ``exchange`` selects the discovery source (e.g. ``"pumpfun"`` for the
    Moralis Pump.fun new-tokens endpoint). ``quote_assets`` restricts results to
    the supported quote assets; ``max_age`` is the freshness window (<24h per
    Req 1.5); ``min_liquidity`` and ``search_query`` are optional refinements.
    """

    exchange: str | None = None
    quote_assets: frozenset[str] | None = None
    max_age: timedelta = timedelta(hours=24)
    min_liquidity: Decimal | None = None
    search_query: str | None = None


# ---------------------------------------------------------------------------
# ChainDataProvider DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContractArtifact:
    """SPL mint / contract state used by the Security_Inspector (Req 2.4/2.5).

    The authority fields (``mint_authority`` / ``freeze_authority`` /
    ``has_transfer_fee_extension``) are authoritative when sourced from the
    Solana RPC SPL mint read; a ``None`` authority means renounced/absent. The
    metadata fields (``update_authority`` / ``is_mutable`` / ``is_verified`` /
    ``possible_spam`` / ``score``) are supporting risk inputs from Moralis token
    metadata. ``raw`` retains the untouched provider payload.
    """

    token_address: str
    network: Network
    mint_authority: str | None = None
    freeze_authority: str | None = None
    has_transfer_fee_extension: bool = False
    is_token_2022: bool = False
    update_authority: str | None = None
    is_mutable: bool | None = None
    is_verified: bool | None = None
    possible_spam: bool | None = None
    score: Decimal | None = None
    raw: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class StateHash:
    """An opaque digest of contract/mint state for change detection (Req 2.10)."""

    value: str


@dataclass(frozen=True)
class TxWindow:
    """A half-open ``[start, end]`` time window over the transaction stream."""

    start: datetime
    end: datetime


@dataclass(frozen=True)
class ChainTx:
    """A single swap/transfer used for wallet-behavior analysis (Req 3.1-3.3).

    Maps the Moralis swaps fields ``walletAddress`` / ``transactionType`` /
    ``bought`` / ``sold`` / ``blockTimestamp`` (and the Solana tx ``signature``).
    ``tx_type`` is normalized lower-case (``"buy"`` / ``"sell"``).
    """

    signature: str
    wallet_address: str
    tx_type: str
    bought_amount: Decimal | None
    sold_amount: Decimal | None
    block_time: datetime
    raw: Mapping[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ContractInspectorProvider DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SecurityInputs:
    """Combined security risk inputs for the Security_Inspector (Task 7).

    Authority fields are authoritative only when ``authority_source`` is set
    (the Solana RPC SPL mint read). The supporting risk signals come from
    Moralis token metadata / Token Score (or the GoPlus fallback). Each provider
    fills only the fields it can supply; the Security_Inspector merges inputs
    from multiple providers. ``raw`` retains the untouched provider payload.
    """

    token_address: str
    # authoritative (Solana RPC SPL mint) when authority_source is set
    mint_authority: str | None = None
    freeze_authority: str | None = None
    has_transfer_fee_extension: bool | None = None
    is_token_2022: bool | None = None
    authority_source: str | None = None
    # supporting risk signals (Moralis metadata / Token Score / GoPlus)
    update_authority: str | None = None
    is_mutable: bool | None = None
    is_verified: bool | None = None
    possible_spam: bool | None = None
    score: Decimal | None = None
    signal_source: str | None = None
    raw: Mapping[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# TradeVenueProvider DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrderRequest:
    """A swap request submitted to the trade venue (Req 6.1/6.2/6.4).

    ``input_mint`` / ``output_mint`` and ``amount`` describe the swap;
    ``max_slippage`` is the user-configured slippage tolerance (percent) attached
    to the order (Req 6.4). ``signed_transaction`` carries an already-signed
    serialized transaction when the caller signs out of band; otherwise the
    adapter requests a serialized tx and signs it via the injected signer
    (wired in Task 15.2 - never key material across this boundary).
    """

    pair_id: str
    kind: OrderKind
    input_mint: str
    output_mint: str
    amount: Decimal
    max_slippage: Decimal
    signed_transaction: str | None = None


@dataclass(frozen=True)
class SubmittedOrder:
    """The venue's acknowledgement that an order was accepted for execution."""

    tx_id: str
    pair_id: str
    kind: OrderKind
    submitted_at: datetime
    raw: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Confirmation:
    """On-chain confirmation outcome polled after submission (Req 6.5/6.6/6.8).

    ``executed_slippage`` is compared against the order's ``max_slippage`` to
    detect a slippage breach (Req 6.8).
    """

    tx_id: str
    confirmed: bool
    executed_price: Decimal | None
    executed_qty: Decimal | None
    fee: Decimal | None
    executed_slippage: Decimal | None
    confirmed_at: datetime
    raw: Mapping[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# NotificationChannel DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Alert:
    """A notification payload delivered through a :class:`NotificationChannel`.

    ``severity`` and ``is_exit_signal`` drive the Notifier's always-deliver /
    quiet-hours policy (Req 8.6); they are carried here so a channel can render
    them, but the policy itself lives in the Notifier (Task 17).
    """

    title: str
    body: str
    severity: Severity = Severity.NONE
    pair_id: str | None = None
    is_exit_signal: bool = False


@dataclass(frozen=True)
class DeliveryResult:
    """The outcome of a single delivery attempt on one channel."""

    channel: str
    delivered: bool
    detail: str = ""


# ---------------------------------------------------------------------------
# Interfaces
# ---------------------------------------------------------------------------


class MarketDataProvider(ABC):
    """Resolves tokens to pairs and returns market snapshots / discovery results.

    Design: ``resolve_pairs``, ``fetch_pair_snapshot``, ``discover_recent_pairs``.
    """

    @abstractmethod
    def resolve_pairs(
        self, token_address: str, network: Network
    ) -> Result[list[PairSnapshot]]:
        """Resolve a Token contract to its Trading_Pair snapshot(s) (Req 1.1).

        Returns ``Err(NotFound)`` when the token has no resolvable pair (Req 1.2).
        """

    @abstractmethod
    def fetch_pair_snapshot(self, pair_id: str) -> Result[PairSnapshot]:
        """Fetch the latest market snapshot for ``pair_id`` (Req 1.7, 4.1-4.3).

        Returns ``Err(ProviderError)`` / ``Err(TimedOut)`` on failure.
        """

    @abstractmethod
    def discover_recent_pairs(
        self, filters: DiscoveryFilters, since: datetime
    ) -> Result[list[PairSnapshot]]:
        """Discover pairs created since ``since`` matching ``filters`` (Req 1.5/1.6)."""


class ChainDataProvider(ABC):
    """Returns contract/mint state, holder distribution, and the tx stream.

    Design: ``fetch_contract``, ``fetch_contract_state_hash``,
    ``fetch_holder_distribution``, ``fetch_transactions``.
    """

    @abstractmethod
    def fetch_contract(
        self, token_address: str, network: Network
    ) -> Result[ContractArtifact]:
        """Fetch SPL mint / contract state (Req 2.4/2.5).

        Returns ``Err(Unverified)`` when the mint cannot be retrieved/parsed,
        or ``Err(ProviderError)`` / ``Err(TimedOut)`` on transport failure.
        """

    @abstractmethod
    def fetch_contract_state_hash(self, token_address: str) -> Result[StateHash]:
        """Return a digest of current contract state for change detection (Req 2.10)."""

    @abstractmethod
    def fetch_holder_distribution(
        self, token_address: str
    ) -> Result[list[HolderBalance]]:
        """Return the token's holder balances for concentration math (Req 3.6/3.7)."""

    @abstractmethod
    def fetch_transactions(
        self, pair_id: str, window: TxWindow
    ) -> Result[list[ChainTx]]:
        """Return swaps/transfers for the pair within ``window`` (Req 3.1-3.3)."""


class ContractInspectorProvider(ABC):
    """Retrieves the security risk inputs for a token (Req 2.4/2.5/2.9).

    Inspects mint/freeze authority and Token-2022 extensions (authoritative via
    Solana RPC) and supporting risk signals (Moralis metadata/Token Score, or
    the GoPlus fallback). Each provider fills only the fields it can supply; the
    Security_Inspector (Task 7) merges them and applies the severity semantics.
    """

    @abstractmethod
    def inspect_token(
        self, token_address: str, network: Network
    ) -> Result[SecurityInputs]:
        """Return the security risk inputs this provider can supply.

        Returns ``Err(Unverified)`` when the subject cannot be analyzed, or
        ``Err(ProviderError)`` / ``Err(TimedOut)`` on transport failure.
        """


class TradeVenueProvider(ABC):
    """Submits swaps to a DEX router and reports on-chain confirmation.

    Design: ``submit_order``, ``poll_confirmation``.
    """

    @abstractmethod
    def submit_order(self, order_request: OrderRequest) -> Result[SubmittedOrder]:
        """Submit ``order_request`` (Req 6.1/6.2/6.4).

        Returns ``Err(ProviderError)`` on a submission failure (Req 6.7).
        """

    @abstractmethod
    def poll_confirmation(
        self, tx_id: str, timeout: timedelta
    ) -> Result[Confirmation]:
        """Poll for on-chain confirmation of ``tx_id`` (Req 6.5/6.6).

        Returns ``Err(TimedOut)`` when confirmation does not arrive within
        ``timeout`` (Req 6.6).
        """


class NotificationChannel(ABC):
    """Delivers an :class:`Alert` over one channel (Req 8.x).

    Design: ``deliver(alert) -> DeliveryResult``. Realized as a ``Result`` so a
    failed delivery is a typed error the Notifier can retry on (Req 8.4/8.5).
    """

    @abstractmethod
    def deliver(self, alert: Alert) -> Result[DeliveryResult]:
        """Attempt to deliver ``alert``.

        Returns ``Ok(DeliveryResult)`` on success, ``Err(ProviderError)`` /
        ``Err(TimedOut)`` on a delivery failure (the Notifier retries).
        """


__all__ = [
    # MarketDataProvider DTOs
    "DiscoveryFilters",
    # ChainDataProvider DTOs
    "ContractArtifact",
    "StateHash",
    "TxWindow",
    "ChainTx",
    # ContractInspectorProvider DTOs
    "SecurityInputs",
    # TradeVenueProvider DTOs
    "OrderRequest",
    "SubmittedOrder",
    "Confirmation",
    # NotificationChannel DTOs
    "Alert",
    "DeliveryResult",
    # interfaces
    "MarketDataProvider",
    "ChainDataProvider",
    "ContractInspectorProvider",
    "TradeVenueProvider",
    "NotificationChannel",
]
