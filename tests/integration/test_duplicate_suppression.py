"""Integration test 19.7: duplicate-order suppression (Req 12.1-12.4).

With a faked venue and an in-flight / open Position, asserts a second buy/sell
for the same pair is suppressed with no state change, and that the in-flight
marker clears exactly on a terminal status.
"""

from __future__ import annotations

from decimal import Decimal

from dex_agent.execution import ExecutionStatus
from dex_agent.models import (
    Network,
    OrderKind,
    OrderRecord,
    OrderStatus,
    PerOrderSize,
    PositionStatus,
)
from dex_agent.providers.interfaces import OrderRequest

from tests.integration.helpers import (
    QUOTE_MINT,
    build_test_agent,
    clean_security_inputs,
    make_config,
    make_profile,
    make_snapshot,
)

TOKEN = "TokenMint555"
PAIR = "pair-dup"
WALLET = "wallet-dup"


def _buy() -> OrderRequest:
    return OrderRequest(
        pair_id=PAIR,
        kind=OrderKind.BUY,
        input_mint=QUOTE_MINT,
        output_mint=TOKEN,
        amount=Decimal(0),
        max_slippage=Decimal(0),
    )


def _sell(qty: Decimal) -> OrderRequest:
    return OrderRequest(
        pair_id=PAIR,
        kind=OrderKind.SELL,
        input_mint=TOKEN,
        output_mint=QUOTE_MINT,
        amount=qty,
        max_slippage=Decimal(0),
    )


def _ready_agent():
    agent, fakes, clock = build_test_agent(
        config=make_config(),
        risk_profile=make_profile(per_order_size=PerOrderSize.fixed_quote(Decimal(10))),
        initial_quote_balance=Decimal(1000),
    )
    agent.boot()
    fakes.market.set_pairs(TOKEN, [make_snapshot(PAIR)])
    fakes.inspector.set_inputs(clean_security_inputs(TOKEN))
    agent.add_token(TOKEN, Network.SOLANA)
    agent.connect_wallet(WALLET)
    agent.enable_automated_trading()
    return agent, fakes, clock


def test_duplicate_buy_suppressed_when_position_open_no_state_change():
    agent, _fakes, _clock = _ready_agent()

    # First buy confirms and opens a position; the marker clears on the terminal
    # (CONFIRMED) status (Req 12.4).
    first = agent.trade_executor.submit_entry(_buy())
    assert first.status is ExecutionStatus.CONFIRMED
    assert agent.in_flight.has_in_flight(PAIR) is False

    position_before = agent.repositories.positions.get(PAIR).value
    orders_before = len(agent.repositories.orders.list_for_pair(PAIR))

    # A second buy for the same pair is suppressed (Req 12.1) with no state change.
    second = agent.trade_executor.submit_entry(_buy())
    assert second.status is ExecutionStatus.SUPPRESSED_DUPLICATE_ENTRY
    assert second.submitted is False
    assert second.order is None

    position_after = agent.repositories.positions.get(PAIR).value
    assert position_after == position_before  # no Position mutation
    assert len(agent.repositories.orders.list_for_pair(PAIR)) == orders_before


def test_duplicate_buy_suppressed_while_order_in_flight():
    agent, _fakes, _clock = _ready_agent()

    # Simulate a buy already in flight for the pair (Req 12.2).
    agent.in_flight.mark(
        PAIR,
        OrderRecord(
            pair_id=PAIR,
            kind=OrderKind.BUY,
            requested_qty=Decimal(10),
            notional=Decimal(10),
            max_slippage=Decimal(1),
            status=OrderStatus.SUBMITTED,
            recorded_at=agent.config.saved_at or _now(),
        ),
    )

    result = agent.trade_executor.submit_entry(_buy())
    assert result.status is ExecutionStatus.SUPPRESSED_DUPLICATE_ENTRY
    assert result.submitted is False
    assert agent.repositories.positions.get(PAIR).is_err()  # no position created


def test_duplicate_sell_suppressed_while_sell_in_flight_then_marker_clears():
    agent, _fakes, _clock = _ready_agent()

    # A sell is already in flight for the pair (Req 12.3).
    agent.in_flight.mark(
        PAIR,
        OrderRecord(
            pair_id=PAIR,
            kind=OrderKind.SELL,
            requested_qty=Decimal(5),
            notional=Decimal(10),
            max_slippage=Decimal(1),
            status=OrderStatus.SUBMITTED,
            recorded_at=_now(),
        ),
    )
    orders_before = len(agent.repositories.orders.list_for_pair(PAIR))

    result = agent.trade_executor.submit_exit(_sell(Decimal(5)))
    assert result.status is ExecutionStatus.SUPPRESSED_DUPLICATE_SELL
    assert result.submitted is False
    # No new order recorded and the marker is unchanged (still in flight).
    assert len(agent.repositories.orders.list_for_pair(PAIR)) == orders_before
    assert agent.in_flight.has_in_flight(PAIR) is True

    # Clearing on a terminal status removes the marker (Req 12.4).
    agent.in_flight.clear(PAIR)
    assert agent.in_flight.has_in_flight(PAIR) is False


def _now():
    from datetime import datetime, timezone

    return datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
