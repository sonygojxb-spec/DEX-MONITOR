"""Tests for the Notifier (Task 17, Action layer).

Covers the design's Correctness Properties for alerting:

* Property 26 - bounded retry with recorded final status (17.2, Req 5.8, 8.4,
  8.5);
* Property 27 - alerts are dispatched to every enabled channel (17.3, Req 8.3,
  8.5);
* Property 28 - quiet-hours suppression preserves Critical and held-position
  Exit_Signal alerts (17.4, Req 8.6);

plus a unit test for order-confirmation message content (17.5, Req 8.1).

All notification channels are in-memory fakes - no real network calls - and the
retry-interval wait is an injected, recording no-op so the property tests run at
>=100 iterations without any real elapsed time.
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.errors import ProviderError, TimedOut
from dex_agent.models import OrderKind, Severity, TimeWindow
from dex_agent.notify import (
    MAX_EXIT_ALERT_RETRIES,
    MIN_EXIT_ALERT_RETRIES,
    Notifier,
    build_confirmation_alert,
)
from dex_agent.providers.interfaces import Alert, DeliveryResult, NotificationChannel
from dex_agent.result import Err, Ok, Result

FIXED_NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Test channels + helpers
# ---------------------------------------------------------------------------


class CountingChannel(NotificationChannel):
    """A channel that fails its first ``fail_count`` attempts, then succeeds.

    ``fail_count = None`` (the default) means it always fails. Records the number
    of ``deliver`` calls so attempt-bounding can be asserted directly.
    """

    def __init__(self, *, name: str, fail_count: int | None = None, error=None) -> None:
        self.name = name
        self._fail_count = fail_count
        self._error = error or ProviderError("delivery failed", provider=name)
        self.calls = 0
        self.delivered: list[Alert] = []

    def deliver(self, alert: Alert) -> Result[DeliveryResult]:
        self.calls += 1
        if self._fail_count is None or self.calls <= self._fail_count:
            return Err(self._error)
        self.delivered.append(alert)
        return Ok(DeliveryResult(channel=self.name, delivered=True))


class RecordingSleep:
    """An injected sleep seam that records waits instead of sleeping."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


def fixed_clock(moment: datetime):
    return lambda: moment


# Strategies ----------------------------------------------------------------

severities = st.sampled_from(list(Severity))


def alerts(
    *,
    severity=severities,
    is_exit=st.booleans(),
    pair_id=st.sampled_from(["pairA", "pairB", "pairC", None]),
) -> st.SearchStrategy[Alert]:
    return st.builds(
        Alert,
        title=st.text(min_size=0, max_size=20),
        body=st.text(min_size=0, max_size=20),
        severity=severity,
        pair_id=pair_id,
        is_exit_signal=is_exit,
    )


# ---------------------------------------------------------------------------
# Property 26: Bounded retry with recorded final status
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 26: Bounded retry with recorded final status
@settings(max_examples=100)
@given(
    alert=alerts(),
    exit_retries=st.integers(min_value=MIN_EXIT_ALERT_RETRIES, max_value=MAX_EXIT_ALERT_RETRIES),
)
def test_property_26_always_failing_channel_is_bounded_and_undelivered(alert, exit_retries):
    """A channel that always fails stops at the budget and records undelivered.

    Validates Req 5.8 (exit-signal retry budget), 8.4 (>=5s spacing, at most 4
    attempts for regular alerts), and 8.5 (undelivered iff every attempt failed).
    """
    channel = CountingChannel(name="always-fail", fail_count=None)
    sleep = RecordingSleep()
    notifier = Notifier(
        channels=[channel],
        exit_alert_retries=exit_retries,
        clock=fixed_clock(FIXED_NOW),
        sleep=sleep,
    )

    result = notifier.send(alert)

    expected_max = 1 + exit_retries if alert.is_exit_signal else 4
    assert notifier.max_attempts(alert) == expected_max
    # At most the allowed maximum, and (always-failing) exactly the maximum.
    assert channel.calls == expected_max
    [record] = result.channels
    assert record.attempts == expected_max
    assert record.attempts <= expected_max
    # Final status recorded undelivered iff every attempt failed (they did).
    assert record.delivered is False
    assert result.any_undelivered is True
    assert record.channel in result.undelivered_channels
    # Spacing: exactly one wait between consecutive attempts, each >= 5s.
    assert len(sleep.waits) == expected_max - 1
    assert all(w >= 5.0 for w in sleep.waits)


