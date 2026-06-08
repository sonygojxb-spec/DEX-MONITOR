"""Audit / persistence service.

Design reference: "Audit / Persistence Service" (Requirements 10.1-10.7). The
:class:`AuditService` records an append-only trail of analyses and actions with
millisecond-precision timestamps, retries failed persistence (writing a
persistence-failure marker when all retries fail), serves validated range
queries reusing the shared in-range primitive, and enforces a user-configured
retention period reusing the shared retention primitive.

Public names are re-exported here for convenient importing, e.g.
``from dex_agent.audit import AuditService``.
"""

from __future__ import annotations

from dex_agent.audit.service import (
    MAX_RETRIES,
    RETENTION_DAYS_DEFAULT,
    RETENTION_DAYS_MAX,
    RETENTION_DAYS_MIN,
    AuditService,
    PersistFn,
    RecordOutcome,
)

__all__ = [
    "AuditService",
    "RecordOutcome",
    "PersistFn",
    "RETENTION_DAYS_MIN",
    "RETENTION_DAYS_MAX",
    "RETENTION_DAYS_DEFAULT",
    "MAX_RETRIES",
]
