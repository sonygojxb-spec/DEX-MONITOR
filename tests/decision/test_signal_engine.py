"""Tests for the Signal_Engine (Task 12).

Covers the design's Correctness Properties for entry/exit signals:

* Property 16 - entry eligibility predicate (subtask 12.3, Req 5.2);
* Property 17 - rug-pull exit predicate (subtask 12.4, Req 5.3);
* Property 18 - dump exit predicate (subtask 12.5, Req 5.4);

plus unit tests for the recorded signal content (Req 5.6) and the
skip-on-stale/missing-metrics path (Req 5.7) (subtask 12.6).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.decision import (
    SignalEngine,
    SignalInputs,
    is_dump,
    is_eligible,
    is_rug_pull,
    liquidity_drop_pct,
)
from dex_agent.models import (
    MISSING,
    Configuration,
    ExitClass,
    Severity,
    SignalType,
)
from dex_agent.providers.interfaces import Alert
from dex_agent.repositories import InMemorySignalRepository

# ---------------------------------------------------------------------------
# Builders / strategies
# ---------------------------------------------------------------------------

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
PAIR_ID = "pair-1"

# A bounded, finite Decimal strategy suitable for percentages / volumes.
pct = st.decimals(
    min_value=Decimal(0),
    max_value=Decimal(100),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
non_negative = st.decimals(
    min_value=Decimal(0),
    max_value=Decimal("1000000"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
positive = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("1000000"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
severities = st.sampled_from(list(Severity))


def make_config(
    *,
    entry_threshold: Decimal = Decimal(50),
    rugpull_threshold: Decimal = Decimal(30),
    dump_threshold: Decimal = Decimal(2),
) -> Configuration:
    return Configuration(
        discovery_scan_interval_s=60,
        measurement_period_s=300,
        bot_pct_threshold=Decimal(50),
        holder_conc_threshold=Decimal(50),
        rugpull_threshold=rugpull_threshold,
        dump_threshold=dump_threshold,
        entry_threshold=entry_threshold,
        slippage_tolerance=Decimal(1),
    )


def make_engine(
    *,
    config: Configuration | None = None,
    max_severity: Severity = Severity.MEDIUM,
    position_held=None,
    alert_sink=None,
):
    repo = InMemorySignalRepository()
    engine = SignalEngine(
        repo,
        config or make_config(),
        max_severity=max_severity,
        position_held=position_held,
        alert_sink=alert_sink,
        clock=lambda: NOW,
    )
    return engine, repo


def make_inputs(
    *,
    severity: Severity = Severity.NONE,
    bot_pct: Decimal = Decimal(0),
    holder_concentration: Decimal = Decimal(0),
    curr_liquidity=Decimal(1000),
    buy_volume=Decimal(100),
    sell_volume=Decimal(50),
    prev_liquidity=Decimal(1000),
    stale: bool = False,
) -> SignalInputs:
    return SignalInputs(
        pair_id=PAIR_ID,
        severity=severity,
        bot_pct=bot_pct,
        holder_concentration=holder_concentration,
        curr_liquidity=curr_liquidity,
        buy_volume=buy_volume,
        sell_volume=sell_volume,
        prev_liquidity=prev_liquidity,
        stale=stale,
    )


# ---------------------------------------------------------------------------
# Property 16: Entry eligibility predicate (Req 5.2)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 16: Entry eligibility predicate
@settings(max_examples=100)
@given(
    entry_score=pct,
    entry_threshold=pct,
    severity=severities,
    max_severity=severities,
)
def test_property_16_entry_eligibility_predicate(
    entry_score, entry_threshold, severity, max_severity
):
    """Validates: Requirements 5.2.

    Eligible iff ``entry_score >= entry_threshold AND severity <= max_severity``.
    """
    expected = (entry_score >= entry_threshold) and (severity <= max_severity)
    assert (
        is_eligible(
            entry_score,
            severity,
            entry_threshold=entry_threshold,
            max_severity=max_severity,
        )
        is expected
    )


def test_property_16_boundaries():
    """Both sides of each conjunct's boundary (score==threshold, severity==max)."""
    th = Decimal(50)
    # score exactly meets threshold -> satisfies the score conjunct.
    assert is_eligible(th, Severity.LOW, entry_threshold=th, max_severity=Severity.LOW)
    # score just below threshold -> fails.
    assert not is_eligible(
        th - Decimal("0.01"), Severity.LOW, entry_threshold=th, max_severity=Severity.LOW
    )
    # severity exactly at max -> satisfies the severity conjunct.
    assert is_eligible(
        th, Severity.MEDIUM, entry_threshold=th, max_severity=Severity.MEDIUM
    )
    # severity one step above max -> fails.
    assert not is_eligible(
        th, Severity.HIGH, entry_threshold=th, max_severity=Severity.MEDIUM
    )