# Feature: dex-trading-agent, Property 26: Bounded retry with recorded final status
@settings(max_examples=100)
@given(
    alert=alerts(),
    exit_retries=st.integers(min_value=MIN_EXIT_ALERT_RETRIES, max_value=MAX_EXIT_ALERT_RETRIES),
    fail_first=st.integers(min_value=0, max_value=MAX_EXIT_ALERT_RETRIES),
)
def test_property_26_recovers_within_budget_records_delivered(alert, exit_retries, fail_first):
    """k<max failures then a success -> delivered, attempts == k+1, bounded.

    Validates Req 5.8/8.4/8.5: the final status is delivered (not undelivered)
    iff some attempt succeeded, and attempts never exceed the budget.
    """
    max_attempts = 1 + exit_retries if alert.is_exit_signal else 4
    # Constrain failures so a success is reachable within the budget.
    fail_count = min(fail_first, max_attempts - 1)
    channel = CountingChannel(name="recovers", fail_count=fail_count)
    sleep = RecordingSleep()
    notifier = Notifier(
        channels=[channel],
        exit_alert_retries=exit_retries,
        clock=fixed_clock(FIXED_NOW),
        sleep=sleep,
    )

    result = notifier.send(alert)

    [record] = result.channels
    assert record.attempts == fail_count + 1
    assert record.attempts <= max_attempts
    assert record.delivered is True
    assert result.all_delivered is True
    assert result.any_undelivered is False
    assert len(sleep.waits) == fail_count


# ---------------------------------------------------------------------------
# Property 27: Alerts are dispatched to every enabled channel
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 27: Alerts are dispatched to every enabled channel
@settings(max_examples=100)
@given(
    alert=alerts(is_exit=st.just(False), severity=st.sampled_from(
        [Severity.NONE, Severity.LOW, Severity.MEDIUM, Severity.HIGH]
    )),
    failing=st.lists(st.booleans(), min_size=1, max_size=5),
)
def test_property_27_every_enabled_channel_attempted(alert, failing):
    """Delivery is attempted on every channel; one failure never blocks others.

    Validates Req 8.3 (deliver through every enabled channel) and 8.5 (a
    per-channel failure does not prevent attempts on the other channels). Uses
    non-quiet-hours so no suppression interferes.
    """
    channels = [
        CountingChannel(name=f"ch{i}", fail_count=None if fail else 0)
        for i, fail in enumerate(failing)
    ]
    notifier = Notifier(
        channels=channels,
        clock=fixed_clock(FIXED_NOW),
        sleep=RecordingSleep(),
    )

    result = notifier.send(alert)

    assert result.suppressed is False
    # Every enabled channel was attempted at least once.
    assert len(result.channels) == len(channels)
    for ch in channels:
        assert ch.calls >= 1
    # Per-channel outcome matches the scripted behaviour: failing channels are
    # undelivered, others delivered - failures did not block the rest.
    for ch, fail, record in zip(channels, failing, result.channels):
        assert record.delivered is (not fail)
        if not fail:
            assert alert in ch.delivered


# ---------------------------------------------------------------------------
# Property 28: Quiet-hours suppression preserves Critical and held exits
# ---------------------------------------------------------------------------

# A quiet-hours window covering the whole day so FIXED_NOW is always inside it.
ALL_DAY_QUIET = TimeWindow(start=time(0, 0, 0), end=time(23, 59, 59))


