"""Tests for the Audit / persistence service (Task 10).

Covers:

* Property 15 - retention deletes exactly the records older than the period
  (subtask 10.2, Req 10.5, 10.6);
* unit tests for audit-record content/precision and the persistence-failure
  record (subtask 10.3, Req 10.1, 10.7);

plus supporting unit tests for the range query (Req 10.2-10.4) which the audit
query shares with the Metrics_Tracker (Properties 13/14).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.audit import (
    MAX_RETRIES,
    RETENTION_DAYS_DEFAULT,
    AuditService,
)
from dex_agent.errors import InvalidRange
from dex_agent.models import ActionType, AuditRecord
from dex_agent.repositories import InMemoryAuditRepository

# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
PAIR_ID = "pair-1"

# Action types that audit records can carry for completed actions (Req 10.1).
ACTION_TYPES = [
    ActionType.SECURITY_INSPECTION,
    ActionType.WALLET_ANALYSIS,
    ActionType.SIGNAL_COMPUTATION,
    ActionType.TRADE_EXECUTION,
]


def make_service(**kwargs) -> tuple[AuditService, InMemoryAuditRepository]:
    repo = InMemoryAuditRepository()
    return AuditService(repo, **kwargs), repo


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Distinct second-offsets so each record lands on its own timestamp (the repo is
# idempotent on (action_type, pair_id, timestamp)).
offsets_st = st.lists(
    st.integers(min_value=0, max_value=4_000 * 86_400),  # up to ~4000 days span
    min_size=0,
    max_size=20,
    unique=True,
)

retention_days_st = st.integers(min_value=30, max_value=3650)


# ---------------------------------------------------------------------------
# Property 15 - retention deletes exactly records older than the period
# (subtask 10.2, Req 10.5, 10.6)
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    offsets=offsets_st,
    retention_days=retention_days_st,
    now_offset_days=st.integers(min_value=0, max_value=4_000),
)
def test_property_15_retention_deletes_exactly_older_than_period(
    offsets, retention_days, now_offset_days
):
    # Feature: dex-trading-agent, Property 15: Retention deletes exactly the records older than the period
    service, repo = make_service(retention_days=retention_days)
    base = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Persist one record per distinct offset, cycling action types so the
    # idempotency key (action_type, pair_id, ts) stays unique per timestamp.
    for i, off in enumerate(offsets):
        ts = base + timedelta(seconds=off)
        service.record(
            ACTION_TYPES[i % len(ACTION_TYPES)],
            PAIR_ID,
            outcome=f"outcome-{i}",
            recorded_at=ts,
        )

    now = base + timedelta(days=now_offset_days)
    boundary = now - timedelta(days=retention_days)

    before = repo.all_records(PAIR_ID)
    # Expected partition, computed independently from the service under test.
    expected_deleted = sorted(
        (r for r in before if r.recorded_at < boundary),
        key=lambda r: r.recorded_at,
    )
    expected_kept = [r for r in before if r.recorded_at >= boundary]

    deleted = service.enforce_retention(now=now)

    # Deleted set is EXACTLY the records strictly older than the boundary.
    assert deleted == expected_deleted
    # A record exactly at the boundary is within retention and is NOT deleted.
    assert all(r.recorded_at < boundary for r in deleted)
    # Survivors are exactly the records whose age does not exceed the period.
    remaining = repo.all_records(PAIR_ID)
    assert sorted(remaining, key=lambda r: r.recorded_at) == sorted(
        expected_kept, key=lambda r: r.recorded_at
    )
    assert all(r.recorded_at >= boundary for r in remaining)


# ---------------------------------------------------------------------------
# Unit tests - audit record content/precision (subtask 10.3, Req 10.1)
# ---------------------------------------------------------------------------


def test_record_builds_record_with_required_fields():
    # Req 10.1: record carries action type, pair, outcome, millisecond UTC ts.
    service, repo = make_service()
    outcome = service.record(
        ActionType.TRADE_EXECUTION, PAIR_ID, "filled", recorded_at=NOW
    )
    rec = outcome.record
    assert rec.action_type == ActionType.TRADE_EXECUTION
    assert rec.pair_id == PAIR_ID
    assert rec.outcome == "filled"
    assert rec.recorded_at == NOW
    # Persisted to the repository.
    assert repo.all_records(PAIR_ID) == [rec]
    assert outcome.persisted is True
    assert outcome.attempts == 1
    assert outcome.failure_record is None


def test_record_timestamp_is_millisecond_precision():
    # Req 10.1: timestamp has millisecond precision (sub-millisecond truncated).
    service, _ = make_service()
    sub = NOW.replace(microsecond=123_456)
    outcome = service.record(
        ActionType.SECURITY_INSPECTION, PAIR_ID, "ok", recorded_at=sub
    )
    # 123_456 microseconds -> truncated to 123 ms -> 123_000 microseconds.
    assert outcome.record.recorded_at.microsecond == 123_000
    assert outcome.record.recorded_at.tzinfo == timezone.utc


def test_record_default_timestamp_is_recent_and_millis_precision():
    # Req 10.1: default timestamp is "now" (within 5s) at millisecond precision.
    service, _ = make_service()
    outcome = service.record(ActionType.WALLET_ANALYSIS, PAIR_ID, "done")
    delta = abs((datetime.now(timezone.utc) - outcome.record.recorded_at).total_seconds())
    assert delta < 5.0
    assert outcome.record.recorded_at.microsecond % 1000 == 0


# ---------------------------------------------------------------------------
# Unit tests - persistence-failure record (subtask 10.3, Req 10.7)
# ---------------------------------------------------------------------------


def test_record_retries_then_writes_persistence_failure_when_all_fail():
    # Req 10.7: retry up to 3 times; if all fail, persist a PERSISTENCE_FAILURE
    # record naming the failed action type and continue operating.
    attempts = {"n": 0}

    def always_fail(_record: AuditRecord) -> bool:
        attempts["n"] += 1
        return False

    service, repo = make_service(persist=always_fail)
    outcome = service.record(ActionType.TRADE_EXECUTION, PAIR_ID, "submit")

    # Initial attempt + MAX_RETRIES retries = MAX_RETRIES + 1 total attempts.
    assert attempts["n"] == MAX_RETRIES + 1
    assert outcome.attempts == MAX_RETRIES + 1
    assert outcome.persisted is False

    # A persistence-failure marker was written naming the failed action type.
    assert outcome.failure_record is not None
    failure = outcome.failure_record
    assert failure.action_type == ActionType.PERSISTENCE_FAILURE
    assert failure.pair_id == PAIR_ID
    assert ActionType.TRADE_EXECUTION.value in failure.outcome

    # The marker is durably recorded; the original (failed) record is not stored.
    stored = repo.all_records(PAIR_ID)
    assert failure in stored
    assert all(r.action_type == ActionType.PERSISTENCE_FAILURE for r in stored)


def test_record_succeeds_after_transient_failures_within_retry_budget():
    # Req 10.7: a record that succeeds on a retry is persisted, no failure marker.
    calls = {"n": 0}

    def fail_twice_then_succeed(record: AuditRecord) -> bool:
        calls["n"] += 1
        if calls["n"] <= 2:
            return False
        # 3rd attempt succeeds: store it.
        repo_ref.append(record)
        return True

    repo_ref = InMemoryAuditRepository()
    service = AuditService(repo_ref, persist=fail_twice_then_succeed)
    outcome = service.record(ActionType.SIGNAL_COMPUTATION, PAIR_ID, "eligible")

    assert outcome.persisted is True
    assert outcome.attempts == 3
    assert outcome.failure_record is None
    stored = repo_ref.all_records(PAIR_ID)
    assert len(stored) == 1
    assert stored[0].action_type == ActionType.SIGNAL_COMPUTATION


# ---------------------------------------------------------------------------
# Unit tests - range query (Req 10.2, 10.3, 10.4) shared with metrics
# ---------------------------------------------------------------------------


def test_query_returns_in_range_ascending():
    # Req 10.2: return records within inclusive range, oldest-to-newest.
    service, _ = make_service()
    for off in (0, 60, 120, 180):
        service.record(
            ActionType.SECURITY_INSPECTION,
            PAIR_ID,
            f"o-{off}",
            recorded_at=NOW + timedelta(seconds=off),
        )
    result = service.query(
        PAIR_ID, NOW + timedelta(seconds=60), NOW + timedelta(seconds=120)
    )
    assert result.is_ok()
    times = [r.recorded_at for r in result.value]
    assert times == [NOW + timedelta(seconds=60), NOW + timedelta(seconds=120)]


def test_query_empty_range_returns_empty_ok():
    # Req 10.3: no records in range -> empty result set without error.
    service, _ = make_service()
    service.record(ActionType.WALLET_ANALYSIS, PAIR_ID, "x", recorded_at=NOW)
    result = service.query(
        PAIR_ID, NOW + timedelta(days=1), NOW + timedelta(days=2)
    )
    assert result.is_ok()
    assert result.value == []


def test_query_unknown_pair_returns_empty_ok():
    # Req 10.3: no persisted records for the pair -> empty set without error.
    service, _ = make_service()
    result = service.query("nope", NOW, NOW + timedelta(hours=1))
    assert result.is_ok()
    assert result.value == []


def test_query_inverted_range_rejected_without_mutation():
    # Req 10.4: inverted range rejected with invalid-time-range result.
    service, repo = make_service()
    service.record(ActionType.TRADE_EXECUTION, PAIR_ID, "x", recorded_at=NOW)
    before = repo.all_records(PAIR_ID)
    result = service.query(PAIR_ID, NOW + timedelta(seconds=10), NOW)
    assert result.is_err()
    assert isinstance(result.error, InvalidRange)
    assert repo.all_records(PAIR_ID) == before


# ---------------------------------------------------------------------------
# Unit tests - retention configuration bounds (Req 10.5)
# ---------------------------------------------------------------------------


def test_default_retention_is_30_days():
    service, _ = make_service()
    assert service.retention_days == RETENTION_DAYS_DEFAULT == 30


@pytest.mark.parametrize("days", [29, 0, 3651, 10_000])
def test_out_of_range_retention_rejected(days):
    with pytest.raises(ValueError):
        make_service(retention_days=days)


@pytest.mark.parametrize("days", [30, 365, 3650])
def test_in_range_retention_accepted(days):
    service, _ = make_service(retention_days=days)
    assert service.retention_days == days
