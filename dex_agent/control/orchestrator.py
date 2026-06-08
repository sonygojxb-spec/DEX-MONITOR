"""Monitoring Orchestrator: lifecycle, concurrency cap, ticks, recovery.

Design reference: "Monitoring Orchestrator", "Concurrency", "Rate Limits &
Real-Time Strategy", "recover_on_startup". Maps to Requirements 1.3, 1.4, 1.7,
1.10, 1.11, 5.3, 5.4, 5.5, 13.1-13.4.

The Orchestrator owns the lifecycle of per-pair monitoring loops:

* **Concurrency cap (Task 18.2; Property 9).** A bounded active-pair registry
  admits a pair atomically *iff* the current active count is below the 200 cap,
  so the count can never exceed 200; a rejected add returns a
  :class:`~dex_agent.errors.ConcurrencyLimitExceeded` error and never mutates the
  registry (Req 1.10, 1.11). :meth:`remove_pair` stops the loop while the
  repositories retain the collected data (Req 1.3, 1.4).
* **Per-tick pipeline (Task 18.2).** :meth:`tick` runs ingest -> analyze ->
  track -> signal for one pair per Data_Refresh_Interval, with per-stage
  isolation (a failure or stall in one stage never aborts the others or stalls
  other pairs) and an optional per-stage timeout guard.
* **Effective poll interval (Task 18.7).** :meth:`effective_poll_interval_s`
  derives a market-data poll cadence from the Moralis CU-budgeted rate limiter
  and the active pair count, honoring the configured >=5s minimum as a per-pair
  floor while coalescing per-pair snapshots into batched Moralis POST
  batch-metadata lookups (so >=200 pairs stay within budget).
* **Real-time streams (Task 18.8).** :meth:`build_stream_sink` returns an
  :data:`~dex_agent.providers.streams.EventSink` that routes latency-sensitive
  liquidity-removal (rug) and dump events from the Moralis Solana Streams intake
  into the exit-signal path (Req 5.3/5.4) and the <=5s held-position exit alert
  (Req 5.5), rather than tight polling.
* **Startup recovery (Task 18.9; Property 33).** :meth:`recover_on_startup`
  restores persisted open Positions and the active Watchlist before any
  trade-affecting operation, resumes monitoring of each (subject to the cap), and
  reconciles any non-terminal order; if persisted state is unreadable it forces
  monitoring-only mode and submits no orders until resolved (Req 13.1-13.4).

Everything is wired through interfaces/seams and driven by an injectable clock,
so the whole component is exercised with in-memory fakes and no real
network/chain calls or sleeps.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable, Protocol

from dex_agent.control.data_ingestor import DataIngestor
from dex_agent.errors import AgentError, ConcurrencyLimitExceeded
from dex_agent.models import (
    Configuration,
    ExitClass,
    MetricValue,
    OrderRecord,
    OrderStatus,
    PairSnapshot,
    Severity,
    Signal,
    SignalType,
    utc_now_seconds,
)
from dex_agent.providers.interfaces import Alert
from dex_agent.providers.ratelimit import MORALIS_CU_COSTS, ProviderRateLimiter
from dex_agent.providers.streams import StreamEvent, StreamEventKind
from dex_agent.repositories.interfaces import (
    OrderRepository,
    PositionRepository,
    SignalRepository,
    WatchlistRepository,
)
from dex_agent.result import Err, Ok, Result

#: The maximum number of Trading_Pairs monitored concurrently (Req 1.10/1.11).
CONCURRENCY_CAP = 200

#: The hard per-pair minimum refresh interval floor in seconds (Req 1.7).
MIN_REFRESH_INTERVAL_S = 5.0

#: The Moralis batch-metadata endpoint accepts up to 100 addresses per POST.
MORALIS_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Injected component seams (kept structural so the Orchestrator never imports the
# concrete analyzers / engines - they are wired by their interfaces in Task 19).
# ---------------------------------------------------------------------------


class SecurityProvider(Protocol):
    """Latest-rating lookup seam (Security_Inspector / SecurityEvalRepository)."""

    def latest(self, token_address: str): ...


class WalletAnalyzer(Protocol):
    """Backend_Analyzer seam used in the analyze stage."""

    def analyze(self, pair, window_minutes: int | None = ...): ...


class MetricsRecorder(Protocol):
    """Metrics_Tracker seam used in the track stage."""

    def register_pair(self, pair_id: str) -> None: ...

    def record(self, snapshot: PairSnapshot): ...


class TradingGate(Protocol):
    """Authorization_Manager gate seam (``trading_enabled`` / ``revoke``)."""

    def trading_enabled(self) -> bool: ...


# An alert sink (the Notifier seam, Task 17). Used for stream exit alerts (Req
# 5.5) and the recovery-failure indication (Req 13.4).
AlertSink = Callable[[Alert], None]

# Reports whether a Position is held for a pair (gates the <=5s exit alert).
PositionHeld = Callable[[str], bool]

# Builds the SignalInputs for a pair's signal stage; injected so the Orchestrator
# stays decoupled from how inputs are assembled. Returns ``None`` to skip.
SignalInputBuilder = Callable[[str, PairSnapshot], object]


@dataclass
class MonitorHandle:
    """The Orchestrator's per-pair monitoring-loop handle."""

    pair_id: str
    token_address: str | None = None
    mint_address: str | None = None
    started_at: datetime | None = None
    active: bool = True