# Feature: dex-trading-agent, Property 28: Quiet-hours suppression preserves Critical and held-position Exit_Signal alerts
@settings(max_examples=100)
@given(alert=alerts(), held_pairs=st.sets(st.sampled_from(["pairA", "pairB", "pairC"])))
def test_property_28_quiet_hours_suppression(alert, held_pairs):
    """During quiet hours, deliver iff Critical OR held-position Exit_Signal.

    Validates Req 8.6: all other non-Critical alerts are suppressed; Critical
    and held-position Exit_Signal alerts are always delivered.
    """
    channel = CountingChannel(name="ch", fail_count=0)
    notifier = Notifier(
        channels=[channel],
        position_held=lambda pair: pair in held_pairs,
        quiet_hours=ALL_DAY_QUIET,
        clock=fixed_clock(FIXED_NOW),
        sleep=RecordingSleep(),
    )

    assert notifier.in_quiet_hours(FIXED_NOW) is True
    result = notifier.send(alert)

    should_deliver = (alert.severity == Severity.CRITICAL) or (
        alert.is_exit_signal and alert.pair_id in held_pairs
    )

    if should_deliver:
        assert result.suppressed is False
        assert result.all_delivered is True
        assert channel.calls >= 1
    else:
        assert result.suppressed is True
        assert result.channels == ()
        assert channel.calls == 0


# Feature: dex-trading-agent, Property 28: Quiet-hours suppression preserves Critical and held-position Exit_Signal alerts
@settings(max_examples=100)
@given(alert=alerts())
def test_property_28_outside_quiet_hours_never_suppressed(alert):
    """Outside the quiet-hours window every alert is dispatched (Req 8.6)."""
    channel = CountingChannel(name="ch", fail_count=0)
    # No quiet-hours configured -> never suppressed.
    notifier = Notifier(
        channels=[channel],
        clock=fixed_clock(FIXED_NOW),
        sleep=RecordingSleep(),
    )

    assert notifier.in_quiet_hours(FIXED_NOW) is False
    result = notifier.send(alert)

    assert result.suppressed is False
    assert result.all_delivered is True


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_confirmation_message_content():
    """Confirmation message contains pair, order type, executed price, qty (8.1)."""
    alert = build_confirmation_alert(
        pair_id="SOL/USDC",
        order_kind=OrderKind.BUY,
        executed_price=Decimal("1.2345"),
        quantity=Decimal("100"),
    )

    assert alert.is_exit_signal is False
    assert alert.severity == Severity.NONE
    assert alert.pair_id == "SOL/USDC"
    # All four required fields present in the rendered content (title + body).
    content = f"{alert.title}\n{alert.body}"
    assert "SOL/USDC" in content       # Trading_Pair
    assert "BUY" in content            # order type
    assert "1.2345" in content         # executed price
    assert "100" in content            # quantity


def test_sell_confirmation_message_content():
    """A sell confirmation renders the SELL order type and its fields (8.1)."""
    alert = build_confirmation_alert(
        pair_id="BONK/SOL",
        order_kind=OrderKind.SELL,
        executed_price=Decimal("0.00042"),
        quantity=Decimal("5000"),
    )
    content = f"{alert.title}\n{alert.body}"
    assert "BONK/SOL" in content
    assert "SELL" in content
    assert "0.00042" in content
    assert "5000" in content


def test_undelivered_does_not_block_other_channels_unit():
    """An always-failing channel is recorded undelivered while others deliver."""
    bad = CountingChannel(name="bad", fail_count=None, error=TimedOut("no ack"))
    good = CountingChannel(name="good", fail_count=0)
    notifier = Notifier(
        channels=[bad, good],
        clock=fixed_clock(FIXED_NOW),
        sleep=RecordingSleep(),
    )

    result = notifier.send(Alert(title="t", body="b", severity=Severity.HIGH))

    assert result.undelivered_channels == ("bad",)
    assert any(c.channel == "good" and c.delivered for c in result.channels)
    assert good.calls == 1
    assert bad.calls == 4  # 1 + 3 retries (Req 8.4)


def test_exit_alert_retries_out_of_range_rejected():
    """The exit-signal retry budget is validated to [1, 10] (Req 5.8)."""
    import pytest

    with pytest.raises(ValueError):
        Notifier(channels=[], exit_alert_retries=0)
    with pytest.raises(ValueError):
        Notifier(channels=[], exit_alert_retries=11)