# ---------------------------------------------------------------------------
# Property 17: Rug-pull exit predicate (Req 5.3)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 17: Rug-pull exit predicate
@settings(max_examples=100)
@given(prev_liquidity=positive, curr_liquidity=non_negative, threshold=pct)
def test_property_17_rug_pull_exit_predicate(prev_liquidity, curr_liquidity, threshold):
    """Validates: Requirements 5.3.

    Rug-pull iff the liquidity drop percentage strictly exceeds the threshold.
    """
    drop = liquidity_drop_pct(prev_liquidity, curr_liquidity)
    expected = drop > threshold
    assert (
        is_rug_pull(
            prev_liquidity, curr_liquidity, rugpull_threshold=threshold
        )
        is expected
    )


def test_property_17_boundaries():
    """A drop exactly at the threshold does not trigger; just above does."""
    prev = Decimal(1000)
    threshold = Decimal(30)
    # Exactly a 30% drop -> not greater than threshold -> no rug-pull.
    assert not is_rug_pull(prev, Decimal(700), rugpull_threshold=threshold)
    # A 30.1% drop -> exceeds threshold -> rug-pull.
    assert is_rug_pull(prev, Decimal(699), rugpull_threshold=threshold)
    # Liquidity increase is never a rug-pull.
    assert not is_rug_pull(prev, Decimal(2000), rugpull_threshold=Decimal(0))


# ---------------------------------------------------------------------------
# Property 18: Dump exit predicate (Req 5.4)
# ---------------------------------------------------------------------------


# Feature: dex-trading-agent, Property 18: Dump exit predicate
@settings(max_examples=100)
@given(buy_volume=non_negative, sell_volume=non_negative, threshold=positive)
def test_property_18_dump_exit_predicate(buy_volume, sell_volume, threshold):
    """Validates: Requirements 5.4.

    Dump iff ``buy_volume > 0`` and ``sell_volume / buy_volume`` strictly
    exceeds the threshold.
    """
    if buy_volume <= 0:
        expected = False
    else:
        expected = sell_volume / buy_volume > threshold
    assert is_dump(buy_volume, sell_volume, dump_threshold=threshold) is expected


def test_property_18_boundaries():
    """A ratio exactly at the threshold does not trigger; above does; zero-buy never does."""
    threshold = Decimal(2)
    # ratio == 2 -> not greater -> no dump.
    assert not is_dump(Decimal(100), Decimal(200), dump_threshold=threshold)
    # ratio == 2.01 -> exceeds -> dump.
    assert is_dump(Decimal(100), Decimal(201), dump_threshold=threshold)
    # buy_volume == 0 -> ratio undefined -> never a dump (even with sells).
    assert not is_dump(Decimal(0), Decimal(500), dump_threshold=threshold)


# ---------------------------------------------------------------------------
# Unit tests: signal record content (Req 5.6) + skip path (Req 5.7)
# ---------------------------------------------------------------------------


def test_records_entry_signal_with_contributing_metrics_and_timestamp():
    """Req 5.6: each generated signal is recorded with metrics + timestamp."""
    engine, repo = make_engine(max_severity=Severity.MEDIUM)
    outcome = engine.compute(
        make_inputs(severity=Severity.LOW, bot_pct=Decimal(10), holder_concentration=Decimal(20))
    )

    assert not outcome.skipped
    assert outcome.entry is not None
    history = repo.history(PAIR_ID)
    entry = next(s for s in history if s.type is SignalType.ENTRY)
    assert entry.generated_at == NOW
    # Contributing metric values are recorded (Req 5.6).
    assert entry.contributing_metrics["severity"] == "LOW"
    assert entry.contributing_metrics["bot_pct"] == Decimal(10)
    assert entry.contributing_metrics["holder_concentration"] == Decimal(20)
    assert "entry_score" in entry.contributing_metrics
    assert entry.contributing_metrics["entry_threshold"] == Decimal(50)


