"""Tests for the Risk_Manager (Task 13).

Covers the design's Correctness Properties for risk management:

* Property 19 - risk approval predicate (subtask 13.3, Req 7.2, 7.3, 7.4, 7.7);
* Property 20 - rejected orders never change positions (subtask 13.4, Req 7.3, 7.4);
* Property 21 - stop-loss triggers a full-position sell (subtask 13.5, Req 7.5);
* Property 22 - risk-profile updates do not retroactively alter decisions
  (subtask 13.6, Req 7.6);

plus unit tests for the approval boundaries, rejection-reason priority, the
stop-loss full-position sell + sink seam, and non-retroactive profile updates.

Requirement numbering follows the design's Correctness-Property mapping (the
design pseudocode tags severity/total/per-token as Req 7.7/7.3/7.4).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.decision import (
    BuyApprovalRequest,
    RejectionReason,
    RiskManager,
    SellRequest,
    evaluate_buy,
    should_stop_loss,
    unrealized_loss_pct,
)
from dex_agent.models import (
    PerOrderSize,
    Position,
    PositionStatus,
    RiskProfile,
    Severity,
)
from dex_agent.repositories import InMemoryPositionRepository

# ---------------------------------------------------------------------------
# Builders / strategies
# ---------------------------------------------------------------------------

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

money = st.decimals(
    min_value=Decimal(0),
    max_value=Decimal("1000000"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
positive_money = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("1000000"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
positive_price = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("100000"),
    allow_nan=False,
    allow_infinity=False,
    places=4,
)
pct = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal(100),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
severities = st.sampled_from(list(Severity))


def make_profile(
    *,
    max_position_per_token: Decimal = Decimal(1000),
    max_total_exposure: Decimal = Decimal(5000),
    max_acceptable_severity: Severity = Severity.MEDIUM,
    stop_loss_pct: Decimal = Decimal(20),
) -> RiskProfile:
    return RiskProfile(
        per_order_size=PerOrderSize.fixed_quote(Decimal(100)),
        max_position_per_token=max_position_per_token,
        max_total_exposure=max_total_exposure,
        max_acceptable_severity=max_acceptable_severity,
        stop_loss_pct=stop_loss_pct,
    )


def make_position(
    *,
    pair_id: str,
    token_address: str,
    quantity: Decimal = Decimal(10),
    avg_entry_price: Decimal = Decimal(10),
    notional_cost: Decimal = Decimal(100),
    status: PositionStatus = PositionStatus.OPEN,
) -> Position:
    return Position(
        pair_id=pair_id,
        token_address=token_address,
        quantity=quantity,
        avg_entry_price=avg_entry_price,
        notional_cost=notional_cost,
        opened_at=NOW,
        status=status,
    )


def expected_reason(
    *,
    severity: Severity,
    current_token: Decimal,
    current_total: Decimal,
    notional: Decimal,
    profile: RiskProfile,
) -> RejectionReason | None:
    """The reference decision following the design's evaluation order."""
    if severity > profile.max_acceptable_severity:
        return RejectionReason.SEVERITY_EXCEEDED
    if current_total + notional > profile.max_total_exposure:
        return RejectionReason.TOTAL_EXPOSURE_EXCEEDED
    if current_token + notional > profile.max_position_per_token:
        return RejectionReason.PER_TOKEN_EXCEEDED
    return None


# ---------------------------------------------------------------------------
# Property 19: Risk approval predicate (Req 7.2, 7.3, 7.4, 7.7)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 19: Risk approval predicate
@settings(max_examples=100)
@given(
    severity=severities,
    max_severity=severities,
    current_token=money,
    current_total=money,
    notional=money,
    max_per_token=positive_money,
    max_total=positive_money,
)
def test_property_19_risk_approval_predicate(
    severity,
    max_severity,
    current_token,
    current_total,
    notional,
    max_per_token,
    max_total,
):
    """Validates: Requirements 7.2, 7.3, 7.4, 7.7.

    Approves iff resulting per-token size <= per-token limit AND resulting total
    exposure <= total limit AND severity <= max acceptable severity; otherwise
    rejects with the corresponding reason.
    """
    profile = make_profile(
        max_position_per_token=max_per_token,
        max_total_exposure=max_total,
        max_acceptable_severity=max_severity,
    )
    decision = evaluate_buy(
        severity=severity,
        current_token_notional=current_token,
        current_total_notional=current_total,
        order_notional=notional,
        profile=profile,
    )

    severity_ok = severity <= max_severity
    total_ok = current_total + notional <= max_total
    per_token_ok = current_token + notional <= max_per_token
    expected_approved = severity_ok and total_ok and per_token_ok

    assert decision.approved is expected_approved
    # The rejection reason is exact and deterministic (design evaluation order).
    assert decision.reason == expected_reason(
        severity=severity,
        current_token=current_token,
        current_total=current_total,
        notional=notional,
        profile=profile,
    )


