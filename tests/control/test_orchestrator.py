"""Tests for the Monitoring Orchestrator (Tasks 18.2, 18.3, 18.7-18.10).

Covers:

* **Property 9** - the concurrency cap is never exceeded (Req 1.10, 1.11).
* **Property 33** - startup state recovery (Req 13.1-13.4).
* Unit tests - the per-tick pipeline isolation (Req 1.3), the effective
  poll-interval derivation (Task 18.7; Req 1.7, 1.10), the Moralis Streams exit
  routing (Task 18.8; Req 5.3/5.4/5.5), and non-terminal order reconciliation
  on recovery (Req 12/13).

Everything runs against in-memory fakes and a controllable clock; there are no
real network/chain calls or sleeps.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.control import MonitoringOrchestrator
from dex_agent.control.orchestrator import CONCURRENCY_CAP, MIN_REFRESH_INTERVAL_S
from dex_agent.errors import ConcurrencyLimitExceeded
from dex_agent.models import (
    Configuration,
    OrderKind,
    OrderRecord,
    OrderStatus,
    PairSnapshot,
    Position,
    PositionStatus,
    WatchlistEntry,
    WatchlistSource,
)
from dex_agent.providers.fakes import FakeTradeVenueProvider
from dex_agent.providers.interfaces import Alert, Confirmation
from dex_agent.providers.ratelimit import ProviderRateLimiter
from dex_agent.providers.streams import (
    MoralisWebhookIntake,
    StreamEvent,
    StreamEventKind,
)
from dex_agent.repositories import (
    InMemoryOrderRepository,
    InMemoryPositionRepository,
    InMemorySignalRepository,
    InMemoryWatchlistRepository,
)
from dex_agent.models import InFlightRegistry
from dex_agent.result import Err, Ok

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def fixed_clock(now: datetime = NOW):
    return lambda: now


def make_config(refresh_interval_s: int = 30) -> Configuration:
    return Configuration(
        discovery_scan_interval_s=60,
        measurement_period_s=300,
        bot_pct_threshold=Decimal(50),
        holder_conc_threshold=Decimal(50),
        rugpull_threshold=Decimal(50),
        dump_threshold=Decimal(2),
        entry_threshold=Decimal(50),
        slippage_tolerance=Decimal(1),
        refresh_interval_s=refresh_interval_s,
    )


def make_orchestrator(**kwargs) -> MonitoringOrchestrator:
    kwargs.setdefault("config", make_config())
    kwargs.setdefault("clock", fixed_clock())
    return MonitoringOrchestrator(**kwargs)


# ---------------------------------------------------------------------------
# Property 9: Concurrency cap is never exceeded
# ---------------------------------------------------------------------------

_op = st.tuples(
    st.sampled_from(["add", "remove"]),
    st.integers(min_value=0, max_value=249),
)


@settings(max_examples=100)
@given(ops=st.lists(_op, max_size=600))
def test_property_9_concurrency_cap_never_exceeded(ops):
    # Feature: dex-trading-agent, Property 9: Concurrency cap is never exceeded
    # Validates: Requirements 1.10, 1.11
    orch = make_orchestrator(watchlist_repo=InMemoryWatchlistRepository())
    model: set[str] = set()

    for kind, idx in ops:
        pair_id = f"pair-{idx}"
        if kind == "add":
            pre_count = len(model)
            already = pair_id in model
            result = orch.add_pair(pair_id)
            if already:
                # Idempotent re-add: always Ok, count unchanged.
                assert isinstance(result, Ok)
            elif pre_count < CONCURRENCY_CAP:
                # An add succeeds iff the current count is below the cap.
                assert isinstance(result, Ok)
                model.add(pair_id)
            else:
                assert isinstance(result, Err)
                assert isinstance(result.error, ConcurrencyLimitExceeded)
        else:  # remove
            orch.remove_pair(pair_id)
            model.discard(pair_id)

        # The resulting count never exceeds the cap and mirrors the model.
        assert orch.active_count() == len(model)
        assert orch.active_count() <= CONCURRENCY_CAP


def test_add_succeeds_exactly_up_to_cap_then_rejects():
    orch = make_orchestrator(cap=5)
    for i in range(5):
        assert isinstance(orch.add_pair(f"p-{i}"), Ok)
    assert orch.active_count() == 5
    # The 6th distinct add is rejected with the concurrency-limit error.
    rejected = orch.add_pair("p-overflow")
    assert isinstance(rejected, Err)
    assert isinstance(rejected.error, ConcurrencyLimitExceeded)
    assert orch.active_count() == 5
    # Removing one frees a slot.
    orch.remove_pair("p-0")
    assert isinstance(orch.add_pair("p-overflow"), Ok)
    assert orch.active_count() == 5


# ---------------------------------------------------------------------------
# Property 33: Startup state recovery
# ---------------------------------------------------------------------------


class FailingPositionRepository(InMemoryPositionRepository):
    """A position repository whose reads fail (unreadable persisted state)."""

    def list_open(self):  # type: ignore[override]
        raise RuntimeError("persisted positions corrupted")


@settings(max_examples=100)
@given(
    position_ids=st.lists(
        st.integers(min_value=0, max_value=60), unique=True, max_size=20
    ),
    watchlist_ids=st.lists(
        st.integers(min_value=0, max_value=60), unique=True, max_size=40
    ),
    readable=st.booleans(),
)
def test_property_33_startup_state_recovery(position_ids, watchlist_ids, readable):
    # Feature: dex-trading-agent, Property 33: Startup state recovery
    # Validates: Requirements 13.1, 13.2, 13.3, 13.4
    watchlist = InMemoryWatchlistRepository()
    alerts: list[Alert] = []

    if readable:
        positions_repo = InMemoryPositionRepository()
        for i in position_ids:
            positions_repo.upsert(
                Position(
                    pair_id=f"pair-{i}",
                    token_address=f"tok-{i}",
                    quantity=Decimal(10),
                    avg_entry_price=Decimal(2),
                    notional_cost=Decimal(20),
                    opened_at=NOW,
                    status=PositionStatus.OPEN,
                )
            )
        for i in watchlist_ids:
            watchlist.add(
                WatchlistEntry(
                    pair_id=f"pair-{i}",
                    added_at=NOW,
                    source=WatchlistSource.MANUAL,
                )
            )
    else:
        positions_repo = FailingPositionRepository()

    orch = make_orchestrator(
        positions_repo=positions_repo,
        watchlist_repo=watchlist,
        alert_sink=alerts.append,
    )

    result = orch.recover_on_startup()

    if not readable:
        # Req 13.4: unreadable state -> monitoring-only, surfaced, no orders.
        assert isinstance(result, Err)
        assert orch.monitoring_only is True
        assert orch.trading_allowed() is False
        assert orch.active_count() == 0
        assert any(a.title == "State recovery failed" for a in alerts)
        return

    assert isinstance(result, Ok)
    report = result.value

    # Build the expected active set: positions admitted first, then watchlist,
    # each subject to the 200-pair cap (Req 13.2, 13.3).
    P = [f"pair-{i}" for i in position_ids]
    W = [f"pair-{i}" for i in watchlist_ids]
    active: set[str] = set()
    for p in P:
        if p not in active and len(active) < CONCURRENCY_CAP:
            active.add(p)
    resumed: list[str] = []
    rejected: list[str] = []
    for w in W:
        if w in active:
            resumed.append(w)
        elif len(active) < CONCURRENCY_CAP:
            active.add(w)
            resumed.append(w)
        else:
            rejected.append(w)

    # Req 13.1/13.2: restored exactly the open positions (monitoring resumed).
    assert set(report.restored_positions) == set(P)
    for p in P:
        assert orch.is_active(p) is True  # stop-loss + exit eval resumed
    # Req 13.3: resumed monitoring of exactly the active watchlist (cap-bound).
    assert report.resumed_watchlist == tuple(resumed)
    assert report.watchlist_capacity_rejected == tuple(rejected)
    assert set(orch.active_pairs()) == active
    assert orch.active_count() <= CONCURRENCY_CAP
    # Readable recovery keeps trading permitted (no recovery failure).
    assert orch.monitoring_only is False
    assert orch.trading_allowed() is True


def test_recovery_respects_cap_for_large_watchlist():
    # Req 13.3: more than 200 active watchlist pairs are admitted only up to 200.
    watchlist = InMemoryWatchlistRepository()
    for i in range(250):
        watchlist.add(
            WatchlistEntry(
                pair_id=f"pair-{i}", added_at=NOW, source=WatchlistSource.MANUAL
            )
        )
    orch = make_orchestrator(
        positions_repo=InMemoryPositionRepository(), watchlist_repo=watchlist
    )
    result = orch.recover_on_startup()
    assert isinstance(result, Ok)
    report = result.value
    assert orch.active_count() == CONCURRENCY_CAP
    assert len(report.resumed_watchlist) == CONCURRENCY_CAP
    assert len(report.watchlist_capacity_rejected) == 50


def test_recovery_reconciles_non_terminal_order():
    # Req 12/13: a non-terminal persisted order is polled to a terminal status
    # and its in-flight marker cleared.
    orders = InMemoryOrderRepository()
    in_flight = InFlightRegistry()
    submitted = OrderRecord(
        pair_id="pair-1",
        kind=OrderKind.BUY,
        requested_qty=Decimal(5),
        notional=Decimal(5),
        max_slippage=Decimal(1),
        status=OrderStatus.SUBMITTED,
        recorded_at=NOW,
        tx_id="tx-1",
    )
    orders.append(submitted)
    in_flight.mark("pair-1", submitted)

    venue = FakeTradeVenueProvider(now=NOW)
    venue.set_confirmation(
        "tx-1",
        Confirmation(
            tx_id="tx-1",
            confirmed=True,
            executed_price=Decimal(2),
            executed_qty=Decimal(5),
            fee=Decimal("0.1"),
            executed_slippage=Decimal("0.2"),
            confirmed_at=NOW,
        ),
    )

    orch = make_orchestrator(
        positions_repo=InMemoryPositionRepository(),
        watchlist_repo=InMemoryWatchlistRepository(),
        orders_repo=orders,
        venue=venue,
        in_flight=in_flight,
    )
    result = orch.recover_on_startup()
    assert isinstance(result, Ok)
    assert result.value.reconciled_orders == ("tx-1",)
    # The in-flight marker is cleared on the terminal status (Req 12.4).
    assert in_flight.has_in_flight("pair-1") is False
    # The venue confirmation was polled during reconciliation.
    assert ("poll_confirmation", ("tx-1", timedelta(seconds=60))) in venue.calls


# ---------------------------------------------------------------------------
# Task 18.7: effective poll interval from the CU budget
# ---------------------------------------------------------------------------


def test_poll_interval_floor_without_rate_limiter():
    orch = make_orchestrator(config=make_config(refresh_interval_s=30))
    # No rate limiter -> the configured refresh interval is the floor.
    assert orch.effective_poll_interval_s(active=200) == 30.0


def test_poll_interval_honors_5s_minimum_floor():
    orch = make_orchestrator(config=make_config(refresh_interval_s=5))
    # Generous budget: sustainable interval is tiny, so the 5s floor wins.
    limiter = ProviderRateLimiter.moralis(cu_per_window=100_000, window_seconds=1.0)
    orch._rate_limiter = limiter  # type: ignore[attr-defined]
    assert orch.effective_poll_interval_s(active=200) == MIN_REFRESH_INTERVAL_S


def test_poll_interval_scales_with_budget_and_pairs():
    orch = make_orchestrator(config=make_config(refresh_interval_s=5))
    # Tight budget: 10 CU/sec. 200 pairs -> ceil(200/100)=2 batches -> 200 CU/tick
    # -> sustainable = 200 / 10 = 20s, which exceeds the 5s floor.
    limiter = ProviderRateLimiter.moralis(cu_per_window=10, window_seconds=1.0)
    orch._rate_limiter = limiter  # type: ignore[attr-defined]
    assert orch.effective_poll_interval_s(active=200) == 20.0
    # Zero active pairs -> just the floor.
    assert orch.effective_poll_interval_s(active=0) == 5.0


# ---------------------------------------------------------------------------
# Task 18.8: Moralis Streams exit routing
# ---------------------------------------------------------------------------


def test_stream_event_routes_rug_pull_to_exit_signal_and_alert():
    signal_repo = InMemorySignalRepository()
    alerts: list[Alert] = []
    held = {"pair-1"}
    orch = make_orchestrator(
        signal_repo=signal_repo,
        alert_sink=alerts.append,
        position_held=lambda pid: pid in held,
    )
    orch.register_mint("mint-1", "pair-1")

    event = StreamEvent(
        signature="sig-1",
        kind=StreamEventKind.LIQUIDITY_REMOVAL,
        deltas=(),
        net_by_mint={"mint-1": Decimal(-1000)},
        block_time=NOW,
    )
    orch.route_stream_event(event)

    signals = signal_repo.history("pair-1")
    assert len(signals) == 1
    assert signals[0].exit_class.value == "RUG_PULL"
    # Held position -> a <=5s exit alert was dispatched (Req 5.5).
    assert len(alerts) == 1
    assert alerts[0].is_exit_signal is True
    assert alerts[0].severity.name == "CRITICAL"


def test_stream_dump_event_without_held_position_records_no_alert():
    signal_repo = InMemorySignalRepository()
    alerts: list[Alert] = []
    orch = make_orchestrator(
        signal_repo=signal_repo,
        alert_sink=alerts.append,
        position_held=lambda pid: False,
    )
    orch.register_mint("mint-2", "pair-2")
    event = StreamEvent(
        signature="sig-2",
        kind=StreamEventKind.DUMP,
        deltas=(),
        net_by_mint={"mint-2": Decimal(-50)},
        block_time=NOW,
    )
    orch.route_stream_event(event)

    signals = signal_repo.history("pair-2")
    assert len(signals) == 1
    assert signals[0].exit_class.value == "DUMP"
    assert alerts == []  # no position held -> no exit alert


def test_webhook_intake_routes_into_exit_path_with_fakes():
    # End-to-end through the Moralis webhook intake using in-memory fakes.
    signal_repo = InMemorySignalRepository()
    alerts: list[Alert] = []
    orch = make_orchestrator(
        signal_repo=signal_repo,
        alert_sink=alerts.append,
        position_held=lambda pid: pid == "pair-3",
    )
    orch.register_mint("mint-3", "pair-3")

    intake = MoralisWebhookIntake(
        orch.build_stream_sink(),
        watched_mints={"mint-3"},
        rug_drop_threshold_pct=Decimal(50),
    )
    payload = {
        "block": {"blockTime": NOW.timestamp()},
        "transactions": [
            {
                "signature": "sig-3",
                "preTokenBalances": [
                    {
                        "accountIndex": 1,
                        "mint": "mint-3",
                        "owner": "lp",
                        "uiTokenAmount": {"amount": "1000"},
                    }
                ],
                "postTokenBalances": [
                    {
                        "accountIndex": 1,
                        "mint": "mint-3",
                        "owner": "lp",
                        "uiTokenAmount": {"amount": "0"},
                    }
                ],
            }
        ],
    }
    response = intake.handle(payload)
    assert response.status_code == 200

    signals = signal_repo.history("pair-3")
    assert len(signals) == 1
    assert signals[0].exit_class.value == "RUG_PULL"
    assert len(alerts) == 1
    assert alerts[0].is_exit_signal is True


# ---------------------------------------------------------------------------
# Task 18.2: per-tick pipeline isolation
# ---------------------------------------------------------------------------


def test_tick_isolates_stage_failures():
    from dex_agent.control import DataIngestor
    from dex_agent.providers.fakes import FakeMarketDataProvider
    from dex_agent.repositories import InMemoryPairRepository

    market = FakeMarketDataProvider()
    snapshot = PairSnapshot(
        pair_id="pair-1",
        price=Decimal(1),
        liquidity=Decimal(1000),
        market_cap=Decimal(1),
        fdv=Decimal(1),
        buy_count=1,
        sell_count=1,
        buy_volume=Decimal(1),
        sell_volume=Decimal(1),
        fetched_at=NOW,
    )
    market.set_snapshot(snapshot)
    ingestor = DataIngestor(
        market,
        InMemoryWatchlistRepository(),
        InMemoryPairRepository(),
        clock=fixed_clock(),
    )

    class BlowingTracker:
        def register_pair(self, pair_id):
            pass

        def record(self, snap):
            raise RuntimeError("tracker down")

    orch = make_orchestrator(ingestor=ingestor, metrics_tracker=BlowingTracker())
    orch.add_pair("pair-1")
    result = orch.tick("pair-1")

    # Ingest succeeded; track failed in isolation; overall tick reports it.
    stage = {s.name: s for s in result.stages}
    assert stage["ingest"].ok is True
    assert stage["track"].ok is False
    assert result.ok is False
    assert result.snapshot is not None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
