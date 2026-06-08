"""Tests for the Metrics_Tracker (Task 9).

Covers the design's Correctness Properties for the metrics time series:

* Property 12 - metric series is stored in ascending timestamp order
  (subtask 9.3, Req 4.4, 4.10);
* Property 13 - range queries return exactly the in-range entries, ascending
  (subtask 9.4, Req 4.6, 4.9, 10.2, 10.3);
* Property 14 - inverted time ranges are rejected without mutation
  (subtask 9.5, Req 4.7, 4.8, 10.4);

plus unit tests for metric-recording fields and the not-monitored query error
(subtask 9.6, Req 4.1-4.3, 4.5, 4.8).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.analysis import (
    FALLBACK_AUDIT_PROVIDER,
    PRIMARY_AUDIT_PROVIDER,
    MetricsTracker,
    build_audit_info,
)
from dex_agent.errors import InvalidRange, NotFound
from dex_agent.models import (
    MISSING,
    AuditInfo,
    MetricKind,
    PairSnapshot,
)
from dex_agent.repositories import InMemoryMetricsRepository

# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
PAIR_ID = "pair-1"

REFRESH_KINDS = {MetricKind.LIQUIDITY, MetricKind.MARKET_CAP, MetricKind.FDV}
PERIOD_KINDS = {
    MetricKind.BUY_COUNT,
    MetricKind.SELL_COUNT,
    MetricKind.BUY_VOLUME,
    MetricKind.SELL_VOLUME,
}
ALL_KINDS = REFRESH_KINDS | PERIOD_KINDS


def make_snapshot(
    *,
    pair_id: str = PAIR_ID,
    fetched_at: datetime = NOW,
    liquidity: Decimal = Decimal("1000"),
    market_cap: Decimal = Decimal("5000"),
    fdv: Decimal = Decimal("9000"),
    buy_count: int = 3,
    sell_count: int = 2,
    buy_volume: Decimal = Decimal("120"),
    sell_volume: Decimal = Decimal("80"),
    audit: AuditInfo | None = None,
) -> PairSnapshot:
    return PairSnapshot(
        pair_id=pair_id,
        price=Decimal("1.5"),
        liquidity=liquidity,
        market_cap=market_cap,
        fdv=fdv,
        buy_count=buy_count,
        sell_count=sell_count,
        buy_volume=buy_volume,
        sell_volume=sell_volume,
        fetched_at=fetched_at,
        audit=audit,
    )


def make_tracker() -> tuple[MetricsTracker, InMemoryMetricsRepository]:
    repo = InMemoryMetricsRepository()
    return MetricsTracker(repo), repo


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Distinct second-offsets so each recorded snapshot lands on its own timestamp
# (the repo is idempotent on (pair_id, kind, second-precision timestamp)).
offsets_st = st.lists(
    st.integers(min_value=0, max_value=100_000),
    min_size=0,
    max_size=12,
    unique=True,
)

decimal_st = st.decimals(
    min_value=0, max_value=10_000_000, allow_nan=False, allow_infinity=False, places=2
)
count_st = st.integers(min_value=0, max_value=10_000)


@st.composite
def snapshot_plan(draw):
    """A list of (offset_seconds, missing_kinds) describing snapshots to record."""
    offsets = draw(offsets_st)
    plan = []
    for off in offsets:
        # Randomly mark a subset of kinds as unavailable (Req 4.10).
        missing = draw(
            st.sets(st.sampled_from(sorted(ALL_KINDS, key=lambda k: k.value)))
        )
        plan.append((off, missing))
    return plan


# ---------------------------------------------------------------------------
# Property 12 - ascending-ordered series storage (subtask 9.3, Req 4.4, 4.10)
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(plan=snapshot_plan())
def test_property_12_series_ascending_timestamp_order(plan):
    # Feature: dex-trading-agent, Property 12: Metric series is stored in ascending timestamp order
    tracker, repo = make_tracker()
    for off, missing in plan:
        ts = NOW + timedelta(seconds=off)
        tracker.record(make_snapshot(fetched_at=ts), missing=missing)

    entries = repo.all_entries(PAIR_ID)
    timestamps = [e.recorded_at for e in entries]
    # Stored ascending by timestamp regardless of insertion order or MISSING values.
    assert timestamps == sorted(timestamps)
    # MISSING is recorded (Req 4.10) and does not break ordering.
    assert all(e.value is MISSING or isinstance(e.value, Decimal) for e in entries)


# ---------------------------------------------------------------------------
# Property 13 - in-range query correctness (subtask 9.4, Req 4.6, 4.9, 10.2, 10.3)
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    offsets=offsets_st,
    lo=st.integers(min_value=-10, max_value=100_010),
    hi=st.integers(min_value=-10, max_value=100_010),
)
def test_property_13_range_query_returns_exactly_in_range_ascending(offsets, lo, hi):
    # Feature: dex-trading-agent, Property 13: Range queries return exactly the in-range entries, ascending
    start_off, end_off = (lo, hi) if lo <= hi else (hi, lo)
    tracker, _ = make_tracker()
    tracker.register_pair(PAIR_ID)
    for off in offsets:
        tracker.record(make_snapshot(fetched_at=NOW + timedelta(seconds=off)))

    start = NOW + timedelta(seconds=start_off)
    end = NOW + timedelta(seconds=end_off)

    result = tracker.query_history(PAIR_ID, start, end)
    assert result.is_ok()
    got = result.value

    # Expected: every stored entry whose timestamp is within the inclusive range,
    # ascending by timestamp (Req 4.6, 4.9). Empty when none fall in range. Built
    # independently from the repo's full view.
    all_entries = tracker._repo.all_entries(PAIR_ID)  # noqa: SLF001 - test introspection
    expected = sorted(
        (e for e in all_entries if start <= e.recorded_at <= end),
        key=lambda e: e.recorded_at,
    )

    assert got == expected
    got_ts = [e.recorded_at for e in got]
    assert got_ts == sorted(got_ts)


# ---------------------------------------------------------------------------
# Property 14 - inverted-range rejection without mutation (subtask 9.5, Req 4.7, 4.8, 10.4)
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    offsets=offsets_st,
    a=st.integers(min_value=0, max_value=100_000),
    b=st.integers(min_value=0, max_value=100_000),
)
def test_property_14_inverted_range_rejected_without_mutation(offsets, a, b):
    # Feature: dex-trading-agent, Property 14: Inverted time ranges are rejected without mutation
    # Force a strictly inverted range (start > end).
    start_off, end_off = (a, b) if a > b else (b, a)
    if start_off == end_off:
        start_off += 1

    tracker, repo = make_tracker()
    tracker.register_pair(PAIR_ID)
    for off in offsets:
        tracker.record(make_snapshot(fetched_at=NOW + timedelta(seconds=off)))

    before = repo.all_entries(PAIR_ID)
    start = NOW + timedelta(seconds=start_off)
    end = NOW + timedelta(seconds=end_off)

    result = tracker.query_history(PAIR_ID, start, end)

    assert result.is_err()
    assert isinstance(result.error, InvalidRange)
    # Stored data left unchanged (Req 4.7, 10.4).
    assert repo.all_entries(PAIR_ID) == before


# ---------------------------------------------------------------------------
# Unit tests - metric-recording fields and not-monitored query (subtask 9.6)
# ---------------------------------------------------------------------------


def test_record_appends_refresh_and_period_metrics_with_fields():
    # Req 4.1, 4.2, 4.3, 4.4: all seven metrics recorded with value + ts + pair_id.
    tracker, repo = make_tracker()
    snap = make_snapshot(
        liquidity=Decimal("1000"),
        market_cap=Decimal("5000"),
        fdv=Decimal("9000"),
        buy_count=7,
        sell_count=4,
        buy_volume=Decimal("210"),
        sell_volume=Decimal("90"),
    )
    result = tracker.record(snap)

    by_kind = {e.kind: e for e in result.entries}
    assert set(by_kind) == ALL_KINDS

    # Second-level precision timestamp and correct pair_id on every entry.
    assert all(e.pair_id == PAIR_ID for e in result.entries)
    assert all(e.recorded_at.microsecond == 0 for e in result.entries)

    # Req 4.1 refresh values.
    assert by_kind[MetricKind.LIQUIDITY].value == Decimal("1000")
    assert by_kind[MetricKind.MARKET_CAP].value == Decimal("5000")
    assert by_kind[MetricKind.FDV].value == Decimal("9000")
    # Req 4.2 counts.
    assert by_kind[MetricKind.BUY_COUNT].value == Decimal(7)
    assert by_kind[MetricKind.SELL_COUNT].value == Decimal(4)
    # Req 4.3 volumes in quote asset.
    assert by_kind[MetricKind.BUY_VOLUME].value == Decimal("210")
    assert by_kind[MetricKind.SELL_VOLUME].value == Decimal("90")

    assert len(repo.all_entries(PAIR_ID)) == len(ALL_KINDS)


def test_record_truncates_subsecond_timestamp_to_seconds():
    # Req 4.4: timestamps stored to second-level precision.
    tracker, _ = make_tracker()
    sub = NOW.replace(microsecond=123_456) + timedelta(seconds=5)
    result = tracker.record(make_snapshot(fetched_at=sub))
    assert all(e.recorded_at.microsecond == 0 for e in result.entries)
    assert all(e.recorded_at == sub.replace(microsecond=0) for e in result.entries)


def test_record_missing_value_records_sentinel_and_continues():
    # Req 4.10: unavailable value recorded as MISSING; other metrics still recorded.
    tracker, _ = make_tracker()
    result = tracker.record(make_snapshot(), missing={MetricKind.LIQUIDITY})
    by_kind = {e.kind: e for e in result.entries}
    assert by_kind[MetricKind.LIQUIDITY].value is MISSING
    # Subsequent interval still tracked.
    later = tracker.record(make_snapshot(fetched_at=NOW + timedelta(seconds=30)))
    assert {e.kind for e in later.entries} == ALL_KINDS


def test_record_refresh_only_and_period_only_cadences():
    # Req 4.1 (refresh) and Req 4.2/4.3 (measurement period) on distinct cadences.
    tracker, _ = make_tracker()
    refresh = tracker.record(make_snapshot(), refresh=True, period=False)
    assert {e.kind for e in refresh.entries} == REFRESH_KINDS

    period = tracker.record(
        make_snapshot(fetched_at=NOW + timedelta(seconds=60)),
        refresh=False,
        period=True,
    )
    assert {e.kind for e in period.entries} == PERIOD_KINDS


def test_record_captures_audit_info_when_available():
    # Req 4.5: record audit provider/result/date when security metadata available.
    audit = AuditInfo(
        provider=PRIMARY_AUDIT_PROVIDER,
        result="no critical authorities",
        audit_date=date(2025, 1, 1),
    )
    tracker, _ = make_tracker()
    result = tracker.record(make_snapshot(audit=audit))
    assert result.audit == audit
    assert tracker.latest_audit(PAIR_ID) == audit


def test_record_leaves_audit_null_when_no_security_metadata():
    # Req 4.5: field omitted (None) when no security metadata is available.
    tracker, _ = make_tracker()
    result = tracker.record(make_snapshot(audit=None))
    assert result.audit is None
    assert tracker.latest_audit(PAIR_ID) is None


def test_build_audit_info_provider_labels_and_null_clarification():
    # Design "Audit field clarification (Req 4.5)": provider labels + null case.
    primary = build_audit_info("ok", date(2025, 1, 1))
    assert primary is not None
    assert primary.provider == PRIMARY_AUDIT_PROVIDER

    fallback = build_audit_info("ok", date(2025, 1, 1), from_fallback=True)
    assert fallback is not None
    assert fallback.provider == FALLBACK_AUDIT_PROVIDER

    assert build_audit_info(None, date(2025, 1, 1)) is None
    assert build_audit_info("ok", None) is None


def test_query_history_not_monitored_returns_error_without_mutation():
    # Req 4.8: querying an unmonitored pair returns NOT_MONITORED, no mutation.
    tracker, repo = make_tracker()
    result = tracker.query_history("unknown-pair", NOW, NOW + timedelta(hours=1))
    assert result.is_err()
    assert isinstance(result.error, NotFound)
    assert repo.all_entries("unknown-pair") == []


def test_query_history_empty_range_returns_empty_ok():
    # Req 4.9: monitored pair with no entries in range -> empty Ok, no error.
    tracker, _ = make_tracker()
    tracker.record(make_snapshot(fetched_at=NOW))
    far_start = NOW + timedelta(days=10)
    far_end = NOW + timedelta(days=11)
    result = tracker.query_history(PAIR_ID, far_start, far_end)
    assert result.is_ok()
    assert result.value == []


def test_query_history_inclusive_bounds():
    # Req 4.6: range is inclusive of both bounds.
    tracker, _ = make_tracker()
    tracker.record(make_snapshot(fetched_at=NOW))
    tracker.record(make_snapshot(fetched_at=NOW + timedelta(seconds=60)))
    result = tracker.query_history(PAIR_ID, NOW, NOW + timedelta(seconds=60))
    assert result.is_ok()
    timestamps = {e.recorded_at for e in result.value}
    assert timestamps == {NOW, NOW + timedelta(seconds=60)}