def test_property_19_boundaries():
    """Both satisfying and non-satisfying sides of each limit boundary (iff)."""
    profile = make_profile(
        max_position_per_token=Decimal(1000),
        max_total_exposure=Decimal(5000),
        max_acceptable_severity=Severity.MEDIUM,
    )

    # --- total exposure boundary: resulting total exactly at the limit -> approve.
    assert evaluate_buy(
        severity=Severity.LOW,
        current_token_notional=Decimal(0),
        current_total_notional=Decimal(4900),
        order_notional=Decimal(100),  # -> 5000 == limit
        profile=profile,
    ).approved
    # One cent over -> reject TOTAL_EXPOSURE_EXCEEDED.
    over_total = evaluate_buy(
        severity=Severity.LOW,
        current_token_notional=Decimal(0),
        current_total_notional=Decimal(4900),
        order_notional=Decimal("100.01"),
        profile=profile,
    )
    assert not over_total.approved
    assert over_total.reason is RejectionReason.TOTAL_EXPOSURE_EXCEEDED

    # --- per-token boundary: resulting per-token exactly at the limit -> approve.
    assert evaluate_buy(
        severity=Severity.LOW,
        current_token_notional=Decimal(900),
        current_total_notional=Decimal(900),
        order_notional=Decimal(100),  # -> 1000 == limit
        profile=profile,
    ).approved
    # One cent over the per-token limit (still within total) -> PER_TOKEN_EXCEEDED.
    over_token = evaluate_buy(
        severity=Severity.LOW,
        current_token_notional=Decimal(900),
        current_total_notional=Decimal(900),
        order_notional=Decimal("100.01"),
        profile=profile,
    )
    assert not over_token.approved
    assert over_token.reason is RejectionReason.PER_TOKEN_EXCEEDED

    # --- severity boundary: exactly at max -> approve; one step above -> reject.
    assert evaluate_buy(
        severity=Severity.MEDIUM,
        current_token_notional=Decimal(0),
        current_total_notional=Decimal(0),
        order_notional=Decimal(100),
        profile=profile,
    ).approved
    over_sev = evaluate_buy(
        severity=Severity.HIGH,
        current_token_notional=Decimal(0),
        current_total_notional=Decimal(0),
        order_notional=Decimal(100),
        profile=profile,
    )
    assert not over_sev.approved
    assert over_sev.reason is RejectionReason.SEVERITY_EXCEEDED


def test_approve_buy_reads_current_positions():
    """approve_buy aggregates per-token + total exposure from open positions."""
    positions = InMemoryPositionRepository()
    # Two open positions in token A (pair-1, pair-2) and one in token B.
    positions.upsert(
        make_position(pair_id="p1", token_address="A", notional_cost=Decimal(400))
    )
    positions.upsert(
        make_position(pair_id="p2", token_address="A", notional_cost=Decimal(400))
    )
    positions.upsert(
        make_position(pair_id="p3", token_address="B", notional_cost=Decimal(1000))
    )
    profile = make_profile(
        max_position_per_token=Decimal(1000),
        max_total_exposure=Decimal(5000),
        max_acceptable_severity=Severity.HIGH,
    )
    rm = RiskManager(profile, positions, clock=lambda: NOW)

    # token A current = 800; +300 = 1100 > 1000 per-token limit -> reject.
    rejected = rm.approve_buy(
        BuyApprovalRequest(token_address="A", notional=Decimal(300), severity=Severity.LOW)
    )
    assert not rejected.approved
    assert rejected.reason is RejectionReason.PER_TOKEN_EXCEEDED

    # token A +150 = 950 <= 1000, total 1800+150=1950 <= 5000 -> approve.
    approved = rm.approve_buy(
        BuyApprovalRequest(token_address="A", notional=Decimal(150), severity=Severity.LOW)
    )
    assert approved.approved


