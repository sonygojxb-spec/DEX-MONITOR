"""Unit tests for core data-model construction.

Covers subtask 2.3 (model construction) for the models defined in subtasks 2.1
and 2.2: identity/market, security, wallet, metrics, signals, positions/risk,
orders + the in-flight registry, config, audit, and auth. Also exercises the
quote-asset validation factory and the ``MISSING`` sentinel.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal

from dex_agent.errors import NotFound
from dex_agent.models import (
    MISSING,
    ActionType,
    AuditInfo,
    AuditRecord,
    AuthorizationRecord,
    AuthStatus,
    Configuration,
    ExitClass,
    HolderBalance,
    InFlightRegistry,
    MetricEntry,
    MetricKind,
    Network,
    OrderKind,
    OrderRecord,
    OrderStatus,
    PairSnapshot,
    PerOrderSize,
    PerOrderSizeKind,
    Position,
    PositionStatus,
    RiskProfile,
    SecurityEvaluation,
    SecurityIssue,
    SecurityIssueType,
    Severity,
    Signal,
    SignalType,
    TERMINAL_ORDER_STATUS,
    TimeWindow,
    Token,
    TradingPair,
    WalletAnalysis,
    WalletClassification,
    WatchlistEntry,
    WatchlistSource,
    make_trading_pair,
)


def _token() -> Token:
    return Token(
        address="MintAddr111",
        network=Network.SOLANA,
        symbol="FOO",
        name="Foo Token",
        total_supply=Decimal("1000000"),
    )


def _now() -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------
# Identity & market
# --------------------------------------------------------------------------


def test_token_and_network_construction():
    token = _token()
    assert token.network is Network.SOLANA
    assert token.total_supply == Decimal("1000000")


def test_make_trading_pair_accepts_supported_quote_assets():
    for quote in ("SOL", "USDC"):
        result = make_trading_pair(
            id=f"pair-{quote}",
            token=_token(),
            quote_asset=quote,
            dex="raydium",
            created_at=_now(),
        )
        assert result.is_ok()
        assert result.value.quote_asset == quote


def test_make_trading_pair_rejects_unsupported_quote_asset():
    result = make_trading_pair(
        id="pair-bad",
        token=_token(),
        quote_asset="USDT",
        dex="raydium",
        created_at=_now(),
    )
    assert result.is_err()
    assert isinstance(result.error, NotFound)
    assert result.error.identifier == "USDT"


def test_trading_pair_is_frozen():
    pair = make_trading_pair(
        id="p1",
        token=_token(),
        quote_asset="SOL",
        dex="raydium",
        created_at=_now(),
    ).value
    try:
        pair.quote_asset = "USDC"  # type: ignore[misc]
    except Exception:
        pass
    else:  # pragma: no cover
        raise AssertionError("TradingPair should be immutable")


def test_watchlist_entry_defaults_active_true():
    entry = WatchlistEntry(
        pair_id="p1", added_at=_now(), source=WatchlistSource.AUTO_DISCOVERY
    )
    assert entry.active is True


def test_pair_snapshot_optional_audit_and_stale_defaults():
    snap = PairSnapshot(
        pair_id="p1",
        price=Decimal("1.5"),
        liquidity=Decimal("1000"),
        market_cap=Decimal("5000"),
        fdv=Decimal("9000"),
        buy_count=10,
        sell_count=3,
        buy_volume=Decimal("100"),
        sell_volume=Decimal("30"),
        fetched_at=_now(),
    )
    assert snap.audit is None
    assert snap.is_stale is False

    audited = PairSnapshot(
        pair_id="p1",
        price=Decimal("1.5"),
        liquidity=Decimal("1000"),
        market_cap=Decimal("5000"),
        fdv=Decimal("9000"),
        buy_count=10,
        sell_count=3,
        buy_volume=Decimal("100"),
        sell_volume=Decimal("30"),
        fetched_at=_now(),
        audit=AuditInfo(provider="GoPlus", result="ok", audit_date=date(2024, 1, 1)),
        is_stale=True,
    )
    assert audited.audit.provider == "GoPlus"
    assert audited.is_stale is True


# --------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------


def test_security_evaluation_construction():
    issue = SecurityIssue(
        type=SecurityIssueType.MINTABLE,
        description="active mint authority",
        severity=Severity.MEDIUM,
    )
    evaluation = SecurityEvaluation(
        token_address="MintAddr111",
        rating=Severity.MEDIUM,
        unverified=False,
        evaluated_at=_now(),
        issues=(issue,),
    )
    assert evaluation.issues[0].type is SecurityIssueType.MINTABLE
    assert evaluation.rating is Severity.MEDIUM


def test_security_evaluation_defaults_to_no_issues():
    evaluation = SecurityEvaluation(
        token_address="MintAddr111",
        rating=Severity.NONE,
        unverified=False,
        evaluated_at=_now(),
    )
    assert evaluation.issues == ()


# --------------------------------------------------------------------------
# Wallet / backend
# --------------------------------------------------------------------------


def test_wallet_models_construction():
    analysis = WalletAnalysis(
        pair_id="p1",
        window_minutes=60,
        distinct_wallet_count=42,
        bot_tx_percentage=Decimal("12.5"),
        holder_concentration_pct=Decimal("40"),
        concentration_risk_flag=False,
        data_unavailable=False,
        analyzed_at=_now(),
    )
    assert analysis.distinct_wallet_count == 42
    assert WalletClassification.BOT.value == "BOT"
    assert HolderBalance(wallet="w1", balance=Decimal("5")).balance == Decimal("5")


# --------------------------------------------------------------------------
# Metrics + MISSING sentinel
# --------------------------------------------------------------------------


def test_metric_entry_with_value_and_missing():
    valued = MetricEntry(
        pair_id="p1",
        kind=MetricKind.LIQUIDITY,
        value=Decimal("1000"),
        recorded_at=_now(),
    )
    assert valued.value == Decimal("1000")

    missing = MetricEntry(
        pair_id="p1",
        kind=MetricKind.FDV,
        value=MISSING,
        recorded_at=_now(),
    )
    assert missing.value is MISSING


def test_missing_is_distinct_from_none_and_zero():
    assert MISSING is not None
    assert MISSING != 0
    assert MISSING != Decimal("0")


# --------------------------------------------------------------------------
# Signals
# --------------------------------------------------------------------------


def test_entry_and_exit_signal_construction():
    entry = Signal(
        pair_id="p1",
        type=SignalType.ENTRY,
        score=Decimal("80"),
        eligible=True,
        generated_at=_now(),
    )
    assert entry.exit_class is None
    assert entry.contributing_metrics == {}

    exit_signal = Signal(
        pair_id="p1",
        type=SignalType.EXIT,
        score=Decimal("0"),
        eligible=False,
        generated_at=_now(),
        exit_class=ExitClass.RUG_PULL,
        contributing_metrics={"liquidity_drop_pct": 90},
    )
    assert exit_signal.exit_class is ExitClass.RUG_PULL
    assert exit_signal.contributing_metrics["liquidity_drop_pct"] == 90


# --------------------------------------------------------------------------
# Positions & risk
# --------------------------------------------------------------------------


def test_position_construction():
    position = Position(
        pair_id="p1",
        token_address="MintAddr111",
        quantity=Decimal("100"),
        avg_entry_price=Decimal("1.0"),
        notional_cost=Decimal("100"),
        opened_at=_now(),
        status=PositionStatus.OPEN,
    )
    assert position.status is PositionStatus.OPEN


def test_per_order_size_discriminated_factories():
    fixed = PerOrderSize.fixed_quote(Decimal("5"))
    assert fixed.kind is PerOrderSizeKind.FIXED_QUOTE
    assert fixed.value == Decimal("5")

    pct = PerOrderSize.percent_balance(Decimal("25"))
    assert pct.kind is PerOrderSizeKind.PERCENT_BALANCE
    assert pct.value == Decimal("25")


def test_risk_profile_construction():
    profile = RiskProfile(
        per_order_size=PerOrderSize.fixed_quote(Decimal("10")),
        max_position_per_token=Decimal("100"),
        max_total_exposure=Decimal("1000"),
        max_acceptable_severity=Severity.MEDIUM,
        stop_loss_pct=Decimal("20"),
    )
    assert profile.per_order_size.kind is PerOrderSizeKind.FIXED_QUOTE
    assert profile.max_acceptable_severity is Severity.MEDIUM


# --------------------------------------------------------------------------
# Orders + in-flight registry
# --------------------------------------------------------------------------


def _order(status: OrderStatus, pair_id: str = "p1") -> OrderRecord:
    return OrderRecord(
        pair_id=pair_id,
        kind=OrderKind.BUY,
        requested_qty=Decimal("10"),
        notional=Decimal("10"),
        max_slippage=Decimal("1"),
        status=status,
        recorded_at=_now(),
    )


def test_terminal_order_status_set_and_predicate():
    assert TERMINAL_ORDER_STATUS == {
        OrderStatus.CONFIRMED,
        OrderStatus.CANCELLED,
        OrderStatus.FAILED,
        OrderStatus.TIMED_OUT,
    }
    assert OrderStatus.SUBMITTED.is_terminal() is False
    for status in TERMINAL_ORDER_STATUS:
        assert status.is_terminal() is True


def test_in_flight_registry_tracks_one_order_per_pair():
    registry = InFlightRegistry()
    assert registry.has_in_flight("p1") is False

    order = _order(OrderStatus.SUBMITTED)
    registry.mark("p1", order)
    assert registry.has_in_flight("p1") is True
    assert registry.get("p1") is order

    # clearing on terminal status removes the marker
    registry.clear("p1")
    assert registry.has_in_flight("p1") is False
    assert registry.get("p1") is None
    # clearing again is a no-op
    registry.clear("p1")
    assert registry.has_in_flight("p1") is False


def test_in_flight_registry_independent_pairs():
    registry = InFlightRegistry()
    registry.mark("p1", _order(OrderStatus.SUBMITTED, "p1"))
    registry.mark("p2", _order(OrderStatus.SUBMITTED, "p2"))
    assert registry.has_in_flight("p1")
    assert registry.has_in_flight("p2")
    registry.clear("p1")
    assert not registry.has_in_flight("p1")
    assert registry.has_in_flight("p2")


def test_order_record_optional_execution_fields():
    order = _order(OrderStatus.SUBMITTED)
    assert order.executed_price is None
    assert order.tx_id is None
    assert order.reason is None


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------


def test_configuration_documented_defaults():
    config = Configuration(
        discovery_scan_interval_s=30,
        measurement_period_s=60,
        bot_pct_threshold=Decimal("50"),
        holder_conc_threshold=Decimal("50"),
        rugpull_threshold=Decimal("50"),
        dump_threshold=Decimal("2"),
        entry_threshold=Decimal("50"),
        slippage_tolerance=Decimal("1"),
    )
    assert config.refresh_interval_s == 30
    assert config.signal_interval_s == 15
    assert config.confirmation_timeout_s == 60
    assert config.exit_alert_retries == 3
    assert config.retention_days == 30
    assert config.automated_trading_enabled is False
    assert config.quiet_hours is None


def test_configuration_distinct_interval_fields():
    config = Configuration(
        discovery_scan_interval_s=120,
        measurement_period_s=300,
        bot_pct_threshold=Decimal("10"),
        holder_conc_threshold=Decimal("10"),
        rugpull_threshold=Decimal("10"),
        dump_threshold=Decimal("1"),
        entry_threshold=Decimal("10"),
        slippage_tolerance=Decimal("0.5"),
        refresh_interval_s=60,
        signal_interval_s=5,
        quiet_hours=TimeWindow(start=time(22, 0), end=time(6, 0)),
    )
    # refresh and signal intervals are distinct fields
    assert config.refresh_interval_s == 60
    assert config.signal_interval_s == 5
    assert config.discovery_scan_interval_s == 120
    assert config.measurement_period_s == 300
    assert config.quiet_hours.start == time(22, 0)


# --------------------------------------------------------------------------
# Audit & auth
# --------------------------------------------------------------------------


def test_audit_record_construction():
    record = AuditRecord(
        action_type=ActionType.TRADE_EXECUTION,
        pair_id="p1",
        outcome="confirmed",
        recorded_at=_now(),
    )
    assert record.action_type is ActionType.TRADE_EXECUTION


def test_authorization_record_construction():
    record = AuthorizationRecord(
        wallet_id="wallet-1", status=AuthStatus.ENABLED, changed_at=_now()
    )
    assert record.status is AuthStatus.ENABLED
