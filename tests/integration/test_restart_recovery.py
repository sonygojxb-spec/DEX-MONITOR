"""Integration test 19.6: restart state recovery (Req 13.1, 13.2, 13.3).

Persists open Positions and an active Watchlist, "restarts" the Agent (rebuilds
it over the same repositories), and asserts that recovery restores exactly those
Positions (with stop-loss/exit evaluation resumed) and resumes monitoring of
those pairs before any trade-affecting operation. Also covers the unreadable
persisted-state path (Req 13.4).
"""

from __future__ import annotations

from decimal import Decimal

from dex_agent.agent import AgentRepositories
from dex_agent.models import (
    OrderKind,
    OrderRecord,
    OrderStatus,
    Position,
    PositionStatus,
    WatchlistEntry,
    WatchlistSource,
)
from dex_agent.repositories import InMemoryPositionRepository

from tests.integration.helpers import NOW, build_test_agent

POS_PAIR = "pair-open"
WATCH_PAIR = "pair-watch"
TOKEN = "TokenMint444"


def _seed_persisted_state(repos: AgentRepositories) -> None:
    """Simulate state durably persisted by a prior Agent run."""
    repos.positions.upsert(
        Position(
            pair_id=POS_PAIR,
            token_address=TOKEN,
            quantity=Decimal(5),
            avg_entry_price=Decimal(2),
            notional_cost=Decimal(10),
            opened_at=NOW,
            status=PositionStatus.OPEN,
        )
    )
    repos.watchlist.add(
        WatchlistEntry(pair_id=POS_PAIR, added_at=NOW, source=WatchlistSource.MANUAL)
    )
    repos.watchlist.add(
        WatchlistEntry(
            pair_id=WATCH_PAIR, added_at=NOW, source=WatchlistSource.AUTO_DISCOVERY
        )
    )
    # A non-terminal order persisted from before the restart (Req 13 reconcile).
    repos.orders.append(
        OrderRecord(
            pair_id=POS_PAIR,
            kind=OrderKind.BUY,
            requested_qty=Decimal(5),
            notional=Decimal(10),
            max_slippage=Decimal(1),
            status=OrderStatus.SUBMITTED,
            recorded_at=NOW,
            tx_id="tx-recover-1",
        )
    )


def test_restart_recovers_positions_and_resumes_monitoring():
    repos = AgentRepositories.in_memory()
    _seed_persisted_state(repos)

    # "Restart": build a fresh Agent over the same persisted repositories.
    agent, _fakes, _clock = build_test_agent(repositories=repos)
    report = agent.boot()

    assert report.recovery_ok is True
    # Req 13.2: the open Position's pair is restored and monitoring resumed.
    assert POS_PAIR in report.restored_positions
    assert agent.is_monitoring(POS_PAIR) is True
    assert agent.repositories.positions.get(POS_PAIR).value.status is PositionStatus.OPEN

    # Req 13.3: the active Watchlist pair is resumed under the cap.
    assert WATCH_PAIR in report.resumed_watchlist
    assert agent.is_monitoring(WATCH_PAIR) is True

    # The non-terminal persisted order was reconciled on recovery.
    assert "tx-recover-1" in report.reconciled_orders

    # Req 13.1: recovery ran before any trade-affecting operation - and trading
    # remains gated (no wallet authorized at boot).
    assert agent.trading_allowed() is False
    assert agent.orchestrator.recovery_failed is False


def test_unreadable_persisted_state_forces_monitoring_only():
    # Req 13.4: if persisted state cannot be read, start monitoring-only and
    # surface the failure; submit no orders until resolved.
    class FailingPositions(InMemoryPositionRepository):
        def list_open(self):
            raise RuntimeError("corrupt position store")

    repos = AgentRepositories.in_memory()
    repos.positions = FailingPositions()

    agent, _fakes, _clock = build_test_agent(repositories=repos)
    report = agent.boot()

    assert report.recovery_ok is False
    assert report.monitoring_only is True
    assert report.recovery_error is not None
    assert agent.orchestrator.recovery_failed is True
    assert agent.trading_allowed() is False
