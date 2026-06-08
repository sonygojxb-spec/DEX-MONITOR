"""Unit tests for the repository layer (subtask 3.1).

Covers the shared query primitives (``entries_in_range`` inclusivity/ordering,
``older_than`` boundary behavior), append idempotency across the in-memory
repositories, and the Result-returning failure paths (NotFound for
not-monitored pairs / missing entities).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from dex_agent.errors import NotFound
from dex_agent.models import (
    ActionType,
    AuditRecord,
    AuthorizationRecord,
    AuthStatus,
    Configuration,
    MetricEntry,
    MetricKind,
    Network,
    OrderKind,
    OrderRecord,
    OrderStatus,
    PerOrderSize,
    Position,
    PositionStatus,
    RiskProfile,
    SecurityEvaluation,
    Severity,
    Signal,
    SignalType,
    Token,
    TradingPair,
    WalletAnalysis,
    WatchlistEntry,
    WatchlistSource,
    make_trading_pair,
)
from dex_agent.repositories import (
    InMemoryAuditRepository,
    InMemoryAuthorizationRepository,
    InMemoryConfigRepository,
    InMemoryMetricsRepository,
    InMemoryOrderRepository,
    InMemoryPairRepository,
    InMemoryPositionRepository,
    InMemoryRiskProfileRepository,
    InMemorySecurityEvalRepository,
    InMemorySignalRepository,
    InMemoryTokenRepository,
    InMemoryWalletAnalysisRepository,
    InMemoryWatchlistRepository,
    entries_in_range,
    older_than,
)


def _ts(seconds: int) -> datetime:
    """A deterministic UTC timestamp offset by ``seconds`` from a fixed epoch."""
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(seconds=seconds)


def _metric(pair_id: str, kind: MetricKind, seconds: int, value: str) -> MetricEntry:
    return MetricEntry(
        pair_id=pair_id, kind=kind, value=Decimal(value), recorded_at=_ts(seconds)
    )


def _audit(pair_id: str, seconds: int, outcome: str = "ok") -> AuditRecord:
    return AuditRecord(
        action_type=ActionType.SIGNAL_COMPUTATION,
        pair_id=pair_id,
        outcome=outcome,
        recorded_at=_ts(seconds),
    )


# ---------------------------------------------------------------------------
# Shared query primitives
# ---------------------------------------------------------------------------


def test_entries_in_range_is_inclusive_and_ascending():
    items = [_audit("p", s) for s in (50, 10, 30, 20, 40)]
    result = entries_in_range(items, _ts(20), _ts(40))
    # Inclusive of both bounds (20 and 40 present) and ascending.
    assert [r.recorded_at for r in result] == [_ts(20), _ts(30), _ts(40)]


def test_entries_in_range_excludes_outside_bounds():
    items = [_audit("p", s) for s in (10, 20, 30)]
    # Range strictly inside the gap between points -> empty.
    assert entries_in_range(items, _ts(11), _ts(19)) == []
    # Single-instant inclusive range hits the exact point.
    single = entries_in_range(items, _ts(20), _ts(20))
    assert [r.recorded_at for r in single] == [_ts(20)]


def test_entries_in_range_inverted_range_is_empty():
    items = [_audit("p", s) for s in (10, 20, 30)]
    assert entries_in_range(items, _ts(30), _ts(10)) == []


def test_older_than_returns_strictly_older_entries():
    items = [_audit("p", s) for s in (0, 100, 200, 300)]
    now = _ts(300)
    # period=150 -> boundary at _ts(150); entries strictly older than 150.
    expired = older_than(items, timedelta(seconds=150), now=now)
    assert [r.recorded_at for r in expired] == [_ts(0), _ts(100)]


def test_older_than_boundary_is_not_expired():
    # An entry exactly at the boundary (age == period) is still retained.
    items = [_audit("p", 0)]
    now = _ts(100)
    assert older_than(items, timedelta(seconds=100), now=now) == []
    # One second older than the boundary IS expired.
    assert older_than([_audit("p", 0)], timedelta(seconds=99), now=now)


# ---------------------------------------------------------------------------
# Metrics repository
# ---------------------------------------------------------------------------


def test_metrics_append_is_idempotent_on_key():
    repo = InMemoryMetricsRepository()
    entry = _metric("p1", MetricKind.LIQUIDITY, 10, "100")
    repo.append(entry)
    repo.append(entry)  # retry with identical key
    # Same (pair_id, kind, recorded_at) but different value also dedupes (first wins).
    repo.append(_metric("p1", MetricKind.LIQUIDITY, 10, "999"))
    entries = repo.all_entries("p1")
    assert len(entries) == 1
    assert entries[0].value == Decimal("100")


def test_metrics_distinct_keys_coexist():
    repo = InMemoryMetricsRepository()
    repo.append(_metric("p1", MetricKind.LIQUIDITY, 10, "1"))
    repo.append(_metric("p1", MetricKind.MARKET_CAP, 10, "2"))  # different kind
    repo.append(_metric("p1", MetricKind.LIQUIDITY, 20, "3"))  # different ts
    assert len(repo.all_entries("p1")) == 3


def test_metrics_query_range_not_monitored_is_notfound():
    repo = InMemoryMetricsRepository()
    result = repo.query_range("ghost", _ts(0), _ts(100))
    assert result.is_err()
    assert isinstance(result.error, NotFound)


def test_metrics_query_range_monitored_empty_is_ok_empty():
    repo = InMemoryMetricsRepository()
    repo.register_pair("p1")
    result = repo.query_range("p1", _ts(0), _ts(100))
    assert result.is_ok()
    assert result.value == []


def test_metrics_query_range_inclusive_ascending():
    repo = InMemoryMetricsRepository()
    for s in (50, 10, 30):
        repo.append(_metric("p1", MetricKind.LIQUIDITY, s, str(s)))
    result = repo.query_range("p1", _ts(10), _ts(30))
    assert result.is_ok()
    assert [e.recorded_at for e in result.value] == [_ts(10), _ts(30)]


def test_metrics_purge_older_than_removes_and_returns_expired():
    repo = InMemoryMetricsRepository()
    for s in (0, 100, 300):
        repo.append(_metric("p1", MetricKind.LIQUIDITY, s, str(s)))
    removed = repo.purge_older_than(timedelta(seconds=150), now=_ts(300))
    assert {r.recorded_at for r in removed} == {_ts(0), _ts(100)}
    assert [e.recorded_at for e in repo.all_entries("p1")] == [_ts(300)]


# ---------------------------------------------------------------------------
# Audit repository
# ---------------------------------------------------------------------------


def test_audit_append_is_idempotent():
    repo = InMemoryAuditRepository()
    rec = _audit("p1", 10)
    repo.append(rec)
    repo.append(rec)
    assert len(repo.all_records("p1")) == 1


def test_audit_query_range_inclusive_ascending_and_empty():
    repo = InMemoryAuditRepository()
    for s in (40, 10, 20):
        repo.append(_audit("p1", s))
    got = repo.query_range("p1", _ts(10), _ts(20))
    assert [r.recorded_at for r in got] == [_ts(10), _ts(20)]
    # No records in range -> empty without error (Req 10.3).
    assert repo.query_range("p1", _ts(100), _ts(200)) == []


def test_audit_purge_older_than_boundary():
    repo = InMemoryAuditRepository()
    for s in (0, 100, 200):
        repo.append(_audit("p1", s))
    removed = repo.purge_older_than(timedelta(seconds=100), now=_ts(200))
    # boundary _ts(100); only _ts(0) strictly older.
    assert [r.recorded_at for r in removed] == [_ts(0)]


# ---------------------------------------------------------------------------
# Order repository: idempotency + in-flight tracking
# ---------------------------------------------------------------------------


def _order(pair_id: str, status: OrderStatus, seconds: int, tx_id=None) -> OrderRecord:
    return OrderRecord(
        pair_id=pair_id,
        kind=OrderKind.BUY,
        requested_qty=Decimal("1"),
        notional=Decimal("10"),
        max_slippage=Decimal("1"),
        status=status,
        recorded_at=_ts(seconds),
        tx_id=tx_id,
    )


def test_order_append_idempotent_on_tx_id():
    repo = InMemoryOrderRepository()
    repo.append(_order("p1", OrderStatus.CONFIRMED, 10, tx_id="TX1"))
    repo.append(_order("p1", OrderStatus.CONFIRMED, 20, tx_id="TX1"))  # retry
    assert len(repo.list_for_pair("p1")) == 1


def test_order_append_idempotent_on_synthetic_key_when_no_tx():
    repo = InMemoryOrderRepository()
    o = _order("p1", OrderStatus.SUBMITTED, 10)
    repo.append(o)
    repo.append(o)
    assert len(repo.list_for_pair("p1")) == 1


def test_order_in_flight_tracking():
    repo = InMemoryOrderRepository()
    repo.append(_order("p1", OrderStatus.SUBMITTED, 10, tx_id="TX1"))
    assert repo.has_in_flight("p1")
    assert repo.in_flight("p1").is_ok()
    assert repo.list_non_terminal()
    # A terminal order does not count as in-flight.
    repo2 = InMemoryOrderRepository()
    repo2.append(_order("p2", OrderStatus.CONFIRMED, 10, tx_id="TX2"))
    assert not repo2.has_in_flight("p2")
    assert repo2.in_flight("p2").is_err()
    assert repo2.list_non_terminal() == []


# ---------------------------------------------------------------------------
# Analysis-history repositories
# ---------------------------------------------------------------------------


def test_security_eval_idempotent_and_latest():
    repo = InMemorySecurityEvalRepository()
    e1 = SecurityEvaluation(
        token_address="MINT",
        rating=Severity.LOW,
        unverified=False,
        evaluated_at=_ts(10),
    )
    e2 = SecurityEvaluation(
        token_address="MINT",
        rating=Severity.HIGH,
        unverified=False,
        evaluated_at=_ts(20),
    )
    repo.append(e1)
    repo.append(e1)  # idempotent
    repo.append(e2)
    assert len(repo.history("MINT")) == 2
    assert repo.latest("MINT").value.rating == Severity.HIGH
    assert repo.latest("OTHER").is_err()


def test_wallet_analysis_history_ascending():
    repo = InMemoryWalletAnalysisRepository()

    def wa(seconds: int) -> WalletAnalysis:
        return WalletAnalysis(
            pair_id="p1",
            window_minutes=60,
            distinct_wallet_count=5,
            bot_tx_percentage=Decimal("10"),
            holder_concentration_pct=Decimal("20"),
            concentration_risk_flag=False,
            data_unavailable=False,
            analyzed_at=_ts(seconds),
        )

    repo.append(wa(30))
    repo.append(wa(10))
    assert [a.analyzed_at for a in repo.history("p1")] == [_ts(10), _ts(30)]
    assert repo.latest("p1").value.analyzed_at == _ts(30)


def test_signal_latest_by_type():
    repo = InMemorySignalRepository()

    def sig(stype: SignalType, seconds: int) -> Signal:
        return Signal(
            pair_id="p1",
            type=stype,
            score=Decimal("1"),
            eligible=True,
            generated_at=_ts(seconds),
        )

    repo.append(sig(SignalType.ENTRY, 10))
    repo.append(sig(SignalType.EXIT, 20))
    repo.append(sig(SignalType.ENTRY, 30))
    assert repo.latest("p1", SignalType.ENTRY).value.generated_at == _ts(30)
    assert repo.latest("p1", SignalType.EXIT).value.generated_at == _ts(20)
    assert len(repo.history("p1")) == 3


# ---------------------------------------------------------------------------
# Entity repositories
# ---------------------------------------------------------------------------


def _token() -> Token:
    return Token(
        address="MINT",
        network=Network.SOLANA,
        symbol="FOO",
        name="Foo",
        total_supply=Decimal("1000"),
    )


def test_token_repo_idempotent_and_get():
    repo = InMemoryTokenRepository()
    repo.add(_token())
    repo.add(_token())
    assert len(repo.list_all()) == 1
    assert repo.get("MINT", Network.SOLANA).is_ok()
    assert repo.get("NOPE", Network.SOLANA).is_err()


def test_pair_repo_add_get_exists():
    repo = InMemoryPairRepository()
    pair = make_trading_pair(
        id="PAIR1",
        token=_token(),
        quote_asset="USDC",
        dex="raydium",
        created_at=_ts(0),
    ).value
    repo.add(pair)
    repo.add(pair)
    assert len(repo.list_all()) == 1
    assert repo.exists("PAIR1")
    assert repo.get("PAIR1").is_ok()
    assert repo.get("X").is_err()


def test_watchlist_deactivate_retains_data():
    repo = InMemoryWatchlistRepository()
    entry = WatchlistEntry(
        pair_id="PAIR1", added_at=_ts(0), source=WatchlistSource.MANUAL
    )
    repo.add(entry)
    assert repo.list_active()
    result = repo.deactivate("PAIR1")
    assert result.is_ok()
    assert result.value.active is False
    # Data retained (Req 1.4): still present in list_all, absent from active.
    assert repo.list_all()
    assert repo.list_active() == []
    assert repo.deactivate("MISSING").is_err()


def test_position_repo_open_and_upsert():
    repo = InMemoryPositionRepository()

    def pos(status: PositionStatus) -> Position:
        return Position(
            pair_id="p1",
            token_address="MINT",
            quantity=Decimal("1"),
            avg_entry_price=Decimal("2"),
            notional_cost=Decimal("2"),
            opened_at=_ts(0),
            status=status,
        )

    repo.upsert(pos(PositionStatus.OPEN))
    assert len(repo.list_open()) == 1
    repo.upsert(pos(PositionStatus.CLOSED))  # replace
    assert repo.list_open() == []
    assert len(repo.list_all()) == 1
    assert repo.get("p1").is_ok()
    assert repo.get("x").is_err()


# ---------------------------------------------------------------------------
# Singleton repositories
# ---------------------------------------------------------------------------


def test_risk_profile_repo_latest_wins():
    repo = InMemoryRiskProfileRepository()
    assert repo.get().is_err()
    profile = RiskProfile(
        per_order_size=PerOrderSize.fixed_quote(Decimal("10")),
        max_position_per_token=Decimal("100"),
        max_total_exposure=Decimal("1000"),
        max_acceptable_severity=Severity.MEDIUM,
        stop_loss_pct=Decimal("10"),
    )
    repo.save(profile)
    assert repo.get().value is profile


def test_config_repo_latest_wins():
    repo = InMemoryConfigRepository()
    assert repo.latest().is_err()
    cfg = Configuration(
        discovery_scan_interval_s=60,
        measurement_period_s=300,
        bot_pct_threshold=Decimal("50"),
        holder_conc_threshold=Decimal("50"),
        rugpull_threshold=Decimal("50"),
        dump_threshold=Decimal("2"),
        entry_threshold=Decimal("50"),
        slippage_tolerance=Decimal("1"),
    )
    repo.save(cfg)
    assert repo.latest().value is cfg


def test_authorization_history_and_latest():
    repo = InMemoryAuthorizationRepository()
    r1 = AuthorizationRecord(
        wallet_id="W", status=AuthStatus.ENABLED, changed_at=_ts(10)
    )
    r2 = AuthorizationRecord(
        wallet_id="W", status=AuthStatus.REVOKED, changed_at=_ts(20)
    )
    repo.append(r1)
    repo.append(r1)  # idempotent
    repo.append(r2)
    assert len(repo.history("W")) == 2
    assert repo.latest("W").value.status == AuthStatus.REVOKED
    assert repo.latest("NONE").is_err()
