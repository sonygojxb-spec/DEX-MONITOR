"""In-memory repository implementations.

Design reference: "Persistence Layer (repositories)" and "Concurrency /
Idempotent persistence". These are the concrete, dependency-free backings used
by unit, property, and integration tests (and as a runnable default) while the
durable backend is wired later. Every implementation satisfies the matching
abstract interface in :mod:`dex_agent.repositories.interfaces`.

**Append idempotency.** Each append-style repository stores items in an
insertion-ordered mapping keyed by that repository's idempotency key
(``(pair_id, kind, timestamp)`` for time series and analysis histories, ``tx_id``
for orders, the natural identity for keyed entities). Re-appending an item whose
key already exists is a no-op that returns the already-stored instance, so a
retry can never create a duplicate record.

**Shared query/retention semantics.** The Metrics and Audit repositories reuse
:func:`~dex_agent.repositories.query.entries_in_range` (inclusive, ascending) and
:func:`~dex_agent.repositories.query.older_than` (strictly-older-than boundary)
so both share one tested definition of "in range" and "expired".
"""

from __future__ import annotations

from datetime import datetime, timedelta

from dex_agent.errors import NotFound
from dex_agent.models import (
    AuditRecord,
    AuthorizationRecord,
    Configuration,
    MetricEntry,
    Network,
    OrderRecord,
    OrderStatus,
    Position,
    PositionStatus,
    RiskProfile,
    SecurityEvaluation,
    Signal,
    SignalType,
    Token,
    TradingPair,
    WalletAnalysis,
    WatchlistEntry,
)
from dex_agent.repositories.interfaces import (
    AuditRepository,
    AuthorizationRepository,
    ConfigRepository,
    MetricsRepository,
    OrderRepository,
    PairRepository,
    PositionRepository,
    RiskProfileRepository,
    SecurityEvalRepository,
    SignalRepository,
    TokenRepository,
    WalletAnalysisRepository,
    WatchlistRepository,
)
from dex_agent.repositories.query import entries_in_range, older_than
from dex_agent.result import Err, Ok, Result

# ---------------------------------------------------------------------------
# Identity & market entity repositories
# ---------------------------------------------------------------------------


