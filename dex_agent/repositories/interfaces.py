"""Repository interface contracts (abstract base classes).

Design reference: "Persistence Layer (repositories)" - the durable storage,
audit, and retention layer that sits behind every component. All persistence is
accessed only through these interfaces and is injected (see the Implementation
Plan "Conventions"); concrete in-memory implementations live in
:mod:`dex_agent.repositories.memory`, and durable backends can be wired later
without changing any caller.

The interfaces cover the twelve repositories named in the design's persistence
diagram: Tokens, Pairs, Watchlist, SecurityEval, WalletAnalysis, Metrics
time-series, Signals, Positions, RiskProfile, Config, Audit, and Authorization.

Conventions shared by all repositories (design "Error model" + "Concurrency /
Idempotent persistence"):

* Operations that can fail return an explicit :class:`~dex_agent.result.Result`
  carrying a typed error (e.g. :class:`~dex_agent.errors.NotFound`) rather than
  raising across the boundary.
* Append operations are **idempotent**: re-appending an item with the same
  idempotency key (``(pair_id, kind, timestamp)`` for time series, ``tx_id`` for
  orders, the natural identity for keyed entities) does not create a duplicate.
* Time-series range queries are inclusive of both bounds and ordered ascending;
  retention deletes records strictly older than the retention boundary (both via
  the shared primitives in :mod:`dex_agent.repositories.query`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from dex_agent.models import (
    AuditRecord,
    AuthorizationRecord,
    Configuration,
    MetricEntry,
    Network,
    OrderRecord,
    PairSnapshot,
    Position,
    RiskProfile,
    SecurityEvaluation,
    Signal,
    SignalType,
    Token,
    TradingPair,
    WalletAnalysis,
    WatchlistEntry,
)
from dex_agent.result import Result

# ---------------------------------------------------------------------------
# Identity & market entity repositories
# ---------------------------------------------------------------------------


class TokenRepository(ABC):
    """Stores :class:`Token` entities keyed by ``(address, network)``."""

    @abstractmethod
    def add(self, token: Token) -> Token:
        """Persist ``token`` (idempotent on ``(address, network)``).

        Returns the stored token; re-adding the same identity is a no-op that
        returns the already-stored instance.
        """

    @abstractmethod
    def get(self, address: str, network: Network) -> Result[Token]:
        """Return the token for ``(address, network)`` or ``Err(NotFound)``."""

    @abstractmethod
    def list_all(self) -> list[Token]:
        """Return all stored tokens in insertion order."""


class PairRepository(ABC):
    """Stores :class:`TradingPair` entities keyed by ``id``."""

    @abstractmethod
    def add(self, pair: TradingPair) -> TradingPair:
        """Persist ``pair`` (idempotent on ``id``)."""

    @abstractmethod
    def get(self, pair_id: str) -> Result[TradingPair]:
        """Return the pair for ``pair_id`` or ``Err(NotFound)``."""

    @abstractmethod
    def exists(self, pair_id: str) -> bool:
        """True iff a pair with ``pair_id`` is stored."""

    @abstractmethod
    def list_all(self) -> list[TradingPair]:
        """Return all stored pairs in insertion order."""


class WatchlistRepository(ABC):
    """Stores :class:`WatchlistEntry` records keyed by ``pair_id``.

    Removal deactivates an entry (``active = False``) while retaining the
    collected data (Requirements 1.3, 1.4).
    """

    @abstractmethod
    def add(self, entry: WatchlistEntry) -> WatchlistEntry:
        """Persist ``entry`` (idempotent on ``pair_id``)."""

    @abstractmethod
    def get(self, pair_id: str) -> Result[WatchlistEntry]:
        """Return the entry for ``pair_id`` or ``Err(NotFound)``."""

    @abstractmethod
    def deactivate(self, pair_id: str) -> Result[WatchlistEntry]:
        """Mark the entry inactive, retaining data (Req 1.3/1.4).

        Returns the updated (inactive) entry, or ``Err(NotFound)`` when no entry
        exists for ``pair_id``.
        """

    @abstractmethod
    def list_active(self) -> list[WatchlistEntry]:
        """Return all entries with ``active == True`` (Req 13.3 recovery)."""

    @abstractmethod
    def list_all(self) -> list[WatchlistEntry]:
        """Return all entries (active and inactive) in insertion order."""


# ---------------------------------------------------------------------------
# Analysis-result repositories (append-style histories)
# ---------------------------------------------------------------------------


class SecurityEvalRepository(ABC):
    """Stores :class:`SecurityEvaluation` results per token.

    Appends are idempotent on ``(token_address, evaluated_at)``.
    """

    @abstractmethod
    def append(self, evaluation: SecurityEvaluation) -> SecurityEvaluation:
        """Persist an evaluation (idempotent on ``(token_address, evaluated_at)``)."""

    @abstractmethod
    def latest(self, token_address: str) -> Result[SecurityEvaluation]:
        """Return the most recent evaluation for the token or ``Err(NotFound)``."""

    @abstractmethod
    def history(self, token_address: str) -> list[SecurityEvaluation]:
        """Return all evaluations for the token, ascending by ``evaluated_at``."""


class WalletAnalysisRepository(ABC):
    """Stores :class:`WalletAnalysis` results per Trading_Pair.

    Appends are idempotent on ``(pair_id, analyzed_at)``.
    """

    @abstractmethod
    def append(self, analysis: WalletAnalysis) -> WalletAnalysis:
        """Persist an analysis (idempotent on ``(pair_id, analyzed_at)``)."""

    @abstractmethod
    def latest(self, pair_id: str) -> Result[WalletAnalysis]:
        """Return the most recent analysis for the pair or ``Err(NotFound)``."""

    @abstractmethod
    def history(self, pair_id: str) -> list[WalletAnalysis]:
        """Return all analyses for the pair, ascending by ``analyzed_at``."""


class SignalRepository(ABC):
    """Stores generated :class:`Signal` records per Trading_Pair.

    Appends are idempotent on ``(pair_id, type, generated_at)`` (Req 5.6).
    """

    @abstractmethod
    def append(self, signal: Signal) -> Signal:
        """Persist a signal (idempotent on ``(pair_id, type, generated_at)``)."""

    @abstractmethod
    def latest(self, pair_id: str, signal_type: SignalType) -> Result[Signal]:
        """Return the most recent signal of ``signal_type`` for the pair."""

    @abstractmethod
    def history(self, pair_id: str) -> list[Signal]:
        """Return all signals for the pair, ascending by ``generated_at``."""


# ---------------------------------------------------------------------------
# Metrics time-series repository
# ---------------------------------------------------------------------------


class MetricsRepository(ABC):
    """Stores the :class:`MetricEntry` time series per Trading_Pair.

    Appends are idempotent on ``(pair_id, kind, recorded_at)`` so a retried
    record cannot create a duplicate point (design "Idempotent persistence").
    Range queries are inclusive and ascending (Requirements 4.4, 4.6); retention
    deletes points strictly older than the boundary (Requirement 10.6).

    A pair is "monitored" once it has been registered (explicitly or implicitly
    by its first append). Querying an unmonitored pair fails with
    :class:`~dex_agent.errors.NotFound` (Requirement 4.8), which is distinct from
    a monitored pair that simply has no points in range (Requirement 4.9 returns
    an empty result without error).
    """

    @abstractmethod
    def register_pair(self, pair_id: str) -> None:
        """Mark ``pair_id`` as monitored so range queries succeed (Req 4.8/4.9)."""

    @abstractmethod
    def is_monitored(self, pair_id: str) -> bool:
        """True iff ``pair_id`` has been registered/monitored."""

    @abstractmethod
    def append(self, entry: MetricEntry) -> MetricEntry:
        """Persist a metric point (idempotent on ``(pair_id, kind, recorded_at)``).

        Appending also registers the pair as monitored.
        """

    @abstractmethod
    def query_range(
        self, pair_id: str, start: datetime, end: datetime
    ) -> Result[list[MetricEntry]]:
        """Return the pair's points within ``[start, end]`` ascending (Req 4.6).

        Returns ``Err(NotFound)`` when the pair is not monitored (Req 4.8);
        otherwise ``Ok(list)`` - possibly empty when no point falls in range
        (Req 4.9).
        """

    @abstractmethod
    def all_entries(self, pair_id: str) -> list[MetricEntry]:
        """Return all points for the pair, ascending by ``recorded_at``."""

    @abstractmethod
    def purge_older_than(
        self, period: timedelta, *, now: datetime | None = None
    ) -> list[MetricEntry]:
        """Delete points strictly older than ``now - period`` (Req 10.6).

        Returns the removed points.
        """


# ---------------------------------------------------------------------------
# Position / Order repositories
# ---------------------------------------------------------------------------


class PositionRepository(ABC):
    """Stores :class:`Position` records keyed by ``pair_id`` (one per pair)."""

    @abstractmethod
    def upsert(self, position: Position) -> Position:
        """Insert or replace the position for ``position.pair_id``."""

    @abstractmethod
    def get(self, pair_id: str) -> Result[Position]:
        """Return the position for ``pair_id`` or ``Err(NotFound)``."""

    @abstractmethod
    def list_open(self) -> list[Position]:
        """Return all positions with ``status == OPEN`` (Req 13.1 recovery)."""

    @abstractmethod
    def list_all(self) -> list[Position]:
        """Return all positions in insertion order."""


class OrderRepository(ABC):
    """Stores :class:`OrderRecord` entries and enforces in-flight tracking.

    Appends are idempotent on ``tx_id`` when present, otherwise on
    ``(pair_id, kind, recorded_at)`` (design "Idempotent persistence"). At most
    one non-terminal (``SUBMITTED``) order may exist per ``pair_id`` at a time
    (Requirement 12.1).
    """

    @abstractmethod
    def append(self, order: OrderRecord) -> OrderRecord:
        """Persist an order (idempotent on ``tx_id`` / ``(pair_id, kind, recorded_at)``)."""

    @abstractmethod
    def has_in_flight(self, pair_id: str) -> bool:
        """True iff a non-terminal (``SUBMITTED``) order exists for the pair (Req 12.1)."""

    @abstractmethod
    def in_flight(self, pair_id: str) -> Result[OrderRecord]:
        """Return the in-flight order for the pair or ``Err(NotFound)``."""

    @abstractmethod
    def list_for_pair(self, pair_id: str) -> list[OrderRecord]:
        """Return all orders for the pair, ascending by ``recorded_at``."""

    @abstractmethod
    def list_non_terminal(self) -> list[OrderRecord]:
        """Return all non-terminal orders (recovery reconciliation, Req 13)."""


# ---------------------------------------------------------------------------
# Singleton configuration repositories
# ---------------------------------------------------------------------------


class RiskProfileRepository(ABC):
    """Stores the single active :class:`RiskProfile` (most recent wins)."""

    @abstractmethod
    def save(self, profile: RiskProfile) -> RiskProfile:
        """Persist ``profile`` as the active risk profile."""

    @abstractmethod
    def get(self) -> Result[RiskProfile]:
        """Return the active risk profile or ``Err(NotFound)`` when unset."""


class ConfigRepository(ABC):
    """Stores persisted :class:`Configuration` snapshots (most recent wins)."""

    @abstractmethod
    def save(self, configuration: Configuration) -> Configuration:
        """Persist ``configuration`` as the latest configuration (Req 9.4)."""

    @abstractmethod
    def latest(self) -> Result[Configuration]:
        """Return the most recently persisted configuration (Req 9.5).

        Returns ``Err(NotFound)`` when none has been persisted, so the caller can
        fall back to documented defaults (Req 9.6).
        """


# ---------------------------------------------------------------------------
# Audit & Authorization repositories
# ---------------------------------------------------------------------------


class AuditRepository(ABC):
    """Append-only :class:`AuditRecord` trail with range queries and retention.

    Appends are idempotent on ``(action_type, pair_id, recorded_at)``. Range
    queries are inclusive and ordered oldest-to-newest (Requirement 10.2);
    retention deletes records strictly older than the boundary (Req 10.6).
    """

    @abstractmethod
    def append(self, record: AuditRecord) -> AuditRecord:
        """Persist an audit record (idempotent on ``(action_type, pair_id, recorded_at)``)."""

    @abstractmethod
    def query_range(
        self, pair_id: str, start: datetime, end: datetime
    ) -> list[AuditRecord]:
        """Return the pair's records within ``[start, end]`` ascending (Req 10.2).

        Possibly empty when no record falls in range (Req 10.3).
        """

    @abstractmethod
    def all_records(self, pair_id: str) -> list[AuditRecord]:
        """Return all records for the pair, ascending by ``recorded_at``."""

    @abstractmethod
    def purge_older_than(
        self, period: timedelta, *, now: datetime | None = None
    ) -> list[AuditRecord]:
        """Delete records strictly older than ``now - period`` (Req 10.6).

        Returns the removed records.
        """


class AuthorizationRepository(ABC):
    """Append-only log of :class:`AuthorizationRecord` status changes (Req 11.6)."""

    @abstractmethod
    def append(self, record: AuthorizationRecord) -> AuthorizationRecord:
        """Persist an authorization status change (idempotent on ``(wallet_id, status, changed_at)``)."""

    @abstractmethod
    def latest(self, wallet_id: str) -> Result[AuthorizationRecord]:
        """Return the most recent authorization record for the wallet."""

    @abstractmethod
    def history(self, wallet_id: str) -> list[AuthorizationRecord]:
        """Return all authorization records for the wallet, ascending by ``changed_at``."""


__all__ = [
    "TokenRepository",
    "PairRepository",
    "WatchlistRepository",
    "SecurityEvalRepository",
    "WalletAnalysisRepository",
    "SignalRepository",
    "MetricsRepository",
    "PositionRepository",
    "OrderRepository",
    "RiskProfileRepository",
    "ConfigRepository",
    "AuditRepository",
    "AuthorizationRepository",
]