def test_records_rug_pull_exit_signal_with_contributing_metrics():
    """Req 5.3/5.6: a rug-pull exit signal records the contributing liquidity values."""
    engine, repo = make_engine()
    # 50% liquidity drop exceeds the default 30% rug-pull threshold.
    outcome = engine.compute(
        make_inputs(prev_liquidity=Decimal(1000), curr_liquidity=Decimal(500))
    )

    assert outcome.exit is not None
    assert outcome.exit.type is SignalType.EXIT
    assert outcome.exit.exit_class is ExitClass.RUG_PULL
    assert outcome.exit.contributing_metrics["prev_liquidity"] == Decimal(1000)
    assert outcome.exit.contributing_metrics["curr_liquidity"] == Decimal(500)
    assert outcome.exit.contributing_metrics["liquidity_drop_pct"] == Decimal(50)
    assert any(s.type is SignalType.EXIT for s in repo.history(PAIR_ID))


def test_records_dump_exit_when_no_rug_pull():
    """Req 5.4: a dump exit is raised when sell/buy ratio exceeds the threshold."""
    engine, _ = make_engine(config=make_config(dump_threshold=Decimal(2)))
    # No liquidity drop, but sell/buy = 300/100 = 3 > 2 -> dump.
    outcome = engine.compute(
        make_inputs(
            prev_liquidity=Decimal(1000),
            curr_liquidity=Decimal(1000),
            buy_volume=Decimal(100),
            sell_volume=Decimal(300),
        )
    )
    assert outcome.exit is not None
    assert outcome.exit.exit_class is ExitClass.DUMP
    assert outcome.exit.contributing_metrics["sell_buy_ratio"] == Decimal(3)


def test_rug_pull_takes_precedence_over_dump():
    """Design: rug-pull is evaluated before dump (elif)."""
    engine, _ = make_engine(config=make_config(rugpull_threshold=Decimal(30), dump_threshold=Decimal(2)))
    outcome = engine.compute(
        make_inputs(
            prev_liquidity=Decimal(1000),
            curr_liquidity=Decimal(400),  # 60% drop
            buy_volume=Decimal(100),
            sell_volume=Decimal(300),  # also a dump
        )
    )
    assert outcome.exit is not None
    assert outcome.exit.exit_class is ExitClass.RUG_PULL


def test_held_position_exit_alert_emitted():
    """Req 5.5: a held-position exit signal surfaces an alert via the sink seam."""
    alerts: list[Alert] = []
    engine, _ = make_engine(
        position_held=lambda pair_id: True, alert_sink=alerts.append
    )
    engine.compute(make_inputs(prev_liquidity=Decimal(1000), curr_liquidity=Decimal(100)))

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.is_exit_signal
    assert alert.pair_id == PAIR_ID
    assert "RUG_PULL" in alert.title


def test_no_exit_alert_when_position_not_held():
    """Req 5.5: no exit alert when no Position is held for the pair."""
    alerts: list[Alert] = []
    engine, _ = make_engine(
        position_held=lambda pair_id: False, alert_sink=alerts.append
    )
    engine.compute(make_inputs(prev_liquidity=Decimal(1000), curr_liquidity=Decimal(100)))
    assert alerts == []


def test_skip_on_missing_required_metric_retains_prior_signals():
    """Req 5.7: missing required metrics skip computation and retain prior signals."""
    engine, repo = make_engine()

    # First interval: a normal computation records an entry signal.
    first = engine.compute(make_inputs())
    assert not first.skipped
    prior = repo.history(PAIR_ID)
    assert len(prior) >= 1

    # Second interval: a required metric (buy_volume) is MISSING -> skip.
    skipped = engine.compute(make_inputs(buy_volume=MISSING))
    assert skipped.skipped
    assert skipped.entry is None
    assert skipped.exit is None
    assert skipped.skip is not None
    assert "buy_volume" in skipped.skip.reason

    # Prior signals are retained; no new signal appended this interval.
    assert repo.history(PAIR_ID) == prior
    assert engine.skipped_intervals[-1].pair_id == PAIR_ID


def test_skip_on_stale_sample():
    """Req 5.7: a stale (last-good) sample skips computation and is recorded."""
    engine, repo = make_engine()
    outcome = engine.compute(make_inputs(stale=True))
    assert outcome.skipped
    assert "stale" in outcome.skip.reason
    assert repo.history(PAIR_ID) == []
    assert len(engine.skipped_intervals) == 1


def test_missing_prev_liquidity_does_not_skip_and_skips_only_rug_check():
    """A missing/None prior liquidity is not a required metric (no skip; no rug-pull)."""
    engine, _ = make_engine(config=make_config(dump_threshold=Decimal(2)))
    outcome = engine.compute(
        make_inputs(prev_liquidity=None, buy_volume=Decimal(100), sell_volume=Decimal(300))
    )
    assert not outcome.skipped
    # No baseline -> rug-pull skipped, but dump still evaluated.
    assert outcome.exit is not None
    assert outcome.exit.exit_class is ExitClass.DUMP
