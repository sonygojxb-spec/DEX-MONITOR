"""Tests for the Trade_Executor (Task 15, safety-critical).

Covers the design's Correctness Properties for trade execution:

* Property 4  - trades require an assigned severity rating (15.3, Req 2.3);
* Property 23 - monitoring-only safety: no order without authorization AND
  enablement (15.4, Req 6.3, 11.2, 11.3, 11.4);
* Property 24 - submitted orders carry the configured slippage tolerance
  (15.5, Req 6.4);
* Property 25 - non-confirmed orders never change position or balance
  (15.6, Req 6.6, 6.7, 6.8);
* Property 32 - trade idempotency and in-flight order control
  (15.10, Req 12.1, 12.2, 12.3, 12.4);
* Property 34 - order sizing and balance sufficiency (15.11, Req 6.9, 6.10);

plus a unit test for the order-confirmation record fields (15.7, Req 6.5).

All external providers are in-memory fakes - no real network/chain/signing
calls - and the signer is a fake that records invocations so the
monitoring-only safety property can assert the signing path is never reached
when the gate is closed (design "Signer / Key Handling", Property 23).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.decision import RiskManager
from dex_agent.execution import (
    ExecutionStatus,
    Signer,
    TradeExecutor,
    cap_to_risk_limits,
    resolve_order_size,
)
from dex_agent.models import (
    OrderKind,
    OrderStatus,
    PerOrderSize,
    Position,
    PositionStatus,
    RiskProfile,
    Severity,
)
from dex_agent.providers.fakes import FakeTradeVenueProvider
from dex_agent.providers.interfaces import Alert, Confirmation, OrderRequest
from dex_agent.errors import ProviderError, TimedOut
from dex_agent.repositories import (
    InMemoryOrderRepository,
    InMemoryPositionRepository,
)
from dex_agent.result import Err, Ok

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

QUOTE_MINT = "QUOTE_SOL"
TOKEN_MINT = "TKN"
PAIR = "tgt"


# ---------------------------------------------------------------------------
# Fakes / builders
# ---------------------------------------------------------------------------


class FakeSigner(Signer):
    """In-memory signer that records every invocation (no real keys)."""

    def __init__(self) -> None:
        self.sign_calls: list[str] = []

    @property
    def public_key(self) -> str:
        return "FakePubKey1111"

    def sign_transaction(self, serialized_tx: str) -> str:
        self.sign_calls.append(serialized_tx)
        return f"signed:{serialized_tx}"


class AutoConfirmVenue(FakeTradeVenueProvider):
    """A venue fake that auto-confirms any submitted tx with scripted fields."""

    def __init__(
        self,
        *,
        confirmed: bool = True,
        executed_slippage: Decimal = Decimal(0),
        executed_price: Decimal = Decimal(2),
        executed_qty: Decimal = Decimal(5),
        fee: Decimal = Decimal("0.01"),
        now: datetime = NOW,
    ) -> None:
        super().__init__(now=now)
        self._confirmed = confirmed
        self._executed_slippage = executed_slippage
        self._executed_price = executed_price
        self._executed_qty = executed_qty
        self._fee = fee

    def poll_confirmation(self, tx_id, timeout):
        self.record("poll_confirmation", tx_id, timeout)
        err = self._next_error("poll_confirmation")
        if err is not None:
            return Err(err)
        return Ok(
            Confirmation(
                tx_id=tx_id,
                confirmed=self._confirmed,
                executed_price=self._executed_price,
                executed_qty=self._executed_qty,
                fee=self._fee,
                executed_slippage=self._executed_slippage,
                confirmed_at=self._now,
            )
        )


def make_profile(
    *,
    per_order_size: PerOrderSize | None = None,
    max_position_per_token: Decimal = Decimal(100000),
    max_total_exposure: Decimal = Decimal(1000000),
    max_acceptable_severity: Severity = Severity.CRITICAL,
    stop_loss_pct: Decimal = Decimal(20),
) -> RiskProfile:
    return RiskProfile(
        per_order_size=per_order_size or PerOrderSize.fixed_quote(Decimal(100)),
        max_position_per_token=max_position_per_token,
        max_total_exposure=max_total_exposure,
        max_acceptable_severity=max_acceptable_severity,
        stop_loss_pct=stop_loss_pct,
    )


def build_executor(
    *,
    profile: RiskProfile | None = None,
    positions: InMemoryPositionRepository | None = None,
    orders: InMemoryOrderRepository | None = None,
    venue: FakeTradeVenueProvider | None = None,
    signer: FakeSigner | None = None,
    trading_enabled: bool = True,
    automated_trading_enabled: bool = True,
    severity: Severity | None = Severity.NONE,
    balance: Decimal = Decimal(100000),
    max_slippage: Decimal = Decimal("1.5"),
    alerts: list[Alert] | None = None,
    confirmation_timeout_s: int = 60,
):
    profile = profile or make_profile()
    positions = positions if positions is not None else InMemoryPositionRepository()
    orders = orders if orders is not None else InMemoryOrderRepository()
    venue = venue if venue is not None else AutoConfirmVenue()
    signer = signer or FakeSigner()
    alerts = alerts if alerts is not None else []
    rm = RiskManager(profile, positions, clock=lambda: NOW)
    executor = TradeExecutor(
        venue=venue,
        signer=signer,
        risk_manager=rm,
        positions=positions,
        orders=orders,
        trading_enabled=lambda: trading_enabled,
        automated_trading_enabled=lambda: automated_trading_enabled,
        severity_for=lambda _addr: severity,
        available_quote_balance=lambda: balance,
        max_slippage=max_slippage,
        alert_sink=alerts.append,
        confirmation_timeout_s=confirmation_timeout_s,
        clock=lambda: NOW,
    )
    return executor, positions, orders, venue, signer, alerts


def entry_order(
    *, pair_id: str = PAIR, token: str = TOKEN_MINT, amount: Decimal = Decimal(0)
) -> OrderRequest:
    return OrderRequest(
        pair_id=pair_id,
        kind=OrderKind.BUY,
        input_mint=QUOTE_MINT,
        output_mint=token,
        amount=amount,
        max_slippage=Decimal(0),
    )


def exit_order(
    *, pair_id: str = PAIR, token: str = TOKEN_MINT, amount: Decimal = Decimal(5)
) -> OrderRequest:
    return OrderRequest(
        pair_id=pair_id,
        kind=OrderKind.SELL,
        input_mint=token,
        output_mint=QUOTE_MINT,
        amount=amount,
        max_slippage=Decimal(0),
    )


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

money = st.decimals(
    min_value=Decimal(0),
    max_value=Decimal(2000),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
positive_money = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal(2000),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
slippage = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal(50),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
percents = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal(100),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
severities = st.sampled_from(list(Severity))


# ---------------------------------------------------------------------------
# Property 4: Trades require an assigned severity rating (Req 2.3)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 4: Trades require an assigned severity rating
@settings(max_examples=100)
@given(severity=st.one_of(st.none(), severities))
def test_property_4_trades_require_assigned_severity(severity):
    """Validates: Requirements 2.3.

    An entry buy is rejected outright when the Token has no assigned
    Severity_Rating (``None``); when a rating *is* assigned the severity guard
    is passed and the trade proceeds. No signing occurs for an unrated token.
    """
    executor, positions, orders, venue, signer, _alerts = build_executor(
        severity=severity, balance=Decimal(100000)
    )

    result = executor.submit_entry(entry_order())

    if severity is None:
        assert result.status is ExecutionStatus.NO_SEVERITY_RATING
        assert result.submitted is False
        # No order reached the venue and the signer was never invoked.
        assert venue.submitted == []
        assert signer.sign_calls == []
        assert positions.list_all() == []
    else:
        # An assigned rating passes the severity guard; with generous limits and
        # balance the order confirms.
        assert result.status is ExecutionStatus.CONFIRMED
        assert signer.sign_calls  # signing happened only after the gate


# ---------------------------------------------------------------------------
# Property 23: Monitoring-only safety (Req 6.3, 11.2, 11.3, 11.4)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 23: Monitoring-only safety - no order without authorization and enablement
@settings(max_examples=100)
@given(
    trading_enabled=st.booleans(),
    automated=st.booleans(),
    is_exit=st.booleans(),
)
def test_property_23_monitoring_only_safety(trading_enabled, automated, is_exit):
    """Validates: Requirements 6.3, 11.2, 11.3, 11.4.

    An order is submitted only if an authorized trading wallet is connected AND
    automated trading is enabled; in every other state no order is submitted, a
    recommendation is sent instead, and the signer is never invoked.
    """
    positions = InMemoryPositionRepository()
    if is_exit:
        # A held position so an exit has something to act on.
        positions.upsert(
            Position(
                pair_id=PAIR,
                token_address=TOKEN_MINT,
                quantity=Decimal(5),
                avg_entry_price=Decimal(2),
                notional_cost=Decimal(10),
                opened_at=NOW,
                status=PositionStatus.OPEN,
            )
        )
    executor, positions, orders, venue, signer, alerts = build_executor(
        positions=positions,
        trading_enabled=trading_enabled,
        automated_trading_enabled=automated,
        severity=Severity.LOW,
        balance=Decimal(100000),
    )

    result = (
        executor.submit_exit(exit_order())
        if is_exit
        else executor.submit_entry(entry_order())
    )

    gate_open = trading_enabled and automated
    if gate_open:
        assert result.submitted is True
        assert venue.submitted  # an order reached the venue
        assert signer.sign_calls  # signing only on the gated path
    else:
        assert result.status is ExecutionStatus.MONITORING_ONLY
        assert result.submitted is False
        assert venue.submitted == []
        assert signer.sign_calls == []  # signer NEVER reachable when gate closed
        # A recommendation is sent instead of an order.
        assert len(alerts) == 1
        assert "recommendation" in alerts[0].title.lower()


# ---------------------------------------------------------------------------
# Property 24: Submitted orders carry the configured slippage tolerance (Req 6.4)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 24: Submitted orders carry the configured slippage tolerance
@settings(max_examples=100)
@given(max_slippage=slippage)
def test_property_24_submitted_orders_carry_slippage(max_slippage):
    """Validates: Requirements 6.4.

    Every order submitted to the venue carries the user-configured maximum
    slippage tolerance, and the recorded order reflects the same tolerance.
    """
    # The venue confirms with an executed slippage at/below max so the order is
    # accepted (slippage breach is exercised separately in Property 25).
    venue = AutoConfirmVenue(executed_slippage=Decimal(0))
    executor, positions, orders, venue, signer, _alerts = build_executor(
        venue=venue, severity=Severity.LOW, max_slippage=max_slippage
    )

    result = executor.submit_entry(entry_order())
    assert result.status is ExecutionStatus.CONFIRMED

    # The OrderRequest handed to the venue carried the configured slippage.
    submit_calls = [c for c in venue.calls if c[0] == "submit_order"]
    assert len(submit_calls) == 1
    submitted_request = submit_calls[0][1][0]
    assert submitted_request.max_slippage == max_slippage
    # And it was signed before submission (signed tx, not key material).
    assert submitted_request.signed_transaction is not None
    # The recorded order also reflects the tolerance.
    assert result.order.max_slippage == max_slippage


# ---------------------------------------------------------------------------
# Property 25: Non-confirmed orders never change position or balance
#              (Req 6.6, 6.7, 6.8)
# ---------------------------------------------------------------------------

FAILURE_MODES = ["submission_fail", "timeout", "not_confirmed", "slippage_breach"]


# Feature: dex-trading-agent, Property 25: Non-confirmed orders never change position or balance
@settings(max_examples=100)
@given(mode=st.sampled_from(FAILURE_MODES), balance=positive_money)
def test_property_25_non_confirmed_no_side_effects(mode, balance):
    """Validates: Requirements 6.6, 6.7, 6.8.

    For a submission failure, a confirmation timeout, an unconfirmed order, or an
    executed-slippage breach, the Position store and the wallet balance are left
    unchanged and the in-flight marker is cleared.
    """
    # A mutable balance holder so we can assert it is never mutated.
    balance_box = {"v": balance + Decimal(100000)}
    positions = InMemoryPositionRepository()
    orders = InMemoryOrderRepository()

    venue = AutoConfirmVenue()
    if mode == "submission_fail":
        venue.fail_next("submit_order", ProviderError("boom", provider="fake"))
        expected = ExecutionStatus.SUBMISSION_FAILED
    elif mode == "timeout":
        venue.fail_next("poll_confirmation", TimedOut("no confirm", timeout_s=60))
        expected = ExecutionStatus.TIMED_OUT
    elif mode == "not_confirmed":
        venue = AutoConfirmVenue(confirmed=False)
        expected = ExecutionStatus.SUBMISSION_FAILED
    else:  # slippage_breach
        venue = AutoConfirmVenue(executed_slippage=Decimal(99))
        expected = ExecutionStatus.SLIPPAGE_EXCEEDED

    rm = RiskManager(make_profile(), positions, clock=lambda: NOW)
    signer = FakeSigner()
    executor = TradeExecutor(
        venue=venue,
        signer=signer,
        risk_manager=rm,
        positions=positions,
        orders=orders,
        trading_enabled=lambda: True,
        automated_trading_enabled=lambda: True,
        severity_for=lambda _a: Severity.LOW,
        available_quote_balance=lambda: balance_box["v"],
        max_slippage=Decimal(1),
        clock=lambda: NOW,
    )

    positions_before = list(positions.list_all())
    balance_before = balance_box["v"]

    result = executor.submit_entry(entry_order())

    assert result.status is expected
    assert result.confirmed is False
    # No position created or mutated.
    assert positions.list_all() == positions_before == []
    # Balance unchanged (the executor never debits the wallet on a non-fill).
    assert balance_box["v"] == balance_before
    # In-flight marker cleared for the pair (Req 12.4); nothing left in flight.
    assert executor.in_flight.has_in_flight(PAIR) is False


# ---------------------------------------------------------------------------
# Property 32: Trade idempotency and in-flight order control
#              (Req 12.1, 12.2, 12.3, 12.4)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 32: Trade idempotency and in-flight order control
@settings(max_examples=100)
@given(
    position_open=st.booleans(),
    marker_kind=st.sampled_from([None, OrderKind.BUY, OrderKind.SELL]),
    op=st.sampled_from(["entry", "exit"]),
)
def test_property_32_idempotency_and_in_flight_control(
    position_open, marker_kind, op
):
    """Validates: Requirements 12.1, 12.2, 12.3, 12.4.

    No new buy is submitted while a Position is open or an order is in flight; no
    duplicate sell is submitted while a sell is in flight; suppression makes no
    state change; and the in-flight marker is cleared exactly on a terminal
    status.
    """
    positions = InMemoryPositionRepository()
    orders = InMemoryOrderRepository()
    if position_open:
        positions.upsert(
            Position(
                pair_id=PAIR,
                token_address=TOKEN_MINT,
                quantity=Decimal(5),
                avg_entry_price=Decimal(2),
                notional_cost=Decimal(10),
                opened_at=NOW,
                status=PositionStatus.OPEN,
            )
        )
    executor, positions, orders, venue, signer, _alerts = build_executor(
        positions=positions,
        orders=orders,
        severity=Severity.LOW,
        balance=Decimal(100000),
    )
    # Optionally seed a pre-existing in-flight marker for the pair.
    if marker_kind is not None:
        from dex_agent.models import OrderRecord

        executor.in_flight.mark(
            PAIR,
            OrderRecord(
                pair_id=PAIR,
                kind=marker_kind,
                requested_qty=Decimal(1),
                notional=Decimal(1),
                max_slippage=Decimal(1),
                status=OrderStatus.SUBMITTED,
                recorded_at=NOW,
                tx_id="pre-existing",
            ),
        )

    positions_before = list(positions.list_all())

    if op == "entry":
        result = executor.submit_entry(entry_order())
        suppressed = position_open or (marker_kind is not None)
        if suppressed:
            assert result.status is ExecutionStatus.SUPPRESSED_DUPLICATE_ENTRY
            assert result.submitted is False
            assert venue.submitted == []  # no new order
            assert positions.list_all() == positions_before  # no state change
            # The pre-existing marker (if any) is untouched.
            if marker_kind is not None:
                assert executor.in_flight.get(PAIR).tx_id == "pre-existing"
        else:
            # Fresh pair, no marker -> dispatches and confirms.
            assert result.status is ExecutionStatus.CONFIRMED
            assert executor.in_flight.has_in_flight(PAIR) is False  # cleared (12.4)
    else:  # exit
        result = executor.submit_exit(exit_order())
        suppressed = marker_kind is OrderKind.SELL
        if suppressed:
            assert result.status is ExecutionStatus.SUPPRESSED_DUPLICATE_SELL
            assert result.submitted is False
            assert venue.submitted == []
            assert positions.list_all() == positions_before
            assert executor.in_flight.get(PAIR).tx_id == "pre-existing"
        else:
            # A BUY marker or no marker does not block a sell; it confirms and
            # the marker is cleared on the terminal status.
            assert result.status is ExecutionStatus.CONFIRMED
            assert executor.in_flight.has_in_flight(PAIR) is False

    # At most one in-flight order per pair at any time (registry is keyed by pair).
    assert executor.in_flight.get(PAIR) is None or isinstance(
        executor.in_flight.get(PAIR).tx_id, str
    )


def test_in_flight_cleared_on_each_terminal_status():
    """The in-flight marker is set on submit and cleared on every terminal state."""
    for mode in ["confirmed", "timeout", "slippage", "submission_fail"]:
        positions = InMemoryPositionRepository()
        orders = InMemoryOrderRepository()
        venue = AutoConfirmVenue()
        if mode == "timeout":
            venue.fail_next("poll_confirmation", TimedOut("t", timeout_s=60))
        elif mode == "slippage":
            venue = AutoConfirmVenue(executed_slippage=Decimal(99))
        elif mode == "submission_fail":
            venue.fail_next("submit_order", ProviderError("x", provider="fake"))
        rm = RiskManager(make_profile(), positions, clock=lambda: NOW)
        executor = TradeExecutor(
            venue=venue,
            signer=FakeSigner(),
            risk_manager=rm,
            positions=positions,
            orders=orders,
            trading_enabled=lambda: True,
            automated_trading_enabled=lambda: True,
            severity_for=lambda _a: Severity.LOW,
            available_quote_balance=lambda: Decimal(100000),
            max_slippage=Decimal(1),
            clock=lambda: NOW,
        )
        executor.submit_entry(entry_order())
        # After any terminal outcome the marker is cleared.
        assert executor.in_flight.has_in_flight(PAIR) is False


# ---------------------------------------------------------------------------
# Property 34: Order sizing and balance sufficiency (Req 6.9, 6.10)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 34: Order sizing and balance sufficiency
@settings(max_examples=100)
@given(
    use_percent=st.booleans(),
    fixed_value=positive_money,
    percent_value=percents,
    balance=money,
    max_per_token=positive_money,
    max_total=positive_money,
    other_exposure=money,
)
def test_property_34_order_sizing_and_balance_sufficiency(
    use_percent,
    fixed_value,
    percent_value,
    balance,
    max_per_token,
    max_total,
    other_exposure,
):
    """Validates: Requirements 6.9, 6.10.

    The prepared buy size is derived from the Per_Order_Size and capped so the
    resulting per-Token position and total exposure stay within Risk_Profile
    limits; an order that the available balance cannot fund is never submitted
    and is recorded with an insufficient-balance reason.
    """
    per_order_size = (
        PerOrderSize.percent_balance(percent_value)
        if use_percent
        else PerOrderSize.fixed_quote(fixed_value)
    )
    profile = make_profile(
        per_order_size=per_order_size,
        max_position_per_token=max_per_token,
        max_total_exposure=max_total,
        max_acceptable_severity=Severity.CRITICAL,
    )
    positions = InMemoryPositionRepository()
    # Pre-existing exposure in a DIFFERENT token/pair so it counts toward total
    # exposure but never collides with (or suppresses) the target pair.
    if other_exposure > 0:
        positions.upsert(
            Position(
                pair_id="other",
                token_address="OTHER",
                quantity=Decimal(1),
                avg_entry_price=Decimal(1),
                notional_cost=other_exposure,
                opened_at=NOW,
                status=PositionStatus.OPEN,
            )
        )
    orders = InMemoryOrderRepository()
    venue = AutoConfirmVenue(executed_slippage=Decimal(0))
    executor, positions, orders, venue, signer, alerts = build_executor(
        profile=profile,
        positions=positions,
        orders=orders,
        venue=venue,
        severity=Severity.NONE,
        balance=balance,
        max_slippage=Decimal(5),
    )

    # Reference computation of the prepared (capped) size.
    raw = resolve_order_size(per_order_size, available_quote_balance=balance)
    expected = cap_to_risk_limits(
        raw,
        current_token_notional=Decimal(0),
        current_total_notional=other_exposure,
        max_position_per_token=max_per_token,
        max_total_exposure=max_total,
    )

    result = executor.submit_entry(entry_order())

    if expected <= 0:
        # No room within risk limits -> no order submitted, no new position.
        assert result.status is ExecutionStatus.RISK_REJECTED
        assert venue.submitted == []
        assert positions.get(PAIR).is_err()
    elif balance < expected:
        # Insufficient balance (Req 6.10): no submission, reason recorded, notify.
        assert result.status is ExecutionStatus.INSUFFICIENT_BALANCE
        assert result.submitted is False
        assert venue.submitted == []
        assert positions.get(PAIR).is_err()
        assert result.order is not None and "INSUFFICIENT_BALANCE" in result.order.reason
        assert any("INSUFFICIENT_BALANCE" in a.title for a in alerts)
    else:
        # Funded and within limits -> submitted at the capped size and confirmed.
        assert result.status is ExecutionStatus.CONFIRMED
        assert result.order.notional == expected
        # Resulting per-Token and total exposure stay within the limits.
        assert Decimal(0) + expected <= max_per_token
        assert other_exposure + expected <= max_total
        # The opened Position carries the capped notional as its cost.
        pos = positions.get(PAIR)
        assert pos.is_ok()
        assert pos.value.notional_cost == expected


def test_sizing_helpers_fixed_and_percent():
    """resolve_order_size / cap_to_risk_limits unit checks."""
    # Fixed quote ignores balance.
    assert resolve_order_size(
        PerOrderSize.fixed_quote(Decimal(250)), available_quote_balance=Decimal(10)
    ) == Decimal(250)
    # Percent of available balance.
    assert resolve_order_size(
        PerOrderSize.percent_balance(Decimal(25)), available_quote_balance=Decimal(400)
    ) == Decimal(100)
    # Cap to the smaller of size / per-token room / total room.
    assert cap_to_risk_limits(
        Decimal(500),
        current_token_notional=Decimal(0),
        current_total_notional=Decimal(0),
        max_position_per_token=Decimal(300),
        max_total_exposure=Decimal(1000),
    ) == Decimal(300)
    # No room -> 0.
    assert cap_to_risk_limits(
        Decimal(500),
        current_token_notional=Decimal(300),
        current_total_notional=Decimal(0),
        max_position_per_token=Decimal(300),
        max_total_exposure=Decimal(1000),
    ) == Decimal(0)


# ---------------------------------------------------------------------------
# Unit test 15.7: Order confirmation record fields (Req 6.5)
# ---------------------------------------------------------------------------


def test_confirmation_record_fields():
    """Validates Requirement 6.5: a confirmed order records type, executed price,
    quantity, fee, tx id, and a timestamp."""
    confirmed_at = datetime(2025, 1, 2, 9, 30, 0, tzinfo=timezone.utc)
    venue = AutoConfirmVenue(
        executed_price=Decimal("3.25"),
        executed_qty=Decimal(40),
        fee=Decimal("0.07"),
        executed_slippage=Decimal("0.2"),
        now=confirmed_at,
    )
    executor, positions, orders, venue, signer, alerts = build_executor(
        venue=venue, severity=Severity.LOW, max_slippage=Decimal(1)
    )

    result = executor.submit_entry(entry_order())

    assert result.status is ExecutionStatus.CONFIRMED
    rec = result.order
    assert rec.kind is OrderKind.BUY
    assert rec.status is OrderStatus.CONFIRMED
    assert rec.executed_price == Decimal("3.25")
    assert rec.executed_qty == Decimal(40)
    assert rec.fee == Decimal("0.07")
    assert rec.tx_id is not None
    assert rec.recorded_at == confirmed_at
    # The order is persisted and the position opened.
    persisted = orders.list_for_pair(PAIR)
    assert any(o.status is OrderStatus.CONFIRMED for o in persisted)
    assert positions.get(PAIR).is_ok()
    # A confirmation message was sent (Req 8.1 seam).
    assert any("confirmed" in a.title.lower() for a in alerts)
