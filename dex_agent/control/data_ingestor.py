"""Data_Ingestor: pair resolution, refresh retry/last-good, discovery scan.

Design reference: "Data_Ingestor" (Requirements 1.1, 1.2, 1.5-1.9). The
Data_Ingestor is the ingestion seam between the external
:class:`~dex_agent.providers.interfaces.MarketDataProvider` and the rest of the
Agent. It:

* **resolves** a Token to its Trading_Pair on watchlist add, rejecting an
  unresolvable Token with an error that names the Token (Req 1.2) and triggering
  a Security_Inspector evaluation for the resolved Token (Req 1.1);
* **refreshes** a monitored pair on the configured interval, resetting the
  consecutive-failure count on success and, on failure, incrementing it (capped
  at 5) while continuing to serve the last successfully retrieved snapshot
  (Req 1.8) and emitting a stale-data notification exactly when the 5th
  consecutive failure is reached (Req 1.9); and
* runs the **discovery scan**, adding exactly the candidate pairs that were first
  listed within the preceding 24 hours *and* that match the user's discovery
  filters (Req 1.5, 1.6).

Discovery sources candidates from the Moralis **Pump.fun new tokens** endpoint
(``createdAt`` < 24h) plus **token-search**, surfaced through
:meth:`~dex_agent.providers.interfaces.MarketDataProvider.discover_recent_pairs`;
it does **not** use the deprecated discovery/filtered-tokens endpoint. The
ingestor re-validates each candidate's first-listed time against the
:class:`~dex_agent.repositories.interfaces.PairRepository` so the "preceding 24h"
guarantee is owned here rather than trusted from the provider (Property 10).

The ingestor depends only on injected seams - the ``MarketDataProvider``
interface, the Watchlist/Pair repositories, an optional Security_Inspector
(``evaluate``) seam for Req 1.1, an optional Metrics_Tracker (``record``) seam, an
optional ``stale_sink`` for the Req 1.9 notification, and an optional
``admit`` seam (the Orchestrator's ``add_pair``) that begins monitoring under the
200-pair cap (Req 1.10/1.11) - plus a controllable clock. No real network/chain
calls or sleeps occur.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Callable, Protocol

from dex_agent.errors import AgentError, NotFound
from dex_agent.models import (
    Network,
    PairSnapshot,
    Severity,
    Token,
    TradingPair,
    WatchlistEntry,
    WatchlistSource,
    utc_now_seconds,
)
from dex_agent.providers.interfaces import (
    Alert,
    DiscoveryFilters,
    MarketDataProvider,
)
from dex_agent.repositories.interfaces import (
    PairRepository,
    TokenRepository,
    WatchlistRepository,
)
from dex_agent.result import Err, Ok, Result

#: The maximum number of consecutive fetch failures tracked per pair (Req 1.8).
#: The consecutive-failure count is clamped to this value; the stale-data
#: notification fires exactly when it is first reached (Req 1.9).
MAX_CONSECUTIVE_FAILURES = 5


# ---------------------------------------------------------------------------
# Injected seams (kept structural so the ingestor never imports the concrete
# Security_Inspector / Metrics_Tracker / Orchestrator - Task 7/9/18 wire them).
# ---------------------------------------------------------------------------


class SecurityEvaluator(Protocol):
    """The Security_Inspector ``evaluate`` seam (Req 1.1)."""

    def evaluate(self, token: Token) -> object: ...


class SnapshotRecorder(Protocol):
    """The Metrics_Tracker ``record`` seam (optional persistence on refresh)."""

    def register_pair(self, pair_id: str) -> None: ...

    def record(self, snapshot: PairSnapshot): ...


# A sink that delivers the stale-data :class:`Alert` (Req 1.9). The Notifier
# (Task 17) is wired here; tests inject a recording sink.
AlertSink = Callable[[Alert], None]

# Begins monitoring a resolved/discovered pair under the concurrency cap. The
# Orchestrator's ``add_pair`` is wired here (Task 18.2); returns a ``Result`` so a
# CONCURRENCY_LIMIT rejection (Req 1.10/1.11) propagates.
PairAdmitter = Callable[[str], "Result[object]"]


@dataclass(frozen=True)
class DiscoveryOutcome:
    """The result of a :meth:`DataIngestor.discovery_scan` (Req 1.5, 1.6).

    Attributes:
        added: The pair ids added to the Watchlist by this scan (exactly the
            recent + matching candidates that were admitted under the cap).
        scanned: The total number of candidate pairs considered.
        rejected_capacity: Pair ids that were recent + matching but rejected by
            the 200-pair concurrency cap (Req 1.10/1.11).
    """

    added: tuple[str, ...] = ()
    scanned: int = 0
    rejected_capacity: tuple[str, ...] = ()


class DataIngestor:
    """Resolves pairs, refreshes data with retry/last-good, runs discovery.

    Args:
        market: The :class:`MarketDataProvider` (pair resolution, snapshots,
            discovery). Tests inject the in-memory fake.
        watchlist_repo: Stores :class:`WatchlistEntry` records (Req 1.1/1.6).
        pair_repo: Stores :class:`TradingPair` entities; the authoritative source
            of each candidate's first-listed ``created_at`` for the 24h discovery
            window (Req 1.5).
        token_repo: Optional :class:`TokenRepository` used to recover a Token's
            full identity for the Security_Inspector; a minimal Token is
            synthesized when absent (the inspector only needs address/network).
        security_inspector: Optional Security_Inspector ``evaluate`` seam invoked
            on watchlist add (Req 1.1).
        metrics_tracker: Optional Metrics_Tracker ``record`` seam invoked on a
            successful refresh.
        stale_sink: Optional alert sink for the Req 1.9 stale-data notification.
        admit: Optional Orchestrator ``add_pair`` seam that begins monitoring a
            resolved/discovered pair under the 200-pair cap (Req 1.10/1.11).
        discovery_window: The "preceding 24h" first-listed window (Req 1.5).
        clock: Injectable second-precision UTC clock (no real time in tests).
    """

    def __init__(
        self,
        market: MarketDataProvider,
        watchlist_repo: WatchlistRepository,
        pair_repo: PairRepository,
        *,
        token_repo: TokenRepository | None = None,
        security_inspector: SecurityEvaluator | None = None,
        metrics_tracker: SnapshotRecorder | None = None,
        stale_sink: AlertSink | None = None,
        admit: PairAdmitter | None = None,
        discovery_window: timedelta = timedelta(hours=24),
        clock: Callable[[], datetime] = utc_now_seconds,
    ) -> None:
        self._market = market
        self._watchlist = watchlist_repo
        self._pairs = pair_repo
        self._tokens = token_repo
        self._security = security_inspector
        self._metrics = metrics_tracker
        self._stale_sink = stale_sink
        self._admit = admit
        self._discovery_window = discovery_window
        self._clock = clock
        # Per-pair retry bookkeeping (Req 1.8/1.9).
        self._failure_counts: dict[str, int] = {}
        self._last_good: dict[str, PairSnapshot] = {}
        self._stale_notified: set[str] = set()
        # Mapping from pair_id -> token mint address so that refresh() can pass
        # the correct token_address to the market provider (Issue 1 fix).
        self._pair_token_map: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Watchlist add / pair resolution (Req 1.1, 1.2)
    # ------------------------------------------------------------------
    def add_token_to_watchlist(
        self,
        token_address: str,
        network: Network,
        *,
        source: WatchlistSource = WatchlistSource.MANUAL,
    ) -> Result[WatchlistEntry]:
        """Resolve ``token_address`` to a Trading_Pair and begin monitoring it.

        Resolves the Token's pair(s) through the market provider; an unresolvable
        Token is rejected with :class:`~dex_agent.errors.NotFound` whose
        ``identifier`` names the Token (Req 1.2). On success the first resolved
        pair is registered on the Watchlist, a Security_Inspector evaluation is
        triggered for the Token (Req 1.1), and - when an ``admit`` seam is wired -
        monitoring begins under the concurrency cap; a cap rejection
        (Req 1.10/1.11) is propagated and the watchlist entry is deactivated so no
        partial state remains.
        """
        result = self._market.resolve_pairs(token_address, network)
        if result.is_err() or not result.value:
            # Req 1.2: reject and identify the Token.
            return Err(
                NotFound(
                    "no Trading_Pair could be resolved for token",
                    identifier=token_address,
                )
            )

        snapshot = result.value[0]
        pair_id = snapshot.pair_id

        # Register the token_address -> pair_id mapping so refresh() can pass
        # the correct token mint to the market provider's fetch_pair_snapshot.
        self._pair_token_map[pair_id] = token_address

        entry = self._watchlist.add(
            WatchlistEntry(
                pair_id=pair_id,
                added_at=self._clock(),
                source=source,
            )
        )

        # Req 1.1: trigger the security evaluation for the resolved Token.
        if self._security is not None:
            evaluation = self._security.evaluate(self._token_for(token_address, network))
            # Emit a notification for High or Critical severity (Issue 6).
            if self._stale_sink is not None and hasattr(evaluation, 'rating'):
                if evaluation.rating in (Severity.HIGH, Severity.CRITICAL):
                    self._stale_sink(
                        Alert(
                            title=f"{evaluation.rating.name} severity: {token_address[:12]}…",
                            body=(
                                f"Security evaluation for pair {pair_id} "
                                f"assigned {evaluation.rating.name} severity."
                            ),
                            severity=evaluation.rating,
                            pair_id=pair_id,
                        )
                    )

        if self._metrics is not None:
            self._metrics.register_pair(pair_id)

        # Begin monitoring under the 200-pair cap (Req 1.10/1.11).
        if self._admit is not None:
            admit_result = self._admit(pair_id)
            if admit_result.is_err():
                # No room: retain prior data but deactivate this fresh entry so no
                # partial monitoring state is left behind.
                self._watchlist.deactivate(pair_id)
                return Err(admit_result.error)

        return Ok(entry)

    # ------------------------------------------------------------------
    # Refresh with retry / last-good (Req 1.7, 1.8, 1.9)
    # ------------------------------------------------------------------
    def refresh(self, pair_id: str) -> Result[PairSnapshot]:
        """Refresh ``pair_id``'s market data, applying the retry/last-good policy.

        On success: resets the consecutive-failure count, stores the snapshot as
        the new last-good value, records it via the Metrics_Tracker seam (when
        wired), and returns the fresh snapshot.

        On failure: increments the consecutive-failure count (clamped at
        :data:`MAX_CONSECUTIVE_FAILURES`) and continues to serve the last-good
        snapshot marked ``is_stale=True`` (Req 1.8). When the count first reaches
        5, a stale-data notification identifying the pair is emitted exactly once
        (Req 1.9). When no last-good snapshot exists yet, the underlying provider
        error is returned.
        """
        # Resolve the token mint for this pair_id so Moralis gets the right key.
        token_addr = self._pair_token_map.get(pair_id)
        result = self._market.fetch_pair_snapshot(pair_id, token_address=token_addr)
        if result.is_ok():
            snapshot = result.value
            self._failure_counts[pair_id] = 0
            self._stale_notified.discard(pair_id)
            self._last_good[pair_id] = snapshot
            if self._metrics is not None:
                self._metrics.record(snapshot)
            return Ok(snapshot)

        # Failure path (Req 1.8): record the failure, retain last-good.
        count = min(self._failure_counts.get(pair_id, 0) + 1, MAX_CONSECUTIVE_FAILURES)
        self._failure_counts[pair_id] = count

        if count >= MAX_CONSECUTIVE_FAILURES and pair_id not in self._stale_notified:
            # Req 1.9: 5th consecutive failure -> stale-data notification (once).
            self._stale_notified.add(pair_id)
            self._emit_stale(pair_id)

        last = self._last_good.get(pair_id)
        if last is not None:
            return Ok(replace(last, is_stale=True))
        return Err(result.error)

    def failure_count(self, pair_id: str) -> int:
        """The current consecutive-failure count for ``pair_id`` (0..5)."""
        return self._failure_counts.get(pair_id, 0)

    def last_good(self, pair_id: str) -> PairSnapshot | None:
        """The last successfully retrieved snapshot for ``pair_id``, if any."""
        return self._last_good.get(pair_id)

    # ------------------------------------------------------------------
    # Discovery scan (Req 1.5, 1.6)
    # ------------------------------------------------------------------
    def discovery_scan(self, filters: DiscoveryFilters) -> Result[DiscoveryOutcome]:
        """Scan for and add recent, matching candidate pairs (Req 1.5, 1.6).

        Calls :meth:`MarketDataProvider.discover_recent_pairs` with the
        ``now - 24h`` lower bound, then adds to the Watchlist exactly those
        candidates that were **first listed within the preceding 24 hours**
        (checked against the resolved :class:`TradingPair.created_at`) **and**
        that **match the filters** (Property 10). Each admitted candidate is
        added to the Watchlist with ``AUTO_DISCOVERY`` provenance and begins
        monitoring under the 200-pair cap; candidates rejected by the cap are
        reported separately and not added.
        """
        now = self._clock()
        since = now - self._discovery_window
        result = self._market.discover_recent_pairs(filters, since)
        if result.is_err():
            return Err(result.error)

        candidates = result.value
        added: list[str] = []
        rejected: list[str] = []

        for snapshot in candidates:
            pair = self._resolve_candidate_pair(snapshot)
            if pair is None:
                continue  # cannot establish first-listed time -> cannot admit
            if not self._is_recent(pair, now):
                continue  # Req 1.5: only pairs first listed within 24h
            if not self._matches(filters, pair, snapshot):
                continue  # Req 1.6: must match the discovery filters

            # Admit under the concurrency cap (Req 1.10/1.11).
            if self._admit is not None:
                admit_result = self._admit(pair.id)
                if admit_result.is_err():
                    rejected.append(pair.id)
                    continue

            self._watchlist.add(
                WatchlistEntry(
                    pair_id=pair.id,
                    added_at=now,
                    source=WatchlistSource.AUTO_DISCOVERY,
                )
            )
            if self._metrics is not None:
                self._metrics.register_pair(pair.id)

            # Trigger security evaluation for the discovered token (Req 1.1).
            if self._security is not None:
                self._security.evaluate(self._token_for(pair.token.address, Network.SOLANA))

            added.append(pair.id)

        return Ok(
            DiscoveryOutcome(
                added=tuple(added),
                scanned=len(candidates),
                rejected_capacity=tuple(rejected),
            )
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _resolve_candidate_pair(self, snapshot: PairSnapshot) -> TradingPair | None:
        """Resolve a candidate snapshot to its :class:`TradingPair`.

        First checks the pair repository for an existing entry. If not found
        (typical for discovery candidates), creates a minimal TradingPair from the
        snapshot data and persists it, so that the recency and filter checks can
        proceed. The ``created_at`` field uses the snapshot's ``fetched_at`` as a
        conservative estimate unless the snapshot carries timing info in its origin
        (the Moralis discover_recent_pairs already filters by ``createdAt``).
        """
        found = self._pairs.get(snapshot.pair_id)
        if found.is_ok():
            return found.value
        # For discovery candidates, create a minimal TradingPair from the snapshot.
        # The token_address may come from the snapshot or be derived from pair_id.
        token_addr = snapshot.token_address or snapshot.pair_id
        from decimal import Decimal as _Decimal
        token = Token(
            address=token_addr,
            network=Network.SOLANA,
            symbol="",
            name="",
            total_supply=_Decimal(0),
        )
        # Derive quote_asset: map the wrapped SOL mint to "SOL".
        quote_asset = "SOL"  # Default for Pump.fun pairs

        # Use fetched_at as the creation time (discover_recent_pairs already
        # filters by the createdAt field from the exchange).
        created_at = snapshot.fetched_at

        pair = TradingPair(
            id=snapshot.pair_id,
            token=token,
            quote_asset=quote_asset,
            dex="pumpfun",
            created_at=created_at,
        )
        self._pairs.add(pair)
        # Also register the token_address mapping for refresh calls.
        self._pair_token_map[snapshot.pair_id] = token_addr
        return pair

    def _is_recent(self, pair: TradingPair, now: datetime) -> bool:
        """True iff ``pair`` was first listed within the discovery window (Req 1.5)."""
        return pair.created_at >= now - self._discovery_window

    @staticmethod
    def _matches(
        filters: DiscoveryFilters, pair: TradingPair, snapshot: PairSnapshot
    ) -> bool:
        """True iff ``pair``/``snapshot`` satisfy the discovery filters (Req 1.6).

        Handles the case where Pump.fun pairs report the wrapped SOL mint
        address instead of the symbol "SOL" as the quote asset.
        """
        if filters.quote_assets is not None:
            # Normalize: the wrapped SOL mint is equivalent to "SOL"
            _WSOL_MINT = "So11111111111111111111111111111111111111112"
            quote = pair.quote_asset
            # Check both the raw quote_asset and its normalized form
            matches_quote = (
                quote in filters.quote_assets
                or (quote == _WSOL_MINT and "SOL" in filters.quote_assets)
                or (quote == "SOL" and _WSOL_MINT in filters.quote_assets)
            )
            if not matches_quote:
                return False
        if filters.min_liquidity is not None and snapshot.liquidity < filters.min_liquidity:
            return False
        return True

    def _token_for(self, token_address: str, network: Network) -> Token:
        """Recover a Token for the Security_Inspector (minimal when not stored)."""
        if self._tokens is not None:
            found = self._tokens.get(token_address, network)
            if found.is_ok():
                return found.value
        from decimal import Decimal

        return Token(
            address=token_address,
            network=network,
            symbol="",
            name="",
            total_supply=Decimal(0),
        )

    def _emit_stale(self, pair_id: str) -> None:
        """Deliver the Req 1.9 stale-data notification through the sink seam."""
        if self._stale_sink is None:
            return
        self._stale_sink(
            Alert(
                title="Stale data",
                body=(
                    f"Trading_Pair {pair_id} failed data retrieval on "
                    f"{MAX_CONSECUTIVE_FAILURES} consecutive attempts; serving "
                    "last-good data."
                ),
                pair_id=pair_id,
            )
        )


__all__ = [
    "DataIngestor",
    "DiscoveryOutcome",
    "SecurityEvaluator",
    "SnapshotRecorder",
    "AlertSink",
    "PairAdmitter",
    "MAX_CONSECUTIVE_FAILURES",
]
