"""Unit tests for the Authorization_Manager (Task 14.2).

Covers the wallet connect/verify path, the trading-enabled gate, revocation,
and the status-change recording contract:

* default ``trading_enabled()`` is ``False`` (Req 11.3);
* a successful, in-bound verification enables trading and records an ``ENABLED``
  status change with a timestamp (Req 11.1, 11.6);
* a failed verification stays monitoring-only, surfaces an error, and records a
  ``FAILED`` status change (Req 11.2, 11.6);
* a verification that exceeds the 5s bound is treated as a timeout: stays
  monitoring-only, surfaces ``TimedOut``, records ``FAILED`` (Req 11.2);
* revocation disables trading, retains monitoring, and records ``REVOKED``
  (Req 11.4, 11.5, 11.6);
* every status change is timestamped and persisted (Req 11.6).

Validates Requirements 11.1-11.6 (Task 14.2 focus: 11.5, 11.6).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from dex_agent.control import AuthorizationManager
from dex_agent.errors import ProviderError, TimedOut, Unverified
from dex_agent.models import AuthStatus
from dex_agent.repositories import InMemoryAuthorizationRepository
from dex_agent.result import Err, Ok

WALLET = "wallet-1"


# ---------------------------------------------------------------------------
# Test doubles: deterministic clocks and a scriptable verifier seam.
# ---------------------------------------------------------------------------


def seq_monotonic(values):
    """A monotonic clock that yields successive ``values`` (repeating the last).

    ``connect_wallet`` reads the monotonic clock twice (start, then after the
    verifier), so a two-element list ``[t0, t1]`` yields ``elapsed == t1 - t0``.
    """
    state = {"i": 0}

    def _clock() -> float:
        i = state["i"]
        if i < len(values):
            state["i"] = i + 1
            return float(values[i])
        return float(values[-1])

    return _clock


def ticking_wall_clock(start: datetime | None = None, step_s: float = 1.0):
    """A wall clock returning strictly increasing UTC datetimes on each call."""
    base = start or datetime(2024, 1, 1, tzinfo=timezone.utc)
    state = {"n": 0}

    def _clock() -> datetime:
        dt = base + timedelta(seconds=step_s * state["n"])
        state["n"] += 1
        return dt

    return _clock


def ok_verifier(_wallet_id):
    return Ok(None)


def err_verifier(_wallet_id):
    return Err(Unverified("rejected", subject=_wallet_id))


def make_manager(
    *,
    verifier=ok_verifier,
    monotonic=None,
    clock=None,
    bound_s=5.0,
    repo=None,
):
    repo = repo or InMemoryAuthorizationRepository()
    return (
        AuthorizationManager(
            repo,
            verifier,
            clock=clock or ticking_wall_clock(),
            monotonic=monotonic or seq_monotonic([0.0, 0.1]),
            bound_s=bound_s,
        ),
        repo,
    )


# ---------------------------------------------------------------------------
# Default gate (Req 11.3)
# ---------------------------------------------------------------------------


def test_trading_disabled_by_default():
    mgr, repo = make_manager()
    assert mgr.trading_enabled() is False
    assert mgr.authorized_wallet is None
    # No status change has occurred, so nothing is persisted yet.
    assert repo.history(WALLET) == []


def test_monitoring_active_by_default():
    mgr, _ = make_manager()
    assert mgr.monitoring_active is True


# ---------------------------------------------------------------------------
# Successful connect (Req 11.1, 11.6)
# ---------------------------------------------------------------------------


def test_successful_connect_enables_trading():
    mgr, _ = make_manager(monotonic=seq_monotonic([0.0, 0.5]))
    result = mgr.connect_wallet(WALLET)

    assert isinstance(result, Ok)
    assert mgr.trading_enabled() is True
    assert mgr.authorized_wallet == WALLET


def test_successful_connect_records_enabled_with_timestamp():
    ts = datetime(2024, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    mgr, repo = make_manager(
        monotonic=seq_monotonic([0.0, 0.1]),
        clock=ticking_wall_clock(start=ts, step_s=1.0),
    )

    result = mgr.connect_wallet(WALLET)

    record = result.value
    assert record.status is AuthStatus.ENABLED
    assert record.wallet_id == WALLET
    assert record.changed_at == ts
    assert record.changed_at.tzinfo is not None
    # Persisted exactly once.
    history = repo.history(WALLET)
    assert [r.status for r in history] == [AuthStatus.ENABLED]


# ---------------------------------------------------------------------------
# Failed verification (Req 11.2, 11.6)
# ---------------------------------------------------------------------------


def test_failed_verification_stays_monitoring_only_and_surfaces_error():
    mgr, repo = make_manager(verifier=err_verifier)

    result = mgr.connect_wallet(WALLET)

    assert isinstance(result, Err)
    assert isinstance(result.error, Unverified)
    # Trading not enabled; remains in monitoring-only mode.
    assert mgr.trading_enabled() is False
    assert mgr.authorized_wallet is None
    assert mgr.monitoring_active is True
    # FAILED status change still recorded with a timestamp.
    history = repo.history(WALLET)
    assert [r.status for r in history] == [AuthStatus.FAILED]
    assert history[0].changed_at.tzinfo is not None


def test_failed_verification_surfaces_provider_error_from_seam():
    def provider_err_verifier(_wallet_id):
        return Err(ProviderError(detail="rpc down", provider="wallet_verifier"))

    mgr, _ = make_manager(verifier=provider_err_verifier)
    result = mgr.connect_wallet(WALLET)

    assert isinstance(result, Err)
    assert isinstance(result.error, ProviderError)


def test_verifier_exception_is_treated_as_failure():
    def boom_verifier(_wallet_id):
        raise RuntimeError("seam blew up")

    mgr, repo = make_manager(verifier=boom_verifier)
    result = mgr.connect_wallet(WALLET)

    assert isinstance(result, Err)
    assert isinstance(result.error, ProviderError)
    assert mgr.trading_enabled() is False
    assert [r.status for r in repo.history(WALLET)] == [AuthStatus.FAILED]


# ---------------------------------------------------------------------------
# Timeout handling (Req 11.2) - elapsed exceeds the 5s bound
# ---------------------------------------------------------------------------


def test_verification_timeout_stays_monitoring_only():
    # Verifier "succeeds" but takes 6s > 5s bound -> treated as a timeout.
    mgr, repo = make_manager(
        verifier=ok_verifier,
        monotonic=seq_monotonic([0.0, 6.0]),
        bound_s=5.0,
    )

    result = mgr.connect_wallet(WALLET)

    assert isinstance(result, Err)
    assert isinstance(result.error, TimedOut)
    assert result.error.timeout_s == 5.0
    assert mgr.trading_enabled() is False
    assert [r.status for r in repo.history(WALLET)] == [AuthStatus.FAILED]


def test_verification_exactly_at_bound_succeeds():
    # Elapsed == bound is within the bound (not a timeout).
    mgr, _ = make_manager(
        verifier=ok_verifier,
        monotonic=seq_monotonic([0.0, 5.0]),
        bound_s=5.0,
    )

    result = mgr.connect_wallet(WALLET)

    assert isinstance(result, Ok)
    assert mgr.trading_enabled() is True


# ---------------------------------------------------------------------------
# Revocation (Req 11.4, 11.5, 11.6)
# ---------------------------------------------------------------------------


def test_revoke_disables_trading_retains_monitoring_records_revoked():
    mgr, repo = make_manager()
    mgr.connect_wallet(WALLET)
    assert mgr.trading_enabled() is True

    result = mgr.revoke()

    assert isinstance(result, Ok)
    assert result.value.status is AuthStatus.REVOKED
    assert result.value.wallet_id == WALLET
    assert result.value.changed_at.tzinfo is not None
    # Trading disabled, authorization cleared.
    assert mgr.trading_enabled() is False
    assert mgr.authorized_wallet is None
    # Monitoring retained (Req 11.5).
    assert mgr.monitoring_active is True


def test_revoke_without_authorized_wallet_records_nothing():
    mgr, repo = make_manager()

    result = mgr.revoke()

    assert isinstance(result, Err)
    assert isinstance(result.error, Unverified)
    assert mgr.trading_enabled() is False
    # No status change occurred, so nothing is persisted.
    assert repo.history(WALLET) == []


# ---------------------------------------------------------------------------
# Every status change is timestamped and persisted, in order (Req 11.6)
# ---------------------------------------------------------------------------


def test_all_status_changes_recorded_in_order_with_timestamps():
    repo = InMemoryAuthorizationRepository()
    clock = ticking_wall_clock(
        start=datetime(2024, 1, 1, tzinfo=timezone.utc), step_s=10.0
    )
    mgr = AuthorizationManager(
        repo,
        ok_verifier,
        clock=clock,
        monotonic=seq_monotonic([0.0, 0.1]),
    )

    # ENABLED -> REVOKED -> (reconnect) ENABLED
    mgr.connect_wallet(WALLET)
    mgr.revoke()
    mgr.connect_wallet(WALLET)

    history = repo.history(WALLET)
    assert [r.status for r in history] == [
        AuthStatus.ENABLED,
        AuthStatus.REVOKED,
        AuthStatus.ENABLED,
    ]
    # Each record carries a tz-aware timestamp and they are strictly ascending.
    times = [r.changed_at for r in history]
    assert all(t.tzinfo is not None for t in times)
    assert times == sorted(times)
    assert len(set(times)) == len(times)


def test_failed_then_successful_connect_records_both_changes():
    repo = InMemoryAuthorizationRepository()
    clock = ticking_wall_clock(step_s=5.0)
    state = {"ok": False}

    def flaky_verifier(_wallet_id):
        return Ok(None) if state["ok"] else Err(Unverified("nope"))

    mgr = AuthorizationManager(
        repo,
        flaky_verifier,
        clock=clock,
        monotonic=seq_monotonic([0.0, 0.1]),
    )

    first = mgr.connect_wallet(WALLET)
    assert isinstance(first, Err)
    assert mgr.trading_enabled() is False

    state["ok"] = True
    second = mgr.connect_wallet(WALLET)
    assert isinstance(second, Ok)
    assert mgr.trading_enabled() is True

    assert [r.status for r in repo.history(WALLET)] == [
        AuthStatus.FAILED,
        AuthStatus.ENABLED,
    ]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