# ---------------------------------------------------------------------------
# Property 20: Rejected orders never change positions (Req 7.3, 7.4)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 20: Rejected orders never change positions
@settings(max_examples=100)
@given(
    notional=positive_money,
    severity=severities,
    max_severity=severities,
)
def test_property_20_rejected_orders_never_change_positions(
    notional, severity, max_severity
):
    """Validates: Requirements 7.3, 7.4.

    For any rejected buy, all existing positions and the total exposure are
    unchanged after the decision.
    """
    positions = InMemoryPositionRepository()
    positions.upsert(
        make_position(pair_id="p1", token_address="A", notional_cost=Decimal(500))
    )
    positions.upsert(
        make_position(pair_id="p2", token_address="B", notional_cost=Decimal(800))
    )
    # Deliberately tight limits so most orders reject; severity may also reject.
    profile = make_profile(
        max_position_per_token=Decimal(600),
        max_total_exposure=Decimal(1400),
        max_acceptable_severity=max_severity,
    )
    rm = RiskManager(profile, positions, clock=lambda: NOW)

    before = list(positions.list_all())
    before_total = sum((p.notional_cost for p in positions.list_open()), Decimal(0))

    decision = rm.approve_buy(
        BuyApprovalRequest(token_address="A", notional=notional, severity=severity)
    )

    if not decision.approved:
        # Positions and total exposure are untouched by a rejection.
        assert positions.list_all() == before
        after_total = sum((p.notional_cost for p in positions.list_open()), Decimal(0))
        assert after_total == before_total


def test_approval_also_does_not_mutate_positions():
    """approve_buy is a pure gate: even an approval leaves positions unchanged."""
    positions = InMemoryPositionRepository()
    positions.upsert(
        make_position(pair_id="p1", token_address="A", notional_cost=Decimal(100))
    )
    rm = RiskManager(make_profile(), positions, clock=lambda: NOW)
    before = list(positions.list_all())

    approved = rm.approve_buy(
        BuyApprovalRequest(token_address="A", notional=Decimal(50), severity=Severity.LOW)
    )
    assert approved.approved
    assert positions.list_all() == before


# ---------------------------------------------------------------------------
# Property 21: Stop-loss triggers a full-position sell (Req 7.5)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 21: Stop-loss triggers a full-position sell
@settings(max_examples=100)
@given(
    avg_entry_price=positive_price,
    current_price=positive_price,
    stop_loss_pct=pct,
    quantity=positive_money,
)
def test_property_21_stop_loss_triggers_full_position_sell(
    avg_entry_price, current_price, stop_loss_pct, quantity
):
    """Validates: Requirements 7.5.

    A sell for the full position quantity is requested iff the unrealized loss
    percentage reaches or exceeds the stop-loss percentage; never while below.
    """
    positions = InMemoryPositionRepository()
    positions.upsert(
        make_position(
            pair_id="p1",
            token_address="A",
            quantity=quantity,
            avg_entry_price=avg_entry_price,
            notional_cost=avg_entry_price * quantity,
        )
    )
    profile = make_profile(stop_loss_pct=stop_loss_pct)
    requests: list[SellRequest] = []
    rm = RiskManager(
        profile, positions, sell_requester=requests.append, clock=lambda: NOW
    )

    result = rm.monitor_stop_loss(lambda _pair: current_price)

    loss = unrealized_loss_pct(avg_entry_price, current_price)
    expected_trigger = loss >= stop_loss_pct

    assert should_stop_loss(avg_entry_price, current_price, stop_loss_pct) is expected_trigger
    if expected_trigger:
        assert len(result) == 1
        assert result[0].pair_id == "p1"
        # Full-position sell: the requested quantity equals the held quantity.
        assert result[0].quantity == quantity
        assert result[0].reason == "STOP_LOSS"
        # Dispatched through the injected Trade_Executor seam exactly once.
        assert requests == result
    else:
        assert result == []
        assert requests == []


def test_property_21_boundaries():
    """A loss exactly at the stop-loss triggers; just below does not."""
    entry = Decimal(100)
    # Exactly 20% loss -> price 80 -> triggers at 20% stop-loss.
    assert should_stop_loss(entry, Decimal(80), Decimal(20))
    # 19.99% loss -> price 80.01 -> does not trigger.
    assert not should_stop_loss(entry, Decimal("80.01"), Decimal(20))
    # A price increase is never a loss / never triggers.
    assert not should_stop_loss(entry, Decimal(150), Decimal(20))
    assert unrealized_loss_pct(entry, Decimal(150)) == Decimal(0)


def test_stop_loss_skips_positions_without_price():
    """Positions with no available price are skipped (no sell requested)."""
    positions = InMemoryPositionRepository()
    positions.upsert(
        make_position(
            pair_id="p1", token_address="A", quantity=Decimal(10), avg_entry_price=Decimal(100)
        )
    )
    rm = RiskManager(make_profile(stop_loss_pct=Decimal(10)), positions, clock=lambda: NOW)
    result = rm.monitor_stop_loss(lambda _pair: None)
    assert result == []


