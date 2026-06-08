"""Integration test 19.3: end-to-end authorized buy/sell happy path.

With a faked venue: authorize the wallet, enable trading, drive an eligible
entry through the Risk_Manager to a confirmed buy, then an exit signal to a
confirmed sell, asserting the confirmation notifications were delivered
(Req 6.1, 6.2, 8.1).
"""

from __future__ import annotations

from decimal import Decimal

from dex_agent.execution import ExecutionStatus
from dex_agent.models import Network, OrderKind, PerOrderSize, PositionStatus
from dex_agent.providers.interfaces import OrderRequest

from tests.integration.helpers import (
    QUOTE_MINT,
    build_test_agent,
    clean_security_inputs,
    make_config,
    make_profile,
    make_snapshot,
)

TOKEN = "TokenMint222"
PAIR = "pair-xyz"
WALLET = "wallet-1"


def _buy_request() -> OrderRequest:
    return OrderRequest(
        pair_id=PAIR,
        kind=OrderKind.BUY,
        input_mint=QUOTE_MINT,
        output_mint=TOKEN,
        amount=Decimal(0),  # the executor sizes from Per_Order_Size (Req 6.9)
        max_slippage=Decimal(0),  # the executor attaches the configured slippage
    )


def _sell_request(qty: Decimal) -> OrderRequest:
    return OrderRequest(
        pair_id=PAIR,
        kind=OrderKind.SELL,
        input_mint=TOKEN,
        output_mint=QUOTE_MINT,
        amount=qty,
        max_slippage=Decimal(0),
    )


def test_authorized_buy_then_sell_happy_path():
    agent, fakes, _clock = build_test_agent(
        config=make_config(),
        risk_profile=make_profile(per_order_size=PerOrderSize.fixed_quote(Decimal(10))),
        initial_quote_balance=Decimal(1000),
    )
    agent.boot()

    # Resolve + monitor the pair and evaluate the token (severity NONE, eligible).
    fakes.market.set_pairs(TOKEN, [make_snapshot(PAIR)])
    fakes.inspector.set_inputs(clean_security_inputs(TOKEN))
    assert agent.add_token(TOKEN, Network.SOLANA).is_ok()

    # Two explicit user actions enable trading (Req 11.x, 6.3).
    assert agent.connect_wallet(WALLET).is_ok()
    agent.enable_automated_trading()
    assert agent.trading_allowed() is True

    # --- eligible entry -> confirmed buy (Req 6.1) ---
    buy = agent.trade_executor.submit_entry(_buy_request())
    assert buy.status is ExecutionStatus.CONFIRMED
    assert buy.confirmed is True
    # The signer was invoked exactly once on the gated buy path (Property 23).
    assert len(fakes.signer.sign_calls) == 1

    position = agent.repositories.positions.get(PAIR)
    assert position.is_ok()
    assert position.value.status is PositionStatus.OPEN
    assert position.value.quantity == Decimal(5)  # executed_qty from the venue

    # The in-flight marker cleared on the terminal (CONFIRMED) status (Req 12.4).
    assert agent.in_flight.has_in_flight(PAIR) is False

    # --- exit signal -> confirmed sell (Req 6.2) ---
    sell = agent.trade_executor.submit_exit(_sell_request(position.value.quantity))
    assert sell.status is ExecutionStatus.CONFIRMED

    closed = agent.repositories.positions.get(PAIR)
    assert closed.is_ok()
    assert closed.value.status is PositionStatus.CLOSED

    # --- confirmation notifications were delivered (Req 8.1) ---
    titles = [a.title for a in fakes.channel.delivered]
    assert "Order confirmed: BUY" in titles
    assert "Order confirmed: SELL" in titles


def test_no_trade_while_monitoring_only():
    # Without enabling trading, the same entry is a monitoring-only no-op and the
    # signer is never invoked (Property 23 / Req 6.3, 11.3).
    agent, fakes, _clock = build_test_agent(
        config=make_config(),
        risk_profile=make_profile(),
        initial_quote_balance=Decimal(1000),
    )
    agent.boot()
    fakes.market.set_pairs(TOKEN, [make_snapshot(PAIR)])
    fakes.inspector.set_inputs(clean_security_inputs(TOKEN))
    agent.add_token(TOKEN, Network.SOLANA)

    result = agent.trade_executor.submit_entry(_buy_request())
    assert result.status is ExecutionStatus.MONITORING_ONLY
    assert result.submitted is False
    assert fakes.signer.sign_calls == []
    assert agent.repositories.positions.get(PAIR).is_err()
