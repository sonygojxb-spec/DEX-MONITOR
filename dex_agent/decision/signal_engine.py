"""Signal_Engine: entry eligibility + rug-pull / dump exit signals.

Design reference: "Signal_Engine". Maps to Requirements 5.1-5.7.

At each Signal_Computation_Interval the engine computes, for a monitored
Trading_Pair, an Entry_Signal and (when conditions hold) an Exit_Signal from the
recorded security, wallet, and market metrics, following the design pseudocode::

    compute(pair):
        if metrics stale/unavailable: skip; record skipped; keep prior   # Req 5.7
        entry = score_entry(security, wallet, metrics)                    # Req 5.1
        eligible = entry >= entry_threshold AND severity <= max_severity  # Req 5.2
        if liquidity_drop_pct(prev, curr) > rugpull_threshold:
            exit = ExitSignal(RUG_PULL)                                   # Req 5.3
        elif sell_volume / buy_volume > dump_threshold:
            exit = ExitSignal(DUMP)                                       # Req 5.4
        record signals with contributing metrics + ts                     # Req 5.6
        if exit and position_held(pair): Notifier.alert(pair, exit) <=5s  # Req 5.5

The three threshold predicates are exposed as pure module-level functions so they
can be exercised exactly (iff) by the Correctness Properties:

* :func:`is_eligible`      - Property 16 (entry eligibility predicate, Req 5.2).
* :func:`is_rug_pull`      - Property 17 (rug-pull exit predicate, Req 5.3).
* :func:`is_dump`          - Property 18 (dump exit predicate, Req 5.4).

The engine depends only on injected seams - the Task 3
:class:`~dex_agent.repositories.interfaces.SignalRepository` (to record generated
signals and to retain prior signals on skip), a ``position_held`` predicate, and
an :data:`~dex_agent.analysis.backend_analyzer.AlertSink` for the <=5s held-position
exit alert (Req 5.5; Task 17 wires the real Notifier behind this seam). Thresholds
come from the validated :class:`~dex_agent.models.Configuration`, and the maximum
acceptable Severity_Rating is injected separately (it lives on the user's
:class:`~dex_agent.models.RiskProfile`, not on ``Configuration``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Callable, Mapping

from dex_agent.models import (
    MISSING,
    Configuration,
    ExitClass,
    MetricValue,
    Severity,
    Signal,
    SignalType,
    utc_now_seconds,
)
from dex_agent.providers.interfaces import Alert
from dex_agent.repositories.interfaces import SignalRepository

# A callable that reports whether a Position is currently held for a pair
# (Req 5.5). Injected so the engine stays decoupled from the position store.
PositionHeld = Callable[[str], bool]

# A callable sink that delivers an :class:`Alert`. Task 17 wires the real
# Notifier behind this seam; tests inject a recording sink (Req 5.5).
AlertSink = Callable[[Alert], None]


# ---------------------------------------------------------------------------
# Pure threshold predicates (exercised exactly by Properties 16-18)
# ---------------------------------------------------------------------------


def is_eligible(
    entry_score: Decimal,
    severity: Severity,
    *,
    entry_threshold: Decimal,
    max_severity: Severity,
) -> bool:
    """Entry-eligibility predicate (Req 5.2; Property 16).

    A Trading_Pair is eligible for entry **iff** the computed entry score *meets*
    (is at or above) the user-configured entry threshold **and** the Token's
    Severity_Rating is at or below the user-configured maximum acceptable
    severity::

        eligible  <=>  entry_score >= entry_threshold  AND  severity <= max_severity

    Both conjuncts are required; failing either makes the pair ineligible.
    """
    return entry_score >= entry_threshold and severity <= max_severity


def liquidity_drop_pct(prev_liquidity: Decimal, curr_liquidity: Decimal) -> Decimal:
    """Percentage by which liquidity *decreased* from ``prev`` to ``curr``.

    Returns ``100 * (prev - curr) / prev`` when liquidity fell, and ``0`` when it
    held steady or rose (an increase is not a "drop"). Returns ``0`` when
    ``prev_liquidity <= 0`` (no meaningful baseline to measure a drop against).
    """
    if prev_liquidity <= 0:
        return Decimal(0)
    drop = (prev_liquidity - curr_liquidity) / prev_liquidity * Decimal(100)
    return drop if drop > 0 else Decimal(0)


def is_rug_pull(
    prev_liquidity: Decimal,
    curr_liquidity: Decimal,
    *,
    rugpull_threshold: Decimal,
) -> bool:
    """Rug-pull exit predicate (Req 5.3; Property 17).

    True **iff** the liquidity drop between two consecutive snapshots within a
    single Measurement_Period is *greater than* (strictly exceeds) the
    user-configured rug-pull threshold::

        rug_pull  <=>  liquidity_drop_pct(prev, curr) > rugpull_threshold
    """
    return liquidity_drop_pct(prev_liquidity, curr_liquidity) > rugpull_threshold


def is_dump(
    buy_volume: Decimal,
    sell_volume: Decimal,
    *,
    dump_threshold: Decimal,
) -> bool:
    """Dump exit predicate (Req 5.4; Property 18).

    True **iff** buy volume is positive **and** the sell-to-buy volume ratio over
    a single Measurement_Period *exceeds* (strictly) the user-configured dump
    threshold::

        dump  <=>  buy_volume > 0  AND  sell_volume / buy_volume > dump_threshold

    When ``buy_volume <= 0`` the ratio is undefined and no dump signal is raised.
    """
    if buy_volume <= 0:
        return False
    return sell_volume / buy_volume > dump_threshold


def score_entry(
    severity: Severity,
    bot_pct: Decimal,
    holder_concentration: Decimal,
) -> Decimal:
    """Compute the entry score in ``[0, 100]`` from the analysis inputs (Req 5.1).

    The score blends three quality signals (higher is a better entry):

    * **security** - lower :class:`Severity` is better; an ordinal ``o`` in
      ``0..4`` contributes ``100 * (4 - o) / 4``;
    * **wallet** - lower bot-transaction percentage is better, contributing
      ``100 - bot_pct``;
    * **distribution** - lower top-10 holder concentration is better,
      contributing ``100 - holder_concentration``.

    The three components are averaged and clamped to ``[0, 100]``. The blend is
    this component's documented scoring choice; the Correctness Properties pin
    only the *eligibility* predicate (:func:`is_eligible`), not the formula.
    """
    security_component = Decimal(100) * Decimal(Severity.CRITICAL.value - severity.value) / Decimal(
        Severity.CRITICAL.value
    )
    wallet_component = Decimal(100) - bot_pct
    distribution_component = Decimal(100) - holder_concentration
    raw = (security_component + wallet_component + distribution_component) / Decimal(3)
    return _clamp_pct(raw)


def _clamp_pct(value: Decimal) -> Decimal:
    """Clamp ``value`` into the inclusive percentage range ``[0, 100]``."""
    if value < 0:
        return Decimal(0)
    if value > 100:
        return Decimal(100)
    return value


# ---------------------------------------------------------------------------
# Inputs / outcome value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignalInputs:
    """The recorded analysis inputs for one Signal_Computation_Interval.

    Gathered by the orchestrator (Task 18) from the Security_Inspector,
    Backend_Analyzer, and Metrics_Tracker outputs and passed to
    :meth:`SignalEngine.compute`.

    ``prev_liquidity`` is the liquidity of the previous consecutive snapshot
    within the Measurement_Period; it is ``None`` on the first snapshot (no
    baseline yet) and :data:`~dex_agent.models.MISSING` when that prior value was
    unavailable - in both cases the rug-pull comparison is skipped. The
    market-volume and current-liquidity values may be :data:`MISSING` when the
    metric was unavailable this interval; ``stale`` marks the whole input as a
    last-good/stale sample. Either condition triggers the skip path (Req 5.7).
    """

    pair_id: str
    severity: Severity
    bot_pct: Decimal
    holder_concentration: Decimal
    curr_liquidity: MetricValue
    buy_volume: MetricValue
    sell_volume: MetricValue
    prev_liquidity: MetricValue | None = None
    stale: bool = False
    generated_at: datetime | None = None


@dataclass(frozen=True)
class SkipRecord:
    """A recorded skipped Signal_Computation_Interval (Req 5.7)."""

    pair_id: str
    reason: str
    skipped_at: datetime


@dataclass(frozen=True)
class ComputeOutcome:
    """The result of one :meth:`SignalEngine.compute` call.

    Attributes:
        pair_id: The Trading_Pair the computation ran for.
        skipped: ``True`` when computation was skipped for stale/missing metrics
            (Req 5.7); in that case ``entry`` and ``exit`` are ``None``.
        skip: The :class:`SkipRecord` when ``skipped`` is set, else ``None``.
        entry: The generated Entry_Signal, or ``None`` when skipped.
        exit: The generated Exit_Signal, or ``None`` when no exit condition held
            (or when skipped).
        eligible: Whether the pair was marked eligible for entry (Req 5.2);
            ``False`` when skipped.
    """

    pair_id: str
    skipped: bool
    skip: SkipRecord | None = None
    entry: Signal | None = None
    exit: Signal | None = None
    eligible: bool = False


class SignalEngine:
    """Computes entry/exit signals for a Trading_Pair (Req 5.1-5.7).

    Args:
        signal_repo: The :class:`SignalRepository` that records generated signals
            (Req 5.6) and whose prior contents are retained on a skip (Req 5.7).
        config: The validated :class:`Configuration` supplying the entry,
            rug-pull, and dump thresholds.
        max_severity: The user-configured maximum acceptable Severity_Rating used
            in the eligibility predicate (Req 5.2). Sourced from the user's
            :class:`~dex_agent.models.RiskProfile`; defaults to
            :attr:`Severity.CRITICAL` (accept all) when not supplied.
        position_held: Predicate reporting whether a Position is held for a pair;
            gates the <=5s exit alert (Req 5.5). Defaults to "never held".
        alert_sink: Sink that receives the held-position exit :class:`Alert`
            (Req 5.5). Task 17 wires the real Notifier here.
        clock: Callable returning the current second-precision UTC timestamp used
            to stamp signals and skip records; injectable for tests.
    """

    def __init__(
        self,
        signal_repo: SignalRepository,
        config: Configuration,
        *,
        max_severity: Severity = Severity.CRITICAL,
        position_held: PositionHeld | None = None,
        alert_sink: AlertSink | None = None,
        clock: Callable[[], datetime] = utc_now_seconds,
    ) -> None:
        self._signal_repo = signal_repo
        self._entry_threshold = config.entry_threshold
        self._rugpull_threshold = config.rugpull_threshold
        self._dump_threshold = config.dump_threshold
        self._max_severity = max_severity
        self._position_held = position_held or (lambda _pair_id: False)
        self._alert_sink = alert_sink
        self._clock = clock
        # Recorded skipped intervals (Req 5.7); prior signals stay in the repo.
        self._skips: list[SkipRecord] = []

    # ------------------------------------------------------------------
    # Computation (Req 5.1-5.7)
    # ------------------------------------------------------------------
    def compute(self, inputs: SignalInputs) -> ComputeOutcome:
        """Compute the signals for one Signal_Computation_Interval.

        Follows the design pseudocode: skip on stale/missing metrics (Req 5.7);
        otherwise score and mark eligibility (Req 5.1, 5.2), evaluate the
        rug-pull then dump exit conditions (Req 5.3, 5.4), record every generated
        signal with its contributing metrics + timestamp (Req 5.6), and surface a
        <=5s exit alert when a Position is held (Req 5.5).
        """
        ts = inputs.generated_at or self._clock()

        # --- Req 5.7: stale / missing required metrics -> skip, keep prior. ---
        missing_reason = self._missing_metrics_reason(inputs)
        if missing_reason is not None:
            skip = SkipRecord(
                pair_id=inputs.pair_id, reason=missing_reason, skipped_at=ts
            )
            self._skips.append(skip)
            return ComputeOutcome(pair_id=inputs.pair_id, skipped=True, skip=skip)

        curr_liquidity = _require_decimal(inputs.curr_liquidity)
        buy_volume = _require_decimal(inputs.buy_volume)
        sell_volume = _require_decimal(inputs.sell_volume)

        # --- Req 5.1 / 5.2: entry score + eligibility. ---
        entry_score = score_entry(
            inputs.severity, inputs.bot_pct, inputs.holder_concentration
        )
        eligible = is_eligible(
            entry_score,
            inputs.severity,
            entry_threshold=self._entry_threshold,
            max_severity=self._max_severity,
        )
        entry_signal = Signal(
            pair_id=inputs.pair_id,
            type=SignalType.ENTRY,
            score=entry_score,
            eligible=eligible,
            generated_at=ts,
            contributing_metrics={
                "severity": inputs.severity.name,
                "bot_pct": inputs.bot_pct,
                "holder_concentration": inputs.holder_concentration,
                "entry_score": entry_score,
                "entry_threshold": self._entry_threshold,
                "max_severity": self._max_severity.name,
            },
        )
        self._signal_repo.append(entry_signal)  # Req 5.6

        # --- Req 5.3 / 5.4: exit conditions (rug-pull takes precedence). ---
        exit_signal = self._evaluate_exit(inputs, curr_liquidity, buy_volume, sell_volume, ts)
        if exit_signal is not None:
            self._signal_repo.append(exit_signal)  # Req 5.6
            # --- Req 5.5: held-position exit alert within 5 seconds. ---
            if self._position_held(inputs.pair_id):
                self._emit_exit_alert(inputs.pair_id, exit_signal)

        return ComputeOutcome(
            pair_id=inputs.pair_id,
            skipped=False,
            entry=entry_signal,
            exit=exit_signal,
            eligible=eligible,
        )

    @property
    def skipped_intervals(self) -> tuple[SkipRecord, ...]:
        """The recorded skipped Signal_Computation_Intervals (Req 5.7)."""
        return tuple(self._skips)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _evaluate_exit(
        self,
        inputs: SignalInputs,
        curr_liquidity: Decimal,
        buy_volume: Decimal,
        sell_volume: Decimal,
        ts: datetime,
    ) -> Signal | None:
        """Evaluate the rug-pull then dump exit conditions (Req 5.3, 5.4)."""
        prev_liquidity = _optional_decimal(inputs.prev_liquidity)

        if prev_liquidity is not None and is_rug_pull(
            prev_liquidity, curr_liquidity, rugpull_threshold=self._rugpull_threshold
        ):
            return self._exit_signal(
                inputs.pair_id,
                ExitClass.RUG_PULL,
                ts,
                {
                    "prev_liquidity": prev_liquidity,
                    "curr_liquidity": curr_liquidity,
                    "liquidity_drop_pct": liquidity_drop_pct(
                        prev_liquidity, curr_liquidity
                    ),
                    "rugpull_threshold": self._rugpull_threshold,
                },
            )

        if is_dump(buy_volume, sell_volume, dump_threshold=self._dump_threshold):
            return self._exit_signal(
                inputs.pair_id,
                ExitClass.DUMP,
                ts,
                {
                    "buy_volume": buy_volume,
                    "sell_volume": sell_volume,
                    "sell_buy_ratio": sell_volume / buy_volume,
                    "dump_threshold": self._dump_threshold,
                },
            )

        return None

    @staticmethod
    def _exit_signal(
        pair_id: str,
        exit_class: ExitClass,
        ts: datetime,
        contributing: Mapping[str, object],
    ) -> Signal:
        """Build an EXIT :class:`Signal` with its contributing metrics (Req 5.6)."""
        return Signal(
            pair_id=pair_id,
            type=SignalType.EXIT,
            score=Decimal(0),
            eligible=False,
            generated_at=ts,
            exit_class=exit_class,
            contributing_metrics=dict(contributing),
        )

    def _missing_metrics_reason(self, inputs: SignalInputs) -> str | None:
        """Return why the interval must be skipped, or ``None`` to proceed (Req 5.7).

        Required metrics are the current liquidity and the buy/sell volumes over
        the Measurement_Period; a stale sample or any missing required value
        triggers a skip. ``prev_liquidity`` is *not* required (the rug-pull check
        is simply skipped when no baseline is available).
        """
        if inputs.stale:
            return "metrics sample is stale (last-good value)"
        missing = [
            name
            for name, value in (
                ("curr_liquidity", inputs.curr_liquidity),
                ("buy_volume", inputs.buy_volume),
                ("sell_volume", inputs.sell_volume),
            )
            if value is MISSING
        ]
        if missing:
            return f"required metrics unavailable: {', '.join(missing)}"
        return None

    def _emit_exit_alert(self, pair_id: str, exit_signal: Signal) -> None:
        """Deliver the held-position exit alert through the sink seam (Req 5.5)."""
        if self._alert_sink is None:
            return
        assert exit_signal.exit_class is not None
        classification = exit_signal.exit_class.value
        alert = Alert(
            title=f"Exit signal: {classification}",
            body=(
                f"Exit signal ({classification}) generated for held position in "
                f"pair {pair_id}."
            ),
            severity=Severity.CRITICAL,
            pair_id=pair_id,
            is_exit_signal=True,
        )
        self._alert_sink(alert)


def _optional_decimal(value: MetricValue | None) -> Decimal | None:
    """Coerce a metric value to a ``Decimal``; ``None``/``MISSING`` -> ``None``."""
    if value is None or value is MISSING:
        return None
    return value


def _require_decimal(value: MetricValue) -> Decimal:
    """Coerce a known-present metric value to ``Decimal`` (post skip-guard)."""
    assert value is not MISSING
    return value  # type: ignore[return-value]


__all__ = [
    "SignalEngine",
    "SignalInputs",
    "SkipRecord",
    "ComputeOutcome",
    "PositionHeld",
    "AlertSink",
    "is_eligible",
    "is_rug_pull",
    "is_dump",
    "liquidity_drop_pct",
    "score_entry",
]