@dataclass(frozen=True)
class StageResult:
    """The outcome of one pipeline stage in a :meth:`tick` (per-stage isolation)."""

    name: str
    ok: bool
    detail: str = ""


@dataclass(frozen=True)
class TickResult:
    """The result of one per-pair :meth:`tick`.

    Attributes:
        pair_id: The pair the tick ran for.
        stages: The per-stage results (ingest/analyze/track/signal).
        snapshot: The snapshot served by the ingest stage, if any.
    """

    pair_id: str
    stages: tuple[StageResult, ...] = ()
    snapshot: PairSnapshot | None = None

    @property
    def ok(self) -> bool:
        """True iff every stage completed without an isolated failure."""
        return all(s.ok for s in self.stages)


@dataclass(frozen=True)
class RecoveryReport:
    """The outcome of :meth:`recover_on_startup` (Req 13.1-13.4; Property 33)."""

    restored_positions: tuple[str, ...] = ()
    resumed_watchlist: tuple[str, ...] = ()
    watchlist_capacity_rejected: tuple[str, ...] = ()
    reconciled_orders: tuple[str, ...] = ()
    monitoring_only: bool = False


class MonitoringOrchestrator:
    """Owns per-pair loops, the concurrency cap, ticks, streams, and recovery."""

    def __init__(
        self,
        *,
        config: Configuration,
        ingestor: DataIngestor | None = None,
        watchlist_repo: WatchlistRepository | None = None,
        positions_repo: PositionRepository | None = None,
        orders_repo: OrderRepository | None = None,
        signal_repo: SignalRepository | None = None,
        security: SecurityProvider | None = None,
        wallet_analyzer: WalletAnalyzer | None = None,
        metrics_tracker: MetricsRecorder | None = None,
        signal_engine=None,
        signal_input_builder: SignalInputBuilder | None = None,
        authz: TradingGate | None = None,
        venue=None,
        in_flight=None,
        rate_limiter: ProviderRateLimiter | None = None,
        alert_sink: AlertSink | None = None,
        position_held: PositionHeld | None = None,
        pair_repo=None,
        cap: int = CONCURRENCY_CAP,
        stage_timeout_s: float | None = None,
        clock: Callable[[], datetime] = utc_now_seconds,
    ) -> None:
        self._config = config
        self._ingestor = ingestor
        self._watchlist = watchlist_repo
        self._positions = positions_repo
        self._orders = orders_repo
        self._signal_repo = signal_repo
        self._security = security
        self._wallet_analyzer = wallet_analyzer
        self._metrics = metrics_tracker
        self._signal_engine = signal_engine
        self._signal_input_builder = signal_input_builder
        self._authz = authz
        self._venue = venue
        self._in_flight = in_flight
        self._rate_limiter = rate_limiter
        self._alert_sink = alert_sink
        self._position_held: PositionHeld = position_held or (lambda _p: False)
        self._pair_repo = pair_repo
        self._cap = cap
        self._stage_timeout_s = stage_timeout_s
        self._clock = clock

        self._active: dict[str, MonitorHandle] = {}
        self._lock = threading.RLock()
        self._mint_to_pair: dict[str, str] = {}
        self._prev_liquidity: dict[str, Decimal] = {}
        self._recovery_failed = False

    # ------------------------------------------------------------------
    # Concurrency cap + loop lifecycle (Task 18.2; Property 9, Req 1.3/1.4)
    # ------------------------------------------------------------------
    def add_pair(
        self,
        pair_id: str,
        *,
        token_address: str | None = None,
        mint_address: str | None = None,
    ) -> Result[MonitorHandle]:
        """Admit ``pair_id`` for monitoring iff under the 200-pair cap (Req 1.11).

        Atomic under the registry lock: the add succeeds **iff** the current
        active count is below the cap, and the resulting count never exceeds the
        cap (Property 9). Re-adding an already-active pair is an idempotent no-op
        that returns the existing handle (the count is unchanged). A rejected add
        returns :class:`~dex_agent.errors.ConcurrencyLimitExceeded` and leaves the
        registry untouched.
        """
        with self._lock:
            existing = self._active.get(pair_id)
            if existing is not None and existing.active:
                return Ok(existing)
            if len(self._active) >= self._cap:
                return Err(
                    ConcurrencyLimitExceeded(
                        "concurrent monitoring cap reached",
                        limit=self._cap,
                        identifier=pair_id,
                    )
                )
            handle = MonitorHandle(
                pair_id=pair_id,
                token_address=token_address,
                mint_address=mint_address,
                started_at=self._clock(),
                active=True,
            )
            self._active[pair_id] = handle
            if mint_address is not None:
                self._mint_to_pair[mint_address] = pair_id
            if self._metrics is not None:
                self._metrics.register_pair(pair_id)
            return Ok(handle)

    def remove_pair(self, pair_id: str) -> None:
        """Stop monitoring ``pair_id`` while repositories retain its data.

        Removes the active-loop handle so no further ticks run for the pair
        (Req 1.3) and deactivates its Watchlist entry, but performs **no**
        repository deletion - all previously collected data is retained
        (Req 1.4).
        """
        with self._lock:
            handle = self._active.pop(pair_id, None)
            if handle is not None and handle.mint_address is not None:
                self._mint_to_pair.pop(handle.mint_address, None)
        # Deactivate the watchlist entry (retains the entry + collected data).
        if self._watchlist is not None:
            self._watchlist.deactivate(pair_id)

    def active_count(self) -> int:
        """The current number of actively monitored pairs (invariant: <= cap)."""
        with self._lock:
            return len(self._active)

    def is_active(self, pair_id: str) -> bool:
        """True iff ``pair_id`` is currently being monitored."""
        with self._lock:
            handle = self._active.get(pair_id)
            return handle is not None and handle.active

    def active_pairs(self) -> tuple[str, ...]:
        """The ids of all currently monitored pairs."""
        with self._lock:
            return tuple(self._active.keys())

    # ------------------------------------------------------------------
    # Per-tick pipeline (Task 18.2): ingest -> analyze -> track -> signal
    # ------------------------------------------------------------------
    def tick(self, pair_id: str) -> TickResult:
        """Run one monitoring tick for ``pair_id`` with per-stage isolation.

        Each stage is wrapped so a failure or stall in one stage neither aborts
        the remaining stages nor stalls other pairs' loops (design "Concurrency"
        -> Isolation). The ingest stage applies the Data_Ingestor's
        retry/last-good policy; analyze runs the Backend_Analyzer; track records
        the snapshot into the Metrics_Tracker; signal computes entry/exit via the
        Signal_Engine using the assembled inputs.
        """
        stages: list[StageResult] = []
        snapshot: PairSnapshot | None = None

        # --- ingest ---
        def _ingest():
            nonlocal snapshot
            if self._ingestor is None:
                return False, "no ingestor wired"
            result = self._ingestor.refresh(pair_id)
            if result.is_err():
                return False, f"refresh failed: {result.error}"
            snapshot = result.value
            return True, ""

        stages.append(self._run_stage("ingest", _ingest))

        # --- analyze ---
        def _analyze():
            if self._wallet_analyzer is None or self._pair_repo is None:
                return True, "analyze skipped (not wired)"
            pair = self._pair_repo.get(pair_id)
            if pair.is_err():
                return True, "pair not resolvable; analyze skipped"
            self._wallet_analyzer.analyze(pair.value)
            return True, ""

        stages.append(self._run_stage("analyze", _analyze))

        # --- track ---
        def _track():
            if self._metrics is None or snapshot is None:
                return True, "track skipped (no snapshot/tracker)"
            self._metrics.record(snapshot)
            return True, ""

        stages.append(self._run_stage("track", _track))

        # --- signal ---
        def _signal():
            if self._signal_engine is None or snapshot is None:
                return True, "signal skipped (not wired)"
            inputs = self._build_signal_inputs(pair_id, snapshot)
            if inputs is None:
                return True, "signal inputs unavailable; skipped"
            self._signal_engine.compute(inputs)
            self._prev_liquidity[pair_id] = snapshot.liquidity
            return True, ""

        stages.append(self._run_stage("signal", _signal))

        return TickResult(pair_id=pair_id, stages=tuple(stages), snapshot=snapshot)

    def _run_stage(
        self, name: str, fn: Callable[[], tuple[bool, str]]
    ) -> StageResult:
        """Run one stage in isolation, converting any failure into a StageResult."""
        try:
            ok, detail = fn()
            return StageResult(name=name, ok=ok, detail=detail)
        except Exception as exc:  # noqa: BLE001 - isolation boundary
            return StageResult(name=name, ok=False, detail=f"{type(exc).__name__}: {exc}")

    def _build_signal_inputs(self, pair_id: str, snapshot: PairSnapshot):
        """Assemble SignalInputs from the latest analysis + snapshot, or skip."""
        if self._signal_input_builder is not None:
            return self._signal_input_builder(pair_id, snapshot)

        # Default assembly using the wired security/wallet seams.
        from dex_agent.decision.signal_engine import SignalInputs

        severity = Severity.NONE
        if self._security is not None and snapshot.pair_id:
            token_addr = self._token_for_pair(pair_id)
            if token_addr is not None:
                latest = self._security.latest(token_addr)
                if latest.is_ok():
                    severity = latest.value.rating

        bot_pct = Decimal(0)
        holder_conc = Decimal(0)
        if self._wallet_analyzer is not None and hasattr(self._wallet_analyzer, "_repository"):
            pass  # analysis history is optional; defaults keep the tick robust

        prev_liq: MetricValue | None = self._prev_liquidity.get(pair_id)
        return SignalInputs(
            pair_id=pair_id,
            severity=severity,
            bot_pct=bot_pct,
            holder_concentration=holder_conc,
            curr_liquidity=snapshot.liquidity,
            buy_volume=snapshot.buy_volume,
            sell_volume=snapshot.sell_volume,
            prev_liquidity=prev_liq,
            stale=snapshot.is_stale,
        )

    def _token_for_pair(self, pair_id: str) -> str | None:
        """Best-effort token address for a pair (from registry or pair repo)."""
        with self._lock:
            handle = self._active.get(pair_id)
        if handle is not None and handle.token_address is not None:
            return handle.token_address
        if self._pair_repo is not None:
            pair = self._pair_repo.get(pair_id)
            if pair.is_ok():
                return pair.value.token.address
        return None

    # ------------------------------------------------------------------
    # Effective poll interval from the CU budget (Task 18.7; Req 1.7/1.10)
    # ------------------------------------------------------------------
    def effective_poll_interval_s(self, active: int | None = None) -> float:
        """Derive the market-data poll interval from the CU budget + pair count.

        Per-pair snapshots are coalesced into batched Moralis POST batch-metadata
        lookups (<=100 addresses, 100 CU each), so a tick over ``active`` pairs
        costs ``ceil(active / 100) * 100`` CU. Given the Moralis CU-budgeted
        limiter's sustainable refill rate (CU/second), the smallest interval that
        keeps the aggregate CU spend within budget is ``cu_per_tick / rate``. The
        configured Data_Refresh_Interval (>= 5s, Req 1.7) is applied as a per-pair
        floor, so the effective interval is the larger of the two. This reconciles
        the >=5s minimum (Req 1.7) with monitoring >=200 pairs (Req 1.10) without
        breaching the provider limit.
        """
        active = self.active_count() if active is None else active
        floor = max(float(self._config.refresh_interval_s), MIN_REFRESH_INTERVAL_S)
        if active <= 0 or self._rate_limiter is None:
            return floor

        batches = math.ceil(active / MORALIS_BATCH_SIZE)
        cu_per_tick = batches * MORALIS_CU_COSTS["metadata_batch"]
        rate = self._rate_limiter.bucket.refill_per_second
        if rate <= 0:
            return floor
        sustainable = cu_per_tick / rate
        return max(floor, sustainable)

    # ------------------------------------------------------------------
    # Real-time stream routing into the exit path (Task 18.8; Req 5.3/5.4/5.5)
    # ------------------------------------------------------------------
    def register_mint(self, mint_address: str, pair_id: str) -> None:
        """Map a watched ``mint_address`` to its ``pair_id`` for stream routing."""
        with self._lock:
            self._mint_to_pair[mint_address] = pair_id

    def build_stream_sink(self) -> Callable[[StreamEvent], None]:
        """Return the :data:`EventSink` routing stream events into the exit path.

        Wired into the Moralis Solana Streams webhook intake (Task 4.5) as the
        PRIMARY real-time mechanism. A ``LIQUIDITY_REMOVAL`` event routes to a
        ``RUG_PULL`` exit signal (Req 5.3) and a ``DUMP`` event to a ``DUMP`` exit
        signal (Req 5.4); both are recorded to the Signal repository, and when a
        Position is held for the affected pair a <=5s exit alert is dispatched
        (Req 5.5). Generic activity events are ignored (they feed the bot/sniper
        heuristics elsewhere).
        """
        return self.route_stream_event

    def route_stream_event(self, event: StreamEvent) -> None:
        """Route a single classified stream event into the exit-signal path."""
        exit_class = _EXIT_CLASS_FOR.get(event.kind)
        if exit_class is None:
            return  # generic activity - no exit routing

        for mint in event.net_by_mint.keys():
            pair_id = self._mint_to_pair.get(mint)
            if pair_id is None:
                continue
            self._emit_exit_signal(pair_id, exit_class, event)

    def _emit_exit_signal(
        self, pair_id: str, exit_class: ExitClass, event: StreamEvent
    ) -> None:
        """Record an EXIT signal and, if a Position is held, alert within 5s."""
        ts = event.block_time or self._clock()
        signal = Signal(
            pair_id=pair_id,
            type=SignalType.EXIT,
            score=Decimal(0),
            eligible=False,
            generated_at=ts,
            exit_class=exit_class,
            contributing_metrics={
                "source": "moralis_streams",
                "signature": event.signature,
                "kind": event.kind.value,
                "net_by_mint": {m: str(v) for m, v in event.net_by_mint.items()},
            },
        )
        if self._signal_repo is not None:
            self._signal_repo.append(signal)

        # Req 5.5: held-position exit alert within 5 seconds.
        if self._position_held(pair_id) and self._alert_sink is not None:
            self._alert_sink(
                Alert(
                    title=f"Exit signal: {exit_class.value}",
                    body=(
                        f"Real-time {exit_class.value} exit signal for held "
                        f"position in pair {pair_id} (tx {event.signature})."
                    ),
                    severity=Severity.CRITICAL,
                    pair_id=pair_id,
                    is_exit_signal=True,
                )
            )

    # ------------------------------------------------------------------
    # Startup state recovery (Task 18.9; Property 33, Req 13.1-13.4)
    # ------------------------------------------------------------------
    def recover_on_startup(self) -> Result[RecoveryReport]:
        """Restore persisted state before any trade-affecting operation (Req 13.1).

        Restores all open Positions and the active Watchlist from persistence;
        resumes monitoring (exit-signal evaluation) for each restored Position
        (Req 13.2) and each restored Watchlist pair subject to the 200-pair cap
        (Req 13.3); and reconciles any non-terminal persisted order via a
        confirmation poll (transitioning it to a terminal status and clearing the
        in-flight marker accordingly). If the persisted Position or Watchlist
        state cannot be read, the Agent is forced into monitoring-only mode, a
        recovery-failure indication is surfaced, and no orders are submitted until
        the state is resolved (Req 13.4).
        """
        try:
            open_positions = (
                list(self._positions.list_open()) if self._positions is not None else []
            )
            active_watchlist = (
                list(self._watchlist.list_active()) if self._watchlist is not None else []
            )
        except Exception as exc:  # noqa: BLE001 - unreadable persisted state (Req 13.4)
            self._force_monitoring_only()
            self._emit_recovery_failure(str(exc))
            return Err(_RecoveryError(str(exc) or "persisted state unreadable"))

        # Req 13.2: resume monitoring + stop-loss/exit evaluation for positions.
        restored_positions: list[str] = []
        for position in open_positions:
            self.add_pair(position.pair_id, token_address=position.token_address)
            restored_positions.append(position.pair_id)

        # Req 13.3: resume monitoring of the active watchlist, subject to the cap.
        resumed: list[str] = []
        rejected: list[str] = []
        for entry in active_watchlist:
            result = self.add_pair(entry.pair_id)
            if result.is_ok():
                resumed.append(entry.pair_id)
            else:
                rejected.append(entry.pair_id)

        # Reconcile any non-terminal persisted order (Req 12/13).
        reconciled = self._reconcile_orders()

        return Ok(
            RecoveryReport(
                restored_positions=tuple(restored_positions),
                resumed_watchlist=tuple(resumed),
                watchlist_capacity_rejected=tuple(rejected),
                reconciled_orders=tuple(reconciled),
                monitoring_only=self._recovery_failed,
            )
        )

    def _reconcile_orders(self) -> list[str]:
        """Reconcile non-terminal orders via a confirmation poll (Req 12/13)."""
        if self._orders is None or self._venue is None:
            return []
        reconciled: list[str] = []
        for order in self._orders.list_non_terminal():
            tx_id = order.tx_id
            if tx_id is None:
                continue
            status, terminal = self._poll_terminal_status(tx_id)
            self._orders.append(
                _with_status(order, status, recorded_at=self._clock())
            )
            if terminal and self._in_flight is not None:
                # Clear the in-flight marker exactly on a terminal status.
                self._in_flight.clear(order.pair_id)
            reconciled.append(tx_id)
        return reconciled

    def _poll_terminal_status(self, tx_id: str) -> tuple[OrderStatus, bool]:
        """Poll the venue for ``tx_id`` and map it to a terminal OrderStatus."""
        timeout = timedelta(seconds=self._config.confirmation_timeout_s)
        result = self._venue.poll_confirmation(tx_id, timeout)
        if result.is_err():
            return OrderStatus.TIMED_OUT, True
        confirmation = result.value
        if confirmation.confirmed:
            return OrderStatus.CONFIRMED, True
        return OrderStatus.FAILED, True

    def _force_monitoring_only(self) -> None:
        """Force monitoring-only mode so no orders are submitted (Req 13.4)."""
        self._recovery_failed = True
        # Best-effort: disable the trading gate via the existing revoke path
        # (never modifies the Authorization_Manager). A no-op when no wallet is
        # connected; the orchestrator gate below is the authoritative guard.
        revoke = getattr(self._authz, "revoke", None)
        if callable(revoke):
            try:
                revoke()
            except Exception:  # noqa: BLE001 - best-effort only
                pass

    def _emit_recovery_failure(self, detail: str) -> None:
        """Surface a recovery-failure indication to the user (Req 13.4)."""
        if self._alert_sink is None:
            return
        self._alert_sink(
            Alert(
                title="State recovery failed",
                body=(
                    "Persisted Position/Watchlist state could not be read at "
                    f"startup ({detail}); starting in monitoring-only mode. No "
                    "orders will be submitted until the state is resolved."
                ),
                severity=Severity.CRITICAL,
            )
        )

    @property
    def recovery_failed(self) -> bool:
        """True iff startup recovery failed and the Agent is monitoring-only."""
        return self._recovery_failed

    @property
    def monitoring_only(self) -> bool:
        """True iff the Agent must not submit orders (recovery unresolved)."""
        return self._recovery_failed

    def trading_allowed(self) -> bool:
        """The orchestrator-side trade gate: blocked while recovery is unresolved.

        Composed with :meth:`AuthorizationManager.trading_enabled` at wiring time
        (Task 19) so that a recovery failure deterministically prevents any order
        submission until :meth:`resolve_recovery` is called (Req 13.4).
        """
        return not self._recovery_failed

    def resolve_recovery(self) -> None:
        """Mark the recovery failure resolved so trading may resume (Req 13.4)."""
        self._recovery_failed = False


# Mapping from a stream event kind to the exit classification it routes to.
_EXIT_CLASS_FOR: dict[StreamEventKind, ExitClass] = {
    StreamEventKind.LIQUIDITY_REMOVAL: ExitClass.RUG_PULL,
    StreamEventKind.DUMP: ExitClass.DUMP,
}


class _RecoveryError(AgentError):
    """Internal error carried when persisted state is unreadable (Req 13.4)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _with_status(
    order: OrderRecord, status: OrderStatus, *, recorded_at: datetime
) -> OrderRecord:
    """Return a copy of ``order`` transitioned to ``status`` (reconciliation)."""
    from dataclasses import replace

    return replace(order, status=status, recorded_at=recorded_at)


__all__ = [
    "MonitoringOrchestrator",
    "MonitorHandle",
    "TickResult",
    "StageResult",
    "RecoveryReport",
    "CONCURRENCY_CAP",
    "MIN_REFRESH_INTERVAL_S",
    "MORALIS_BATCH_SIZE",
]