def test_stop_loss_only_open_positions():
    """Closed positions are not evaluated for stop-loss."""
    positions = InMemoryPositionRepository()
    positions.upsert(
        make_position(
            pair_id="p1",
            token_address="A",
            quantity=Decimal(10),
            avg_entry_price=Decimal(100),
            status=PositionStatus.CLOSED,
        )
    )
    rm = RiskManager(make_profile(stop_loss_pct=Decimal(10)), positions, clock=lambda: NOW)
    # Price implies a 50% loss, but the position is CLOSED -> no request.
    result = rm.monitor_stop_loss(lambda _pair: Decimal(50))
    assert result == []


def test_eval_interval_must_be_at_most_60s():
    """The stop-loss evaluation interval is capped at 60 seconds (Req 7.5)."""
    positions = InMemoryPositionRepository()
    # Valid interval is accepted and exposed.
    rm = RiskManager(make_profile(), positions, eval_interval_s=30)
    assert rm.eval_interval_s == 30
    # An interval above 60s is rejected.
    import pytest

    with pytest.raises(ValueError):
        RiskManager(make_profile(), positions, eval_interval_s=61)


# ---------------------------------------------------------------------------
# Property 22: Risk-profile updates do not retroactively alter decisions (Req 7.6)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 22: Risk-profile updates do not retroactively alter decisions
@settings(max_examples=100)
@given(
    notional=positive_money,
    first_limit=positive_money,
    second_limit=positive_money,
)
def test_property_22_profile_updates_not_retroactive(
    notional, first_limit, second_limit
):
    """Validates: Requirements 7.6.

    A decision returned before a profile update is never altered by the update;
    decisions initiated after the update reflect the new profile.
    """
    positions = InMemoryPositionRepository()  # empty -> current exposure 0
    rm = RiskManager(
        make_profile(
            max_total_exposure=first_limit,
            max_position_per_token=first_limit,
            max_acceptable_severity=Severity.CRITICAL,
        ),
        positions,
        clock=lambda: NOW,
    )
    request = BuyApprovalRequest(
        token_address="A", notional=notional, severity=Severity.NONE
    )

    # Decision under the first profile.
    first_decision = rm.approve_buy(request)
    first_approved_snapshot = first_decision.approved
    first_reason_snapshot = first_decision.reason
    expected_first = notional <= first_limit  # empty positions -> resulting == notional

    # Update to a second profile (different limits).
    rm.update_profile(
        make_profile(
            max_total_exposure=second_limit,
            max_position_per_token=second_limit,
            max_acceptable_severity=Severity.CRITICAL,
        )
    )

    # The already-returned decision is unchanged (immutability + non-retroactive).
    assert first_decision.approved == first_approved_snapshot == expected_first
    assert first_decision.reason == first_reason_snapshot

    # A new decision reflects the updated profile.
    second_decision = rm.approve_buy(request)
    assert second_decision.approved is (notional <= second_limit)


def test_update_profile_applies_to_later_decisions_and_is_exposed():
    """update_profile swaps the active profile for subsequent approvals (Req 7.6)."""
    positions = InMemoryPositionRepository()
    rm = RiskManager(
        make_profile(max_total_exposure=Decimal(100), max_position_per_token=Decimal(100)),
        positions,
        clock=lambda: NOW,
    )
    req = BuyApprovalRequest(token_address="A", notional=Decimal(150), severity=Severity.LOW)

    # 150 > 100 limit -> rejected under the first profile.
    assert not rm.approve_buy(req).approved

    # Raise the limits; the same order now approves.
    rm.update_profile(
        make_profile(max_total_exposure=Decimal(1000), max_position_per_token=Decimal(1000))
    )
    assert rm.profile.max_total_exposure == Decimal(1000)
    assert rm.approve_buy(req).approved


def test_update_profile_persists_when_repo_injected():
    """update_profile persists the new profile when a repository is injected."""
    from dex_agent.repositories import InMemoryRiskProfileRepository

    positions = InMemoryPositionRepository()
    repo = InMemoryRiskProfileRepository()
    rm = RiskManager(make_profile(), positions, profile_repo=repo, clock=lambda: NOW)

    new_profile = make_profile(max_total_exposure=Decimal(9999))
    rm.update_profile(new_profile)

    saved = repo.get()
    assert saved.is_ok()
    assert saved.value.max_total_exposure == Decimal(9999)
