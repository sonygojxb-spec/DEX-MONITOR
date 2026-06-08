"""Metrics_Tracker: continuous market-metric time series + range queries.

Design references: "Metrics_Tracker" and "Audit field clarification (Req 4.5)".
Maps to Requirements 4.1-4.10.

The tracker appends time-series :class:`~dex_agent.models.MetricEntry` points for
each monitored Trading_Pair and serves validated range queries:

* On every Data_Refresh_Interval it records ``LIQUIDITY``, ``MARKET_CAP`` and
  ``FDV`` (Req 4.1); on every Measurement_Period it records the buy/sell counts
  (Req 4.2) and the buy/sell volumes expressed in the Quote_Asset (Req 4.3).
* Each entry carries the metric value **or** the :data:`~dex_agent.models.MISSING`
  sentinel, a timestamp truncated to second-level precision, and the Trading_Pair
  identifier; the series is stored ascending by timestamp (Req 4.4). When a value
  is unavailable the tracker records ``MISSING`` for that interval and keeps
  tracking subsequent intervals (Req 4.10).
* Where security metadata is available it captures an
  :class:`~dex_agent.models.AuditInfo` (provider / result / date, Req 4.5). Per
  the design's "Audit field clarification", that metadata is sourced **primarily**
  from the Solana RPC SPL mint-authority checks plus Moralis token metadata /
  Token Score (``provider = "Moralis+SolanaRPC"``), with GoPlus as an optional
  fallback (``provider = "GoPlus"``); the field is left ``None`` when no security
  metadata is available.
* :meth:`MetricsTracker.query_history` rejects an unmonitored pair with
  :class:`~dex_agent.errors.NotFound` (Req 4.8) and an inverted range with
  :class:`~dex_agent.errors.InvalidRange` (Req 4.7) - both without mutating stored
  data - otherwise returns the in-range entries ascending, possibly empty
  (Req 4.6, 4.9). The in-range selection reuses the shared
  :func:`~dex_agent.repositories.query.entries_in_range` primitive via the
  injected :class:`~dex_agent.repositories.interfaces.MetricsRepository`.

The tracker depends only on the ``MetricsRepository`` interface so storage is
injectable / fakeable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

from dex_agent.errors import InvalidRange, NotFound
from dex_agent.models import (
    MISSING,
    AuditInfo,
    MetricEntry,
    MetricKind,
    MetricValue,
    PairSnapshot,
    to_second_precision,
)
from dex_agent.repositories.interfaces import MetricsRepository
from dex_agent.result import Err, Ok, Result

# Provider labels for the redefined ``AuditInfo`` security metadata (design
# "Audit field clarification (Req 4.5)").
PRIMARY_AUDIT_PROVIDER = "Moralis+SolanaRPC"
FALLBACK_AUDIT_PROVIDER = "GoPlus"

# Metric kinds recorded at each Data_Refresh_Interval (Req 4.1).
REFRESH_KINDS: tuple[MetricKind, ...] = (
    MetricKind.LIQUIDITY,
    MetricKind.MARKET_CAP,
    MetricKind.FDV,
)

# Metric kinds recorded at each Measurement_Period (Req 4.2, 4.3).
PERIOD_KINDS: tuple[MetricKind, ...] = (
    MetricKind.BUY_COUNT,
    MetricKind.SELL_COUNT,
    MetricKind.BUY_VOLUME,
    MetricKind.SELL_VOLUME,
)


@dataclass(frozen=True)
class RecordResult:
    """Outcome of a :meth:`MetricsTracker.record` call.

    Attributes:
        entries: The metric points appended (stored), ascending by kind order.
        audit: The captured :class:`~dex_agent.models.AuditInfo`, or ``None`` when
            no security metadata was available (Req 4.5).
    """

    entries: list[MetricEntry] = field(default_factory=list)
    audit: AuditInfo | None = None


def build_audit_info(
    result: str | None,
    audit_date: date | None,
    *,
    from_fallback: bool = False,
) -> AuditInfo | None:
    """Construct the redefined Req 4.5 security-metadata :class:`AuditInfo`.

    Per the design's "Audit field clarification", the recorded audit information
    is best-effort security metadata. It is sourced **primarily** from the Solana
    RPC SPL mint-authority checks plus Moralis metadata / Token Score
    (``provider = "Moralis+SolanaRPC"``); when only the optional GoPlus fallback
    supplied the data, ``provider = "GoPlus"``. The field is **omitted**
    (``None``) when no security metadata is available.

    Args:
        result: The security summary returned by the providing adapter, or
            ``None`` when no security metadata is available.
        audit_date: The fetch date of the metadata. Required when ``result`` is
            present.
        from_fallback: ``True`` when the GoPlus fallback supplied the metadata.

    Returns:
        An :class:`AuditInfo` when ``result`` (and ``audit_date``) are present,
        otherwise ``None``.
    """
    if result is None or audit_date is None:
        return None
    provider = FALLBACK_AUDIT_PROVIDER if from_fallback else PRIMARY_AUDIT_PROVIDER
    return AuditInfo(provider=provider, result=result, audit_date=audit_date)


class MetricsTracker:
    """Records market-metric time series and serves validated range queries."""

    def __init__(self, repo: MetricsRepository) -> None:
        self._repo = repo
        # Latest captured security metadata per pair (Req 4.5). The metrics repo
        # stores only metric points, so the tracker retains the optional audit
        # metadata it captures from snapshots / security inputs.
        self._audit: dict[str, AuditInfo] = {}

    # -- registration -------------------------------------------------------

    def register_pair(self, pair_id: str) -> None:
        """Mark ``pair_id`` as monitored so range queries succeed (Req 4.8/4.9)."""
        self._repo.register_pair(pair_id)

    def is_monitored(self, pair_id: str) -> bool:
        """True iff ``pair_id`` is currently monitored."""
        return self._repo.is_monitored(pair_id)

    # -- recording ----------------------------------------------------------

    def record(
        self,
        snapshot: PairSnapshot,
        *,
        refresh: bool = True,
        period: bool = True,
        missing: Iterable[MetricKind] = (),
    ) -> RecordResult:
        """Append metric points for ``snapshot`` and capture any audit metadata.

        Records the refresh metrics (``LIQUIDITY``/``MARKET_CAP``/``FDV``,
        Req 4.1) when ``refresh`` is set and the per-Measurement_Period metrics
        (buy/sell counts and volumes, Req 4.2/4.3) when ``period`` is set. Each
        point is timestamped at second-level precision from ``snapshot.fetched_at``
        and stored ascending (Req 4.4). Any kind listed in ``missing`` is recorded
        as :data:`~dex_agent.models.MISSING` for this interval, and tracking of
        subsequent intervals continues (Req 4.10).

        When ``snapshot.audit`` carries security metadata it is captured as the
        pair's latest :class:`AuditInfo` (Req 4.5).

        Args:
            snapshot: The ingestion sample to record.
            refresh: Record the refresh-cadence metrics (Req 4.1).
            period: Record the Measurement_Period metrics (Req 4.2, 4.3).
            missing: Kinds whose value is unavailable this interval (Req 4.10).

        Returns:
            A :class:`RecordResult` with the appended entries and captured audit.
        """
        ts = to_second_precision(snapshot.fetched_at)
        missing_kinds = set(missing)

        # Map each selected kind to its raw value from the snapshot.
        sources: list[tuple[MetricKind, Decimal]] = []
        if refresh:
            sources.append((MetricKind.LIQUIDITY, snapshot.liquidity))
            sources.append((MetricKind.MARKET_CAP, snapshot.market_cap))
            sources.append((MetricKind.FDV, snapshot.fdv))
        if period:
            sources.append((MetricKind.BUY_COUNT, Decimal(snapshot.buy_count)))
            sources.append((MetricKind.SELL_COUNT, Decimal(snapshot.sell_count)))
            sources.append((MetricKind.BUY_VOLUME, snapshot.buy_volume))
            sources.append((MetricKind.SELL_VOLUME, snapshot.sell_volume))

        entries: list[MetricEntry] = []
        for kind, raw in sources:
            value: MetricValue = MISSING if kind in missing_kinds else raw
            stored = self._repo.append(
                MetricEntry(
                    pair_id=snapshot.pair_id,
                    kind=kind,
                    value=value,
                    recorded_at=ts,
                )
            )
            entries.append(stored)

        # Capture optional security metadata when available (Req 4.5).
        if snapshot.audit is not None:
            self._audit[snapshot.pair_id] = snapshot.audit

        return RecordResult(entries=entries, audit=self._audit.get(snapshot.pair_id))

    def latest_audit(self, pair_id: str) -> AuditInfo | None:
        """Return the most recent captured :class:`AuditInfo`, or ``None`` (Req 4.5)."""
        return self._audit.get(pair_id)

    # -- queries ------------------------------------------------------------

    def query_history(
        self, pair_id: str, start: datetime, end: datetime
    ) -> Result[list[MetricEntry]]:
        """Return the pair's points within ``[start, end]`` ascending (Req 4.6).

        Validation order follows the design's Metrics_Tracker pseudocode:

        1. An unmonitored pair is rejected with :class:`~dex_agent.errors.NotFound`
           (Req 4.8) and leaves stored data unchanged.
        2. An inverted range (``start > end``) is rejected with
           :class:`~dex_agent.errors.InvalidRange` (Req 4.7), again without
           mutation - the rejection happens before any lookup.
        3. Otherwise the in-range entries are returned ascending via the shared
           :func:`~dex_agent.repositories.query.entries_in_range` primitive
           (reused by the repository), possibly empty (Req 4.9).
        """
        if not self._repo.is_monitored(pair_id):
            return Err(NotFound("trading pair is not monitored", identifier=pair_id))
        if start > end:
            return Err(
                InvalidRange(
                    "metric history range start is later than end",
                    start=start,
                    end=end,
                )
            )
        # Monitored + valid range: delegate to the repo, which reuses the shared
        # inclusive/ascending in-range primitive (Task 3).
        result = self._repo.query_range(pair_id, start, end)
        if result.is_err():
            return result
        return Ok(result.value)


__all__ = [
    "MetricsTracker",
    "RecordResult",
    "build_audit_info",
    "PRIMARY_AUDIT_PROVIDER",
    "FALLBACK_AUDIT_PROVIDER",
    "REFRESH_KINDS",
    "PERIOD_KINDS",
]