class InMemoryTokenRepository(TokenRepository):
    """In-memory :class:`TokenRepository` keyed by ``(address, network)``."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, Network], Token] = {}

    def add(self, token: Token) -> Token:
        key = (token.address, token.network)
        # Idempotent: first write wins; a retry returns the stored instance.
        return self._by_key.setdefault(key, token)

    def get(self, address: str, network: Network) -> Result[Token]:
        token = self._by_key.get((address, network))
        if token is None:
            return Err(NotFound("token not found", identifier=address))
        return Ok(token)

    def list_all(self) -> list[Token]:
        return list(self._by_key.values())


class InMemoryPairRepository(PairRepository):
    """In-memory :class:`PairRepository` keyed by ``id``."""

    def __init__(self) -> None:
        self._by_id: dict[str, TradingPair] = {}

    def add(self, pair: TradingPair) -> TradingPair:
        return self._by_id.setdefault(pair.id, pair)

    def get(self, pair_id: str) -> Result[TradingPair]:
        pair = self._by_id.get(pair_id)
        if pair is None:
            return Err(NotFound("trading pair not found", identifier=pair_id))
        return Ok(pair)

    def exists(self, pair_id: str) -> bool:
        return pair_id in self._by_id

    def list_all(self) -> list[TradingPair]:
        return list(self._by_id.values())


class InMemoryWatchlistRepository(WatchlistRepository):
    """In-memory :class:`WatchlistRepository` keyed by ``pair_id``."""

    def __init__(self) -> None:
        self._by_pair: dict[str, WatchlistEntry] = {}

    def add(self, entry: WatchlistEntry) -> WatchlistEntry:
        return self._by_pair.setdefault(entry.pair_id, entry)

    def get(self, pair_id: str) -> Result[WatchlistEntry]:
        entry = self._by_pair.get(pair_id)
        if entry is None:
            return Err(NotFound("watchlist entry not found", identifier=pair_id))
        return Ok(entry)

    def deactivate(self, pair_id: str) -> Result[WatchlistEntry]:
        entry = self._by_pair.get(pair_id)
        if entry is None:
            return Err(NotFound("watchlist entry not found", identifier=pair_id))
        # Retain the entry/data, only flip the active flag (Req 1.3/1.4).
        updated = WatchlistEntry(
            pair_id=entry.pair_id,
            added_at=entry.added_at,
            source=entry.source,
            active=False,
        )
        self._by_pair[pair_id] = updated
        return Ok(updated)

    def list_active(self) -> list[WatchlistEntry]:
        return [e for e in self._by_pair.values() if e.active]

    def list_all(self) -> list[WatchlistEntry]:
        return list(self._by_pair.values())


# ---------------------------------------------------------------------------
# Analysis-result repositories (append-style histories)
# ---------------------------------------------------------------------------


class InMemorySecurityEvalRepository(SecurityEvalRepository):
    """In-memory :class:`SecurityEvalRepository`.

    Idempotent on ``(token_address, evaluated_at)``.
    """

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, datetime], SecurityEvaluation] = {}

    def append(self, evaluation: SecurityEvaluation) -> SecurityEvaluation:
        key = (evaluation.token_address, evaluation.evaluated_at)
        return self._by_key.setdefault(key, evaluation)

    def history(self, token_address: str) -> list[SecurityEvaluation]:
        items = [
            e for e in self._by_key.values() if e.token_address == token_address
        ]
        items.sort(key=lambda e: e.evaluated_at)
        return items

    def latest(self, token_address: str) -> Result[SecurityEvaluation]:
        items = self.history(token_address)
        if not items:
            return Err(NotFound("no security evaluation", identifier=token_address))
        return Ok(items[-1])


class InMemoryWalletAnalysisRepository(WalletAnalysisRepository):
    """In-memory :class:`WalletAnalysisRepository`.

    Idempotent on ``(pair_id, analyzed_at)``.
    """

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, datetime], WalletAnalysis] = {}

    def append(self, analysis: WalletAnalysis) -> WalletAnalysis:
        key = (analysis.pair_id, analysis.analyzed_at)
        return self._by_key.setdefault(key, analysis)

    def history(self, pair_id: str) -> list[WalletAnalysis]:
        items = [a for a in self._by_key.values() if a.pair_id == pair_id]
        items.sort(key=lambda a: a.analyzed_at)
        return items

    def latest(self, pair_id: str) -> Result[WalletAnalysis]:
        items = self.history(pair_id)
        if not items:
            return Err(NotFound("no wallet analysis", identifier=pair_id))
        return Ok(items[-1])


class InMemorySignalRepository(SignalRepository):
    """In-memory :class:`SignalRepository`.

    Idempotent on ``(pair_id, type, generated_at)``.
    """

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, SignalType, datetime], Signal] = {}

    def append(self, signal: Signal) -> Signal:
        key = (signal.pair_id, signal.type, signal.generated_at)
        return self._by_key.setdefault(key, signal)

    def history(self, pair_id: str) -> list[Signal]:
        items = [s for s in self._by_key.values() if s.pair_id == pair_id]
        items.sort(key=lambda s: s.generated_at)
        return items

    def latest(self, pair_id: str, signal_type: SignalType) -> Result[Signal]:
        items = [
            s
            for s in self.history(pair_id)
            if s.type == signal_type
        ]
        if not items:
            return Err(NotFound("no signal of requested type", identifier=pair_id))
        return Ok(items[-1])


# ---------------------------------------------------------------------------
# Metrics time-series repository
# ---------------------------------------------------------------------------


class InMemoryMetricsRepository(MetricsRepository):
    """In-memory :class:`MetricsRepository`.

    Idempotent on ``(pair_id, kind, recorded_at)``; reuses the shared
    range/retention primitives.
    """

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, object, datetime], MetricEntry] = {}
        self._monitored: set[str] = set()

    def register_pair(self, pair_id: str) -> None:
        self._monitored.add(pair_id)

    def is_monitored(self, pair_id: str) -> bool:
        return pair_id in self._monitored

    def append(self, entry: MetricEntry) -> MetricEntry:
        self._monitored.add(entry.pair_id)
        key = (entry.pair_id, entry.kind, entry.recorded_at)
        return self._by_key.setdefault(key, entry)

    def all_entries(self, pair_id: str) -> list[MetricEntry]:
        items = [e for e in self._by_key.values() if e.pair_id == pair_id]
        items.sort(key=lambda e: e.recorded_at)
        return items

    def query_range(
        self, pair_id: str, start: datetime, end: datetime
    ) -> Result[list[MetricEntry]]:
        if not self.is_monitored(pair_id):
            return Err(NotFound("trading pair is not monitored", identifier=pair_id))
        in_range = entries_in_range(self.all_entries(pair_id), start, end)
        return Ok(in_range)

    def purge_older_than(
        self, period: timedelta, *, now: datetime | None = None
    ) -> list[MetricEntry]:
        expired = older_than(self._by_key.values(), period, now=now)
        for entry in expired:
            del self._by_key[(entry.pair_id, entry.kind, entry.recorded_at)]
        return expired


# ---------------------------------------------------------------------------
# Position / Order repositories
# ---------------------------------------------------------------------------


class InMemoryPositionRepository(PositionRepository):
    """In-memory :class:`PositionRepository` keyed by ``pair_id``."""

    def __init__(self) -> None:
        self._by_pair: dict[str, Position] = {}

    def upsert(self, position: Position) -> Position:
        self._by_pair[position.pair_id] = position
        return position

    def get(self, pair_id: str) -> Result[Position]:
        position = self._by_pair.get(pair_id)
        if position is None:
            return Err(NotFound("position not found", identifier=pair_id))
        return Ok(position)

    def list_open(self) -> list[Position]:
        return [
            p for p in self._by_pair.values() if p.status == PositionStatus.OPEN
        ]

    def list_all(self) -> list[Position]:
        return list(self._by_pair.values())


class InMemoryOrderRepository(OrderRepository):
    """In-memory :class:`OrderRepository`.

    Idempotent on ``tx_id`` when present, otherwise on
    ``(pair_id, kind, recorded_at)``.
    """

    def __init__(self) -> None:
        # Insertion-ordered store keyed by the order's idempotency key.
        self._by_key: dict[object, OrderRecord] = {}

    @staticmethod
    def _key(order: OrderRecord) -> object:
        if order.tx_id is not None:
            return ("tx", order.tx_id)
        return ("syn", order.pair_id, order.kind, order.recorded_at)

    def append(self, order: OrderRecord) -> OrderRecord:
        return self._by_key.setdefault(self._key(order), order)

    def _for_pair(self, pair_id: str) -> list[OrderRecord]:
        items = [o for o in self._by_key.values() if o.pair_id == pair_id]
        items.sort(key=lambda o: o.recorded_at)
        return items

    def has_in_flight(self, pair_id: str) -> bool:
        return any(
            o.status == OrderStatus.SUBMITTED for o in self._for_pair(pair_id)
        )

    def in_flight(self, pair_id: str) -> Result[OrderRecord]:
        for order in self._for_pair(pair_id):
            if order.status == OrderStatus.SUBMITTED:
                return Ok(order)
        return Err(NotFound("no in-flight order", identifier=pair_id))

    def list_for_pair(self, pair_id: str) -> list[OrderRecord]:
        return self._for_pair(pair_id)

    def list_non_terminal(self) -> list[OrderRecord]:
        return [
            o for o in self._by_key.values() if not o.status.is_terminal()
        ]


# ---------------------------------------------------------------------------
# Singleton configuration repositories
# ---------------------------------------------------------------------------


class InMemoryRiskProfileRepository(RiskProfileRepository):
    """In-memory :class:`RiskProfileRepository` holding the active profile."""

    def __init__(self) -> None:
        self._profile: RiskProfile | None = None

    def save(self, profile: RiskProfile) -> RiskProfile:
        self._profile = profile
        return profile

    def get(self) -> Result[RiskProfile]:
        if self._profile is None:
            return Err(NotFound("no risk profile configured"))
        return Ok(self._profile)


class InMemoryConfigRepository(ConfigRepository):
    """In-memory :class:`ConfigRepository` holding the latest configuration."""

    def __init__(self) -> None:
        self._configuration: Configuration | None = None

    def save(self, configuration: Configuration) -> Configuration:
        self._configuration = configuration
        return configuration

    def latest(self) -> Result[Configuration]:
        if self._configuration is None:
            return Err(NotFound("no persisted configuration"))
        return Ok(self._configuration)


# ---------------------------------------------------------------------------
# Audit & Authorization repositories
# ---------------------------------------------------------------------------


class InMemoryAuditRepository(AuditRepository):
    """In-memory :class:`AuditRepository`.

    Idempotent on ``(action_type, pair_id, recorded_at)``; reuses the shared
    range/retention primitives so its semantics match the Metrics repository.
    """

    def __init__(self) -> None:
        self._by_key: dict[tuple[object, str, datetime], AuditRecord] = {}

    def append(self, record: AuditRecord) -> AuditRecord:
        key = (record.action_type, record.pair_id, record.recorded_at)
        return self._by_key.setdefault(key, record)

    def all_records(self, pair_id: str) -> list[AuditRecord]:
        items = [r for r in self._by_key.values() if r.pair_id == pair_id]
        items.sort(key=lambda r: r.recorded_at)
        return items

    def query_range(
        self, pair_id: str, start: datetime, end: datetime
    ) -> list[AuditRecord]:
        return entries_in_range(self.all_records(pair_id), start, end)

    def purge_older_than(
        self, period: timedelta, *, now: datetime | None = None
    ) -> list[AuditRecord]:
        expired = older_than(self._by_key.values(), period, now=now)
        for record in expired:
            del self._by_key[
                (record.action_type, record.pair_id, record.recorded_at)
            ]
        return expired


class InMemoryAuthorizationRepository(AuthorizationRepository):
    """In-memory :class:`AuthorizationRepository`.

    Idempotent on ``(wallet_id, status, changed_at)``.
    """

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, object, datetime], AuthorizationRecord] = {}

    def append(self, record: AuthorizationRecord) -> AuthorizationRecord:
        key = (record.wallet_id, record.status, record.changed_at)
        return self._by_key.setdefault(key, record)

    def history(self, wallet_id: str) -> list[AuthorizationRecord]:
        items = [r for r in self._by_key.values() if r.wallet_id == wallet_id]
        items.sort(key=lambda r: r.changed_at)
        return items

    def latest(self, wallet_id: str) -> Result[AuthorizationRecord]:
        items = self.history(wallet_id)
        if not items:
            return Err(NotFound("no authorization record", identifier=wallet_id))
        return Ok(items[-1])


__all__ = [
    "InMemoryTokenRepository",
    "InMemoryPairRepository",
    "InMemoryWatchlistRepository",
    "InMemorySecurityEvalRepository",
    "InMemoryWalletAnalysisRepository",
    "InMemorySignalRepository",
    "InMemoryMetricsRepository",
    "InMemoryPositionRepository",
    "InMemoryOrderRepository",
    "InMemoryRiskProfileRepository",
    "InMemoryConfigRepository",
    "InMemoryAuditRepository",
    "InMemoryAuthorizationRepository",
]
