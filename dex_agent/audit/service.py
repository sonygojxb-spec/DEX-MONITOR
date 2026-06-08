"""Audit / persistence service: append-only trail with retry + retention.

Design reference: "Audit / Persistence Service". Maps to Requirements 10.1-10.7.

The service durably records the Agent's analyses and actions and serves
validated history queries:

* :meth:`AuditService.record` builds an :class:`~dex_agent.models.AuditRecord`
  (action type, Trading_Pair, outcome, **millisecond-precision UTC** timestamp;
  Req 10.1) and persists it. Persistence is performed through an **injected**
  ``persist`` callable so transient failures can be simulated deterministically
  in tests. On failure it retries up to 3 times (4 attempts total); if every
  attempt fails it records a :data:`~dex_agent.models.ActionType.PERSISTENCE_FAILURE`
  marker naming the failed action type and continues without interrupting
  in-progress operations (Req 10.7).
* :meth:`AuditService.query` rejects an inverted range
  (``start > end``) with :class:`~dex_agent.errors.InvalidRange` (Req 10.4) and
  otherwise returns the pair's records whose timestamp falls within the inclusive
  ``[start, end]`` range, oldest-to-newest (Req 10.2), or an empty list when none
  fall in range (Req 10.3). The in-range selection reuses the **same** shared
  :func:`~dex_agent.repositories.query.entries_in_range` primitive (via the
  injected :class:`~dex_agent.repositories.interfaces.AuditRepository`) that the
  Metrics_Tracker uses, so the audit query satisfies the same Property 13/14
  semantics.
* :meth:`AuditService.enforce_retention` deletes exactly the records whose age
  exceeds the user-configured retention period (30-3650 days, default 30;
  Req 10.5, 10.6), reusing the shared
  :func:`~dex_agent.repositories.query.older_than` retention primitive (via the
  repository's ``purge_older_than``).

The service depends only on the ``AuditRepository`` interface so storage is
injectable / fakeable, and the retry path never sleeps on real time - the
``persist`` callable is injected so failure is deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from dex_agent.errors import InvalidRange
from dex_agent.models import (
    ActionType,
    AuditRecord,
    to_millis_precision,
    utc_now_millis,
)
from dex_agent.repositories.interfaces import AuditRepository
from dex_agent.result import Err, Ok, Result

# Retention bounds (days), inclusive, with the documented default (Req 10.5).
RETENTION_DAYS_MIN = 30
RETENTION_DAYS_MAX = 3650
RETENTION_DAYS_DEFAULT = 30

# Maximum number of persistence *retries* after the initial attempt (Req 10.7),
# i.e. up to ``MAX_RETRIES + 1`` total attempts.
MAX_RETRIES = 3

# A persistence operation: stores a record and returns ``True`` on success,
# ``False`` when the write failed (so the caller can retry). Injected so a
# flaky/failing backend can be simulated deterministically without real I/O.
PersistFn = Callable[[AuditRecord], bool]


@dataclass(frozen=True)
class RecordOutcome:
    """Outcome of an :meth:`AuditService.record` call.

    Attributes:
        record: The audit record that was built for the action (Req 10.1).
        persisted: ``True`` iff the record was durably persisted (within the
            retry budget).
        attempts: The number of persistence attempts made for ``record`` (1 when
            the first attempt succeeded, up to ``MAX_RETRIES + 1``).
        failure_record: The :data:`ActionType.PERSISTENCE_FAILURE` marker written
            when every attempt failed (Req 10.7), otherwise ``None``.
    """

    record: AuditRecord
    persisted: bool
    attempts: int
    failure_record: AuditRecord | None = None


class AuditService:
    """Append-only audit trail with retry-on-persist and retention enforcement."""

    def __init__(
        self,
        repo: AuditRepository,
        *,
        persist: PersistFn | None = None,
        retention_days: int = RETENTION_DAYS_DEFAULT,
    ) -> None:
        """Create the service.

        Args:
            repo: The injected append-only audit repository (storage backend).
            persist: Optional persistence operation used for the primary record
                and its retries. Defaults to appending through ``repo`` (always
                succeeds for the in-memory repo). Inject a failing/flaky callable
                to exercise the retry + persistence-failure path (Req 10.7).
            retention_days: User-configured retention period in days; must be in
                ``[30, 3650]`` (Req 10.5). Defaults to 30.
        """
        self._repo = repo
        self._persist: PersistFn = persist if persist is not None else self._default_persist
        self.retention_days = self._validate_retention(retention_days)

    # -- configuration ------------------------------------------------------

    @staticmethod
    def _validate_retention(days: int) -> int:
        if not (RETENTION_DAYS_MIN <= days <= RETENTION_DAYS_MAX):
            raise ValueError(
                "retention_days must be within "
                f"[{RETENTION_DAYS_MIN}, {RETENTION_DAYS_MAX}], got {days}"
            )
        return days

    def _default_persist(self, record: AuditRecord) -> bool:
        """Default persistence: append through the repository (Req 10.2 store)."""
        self._repo.append(record)
        return True

    # -- recording (Req 10.1, 10.7) -----------------------------------------

    def record(
        self,
        action_type: ActionType,
        pair_id: str,
        outcome: str,
        *,
        recorded_at: datetime | None = None,
    ) -> RecordOutcome:
        """Persist an audit record for a completed action.

        Builds an :class:`AuditRecord` carrying ``action_type``, ``pair_id``,
        ``outcome`` and a millisecond-precision UTC timestamp (Req 10.1), then
        persists it through the injected ``persist`` callable, retrying up to
        :data:`MAX_RETRIES` times on failure (Req 10.7). When every attempt
        fails, a :data:`ActionType.PERSISTENCE_FAILURE` marker naming the failed
        action type is written directly to the repository and the service returns
        without interrupting in-progress operations (Req 10.7).

        Args:
            action_type: The kind of completed action being audited.
            pair_id: The associated Trading_Pair identifier.
            outcome: A description of the action outcome.
            recorded_at: Optional timestamp override (truncated to millisecond
                precision). Defaults to the current UTC time at millisecond
                precision; injectable so timing is deterministic in tests.

        Returns:
            A :class:`RecordOutcome` describing the persistence result.
        """
        ts = (
            to_millis_precision(recorded_at)
            if recorded_at is not None
            else utc_now_millis()
        )
        record = AuditRecord(
            action_type=action_type,
            pair_id=pair_id,
            outcome=outcome,
            recorded_at=ts,
        )

        attempts = 0
        persisted = False
        # Initial attempt + up to MAX_RETRIES retries (Req 10.7).
        while attempts <= MAX_RETRIES:
            attempts += 1
            if self._persist(record):
                persisted = True
                break

        if persisted:
            return RecordOutcome(record=record, persisted=True, attempts=attempts)

        # All attempts failed: record a persistence-failure marker naming the
        # failed action type and continue operating (Req 10.7). The marker is
        # written directly to the repository so the failure is durably noted even
        # when the injected persist path is unavailable.
        failure_record = AuditRecord(
            action_type=ActionType.PERSISTENCE_FAILURE,
            pair_id=pair_id,
            outcome=f"persistence failed for action {action_type.value}",
            recorded_at=utc_now_millis(),
        )
        self._repo.append(failure_record)
        return RecordOutcome(
            record=record,
            persisted=False,
            attempts=attempts,
            failure_record=failure_record,
        )

    # -- queries (Req 10.2, 10.3, 10.4) -------------------------------------

    def query(
        self, pair_id: str, start: datetime, end: datetime
    ) -> Result[list[AuditRecord]]:
        """Return the pair's records within ``[start, end]`` ascending (Req 10.2).

        Mirrors the Metrics_Tracker validation/selection semantics so audit and
        metrics share one definition of "in range":

        1. An inverted range (``start > end``) is rejected with
           :class:`~dex_agent.errors.InvalidRange` (Req 10.4) before any lookup,
           so the rejection never mutates stored data.
        2. Otherwise the in-range records are returned oldest-to-newest via the
           shared :func:`~dex_agent.repositories.query.entries_in_range` primitive
           (reused by the repository), possibly empty when none fall in range
           (Req 10.3).
        """
        if start > end:
            return Err(
                InvalidRange(
                    "audit history range start is later than end",
                    start=start,
                    end=end,
                )
            )
        return Ok(self._repo.query_range(pair_id, start, end))

    # -- retention (Req 10.5, 10.6) -----------------------------------------

    def enforce_retention(
        self, *, now: datetime | None = None
    ) -> list[AuditRecord]:
        """Delete exactly the records whose age exceeds the retention period.

        The retention boundary is ``now - retention_period`` where the period is
        :attr:`retention_days` days (Req 10.5). A record is deleted iff its
        timestamp is **strictly older** than the boundary (its age exceeds the
        period; Req 10.6) - reusing the shared
        :func:`~dex_agent.repositories.query.older_than` primitive via the
        repository's ``purge_older_than``.

        Args:
            now: Reference "current" time; defaults to the current UTC time.
                Injectable so retention is deterministically testable.

        Returns:
            The list of records that were deleted (ascending by timestamp).
        """
        period = timedelta(days=self.retention_days)
        return self._repo.purge_older_than(period, now=now)


__all__ = [
    "AuditService",
    "RecordOutcome",
    "PersistFn",
    "RETENTION_DAYS_MIN",
    "RETENTION_DAYS_MAX",
    "RETENTION_DAYS_DEFAULT",
    "MAX_RETRIES",
]
