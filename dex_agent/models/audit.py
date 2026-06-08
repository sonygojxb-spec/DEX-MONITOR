"""Audit-trail models.

Design reference: "Data Models" -> "Audit & Authorization". Covers
:class:`ActionType` and :class:`AuditRecord`. (The :class:`AuditInfo` token
security metadata is a separate value object in :mod:`dex_agent.models.market`.)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ActionType(Enum):
    """The kind of action captured by an append-only audit record (Req 10.1)."""

    SECURITY_INSPECTION = "SECURITY_INSPECTION"
    WALLET_ANALYSIS = "WALLET_ANALYSIS"
    SIGNAL_COMPUTATION = "SIGNAL_COMPUTATION"
    TRADE_EXECUTION = "TRADE_EXECUTION"
    PERSISTENCE_FAILURE = "PERSISTENCE_FAILURE"


@dataclass(frozen=True)
class AuditRecord:
    """One append-only audit-trail entry.

    ``recorded_at`` is to millisecond-level UTC precision (Requirement 10.1).
    """

    action_type: ActionType
    pair_id: str
    outcome: str
    recorded_at: datetime


__all__ = [
    "ActionType",
    "AuditRecord",
]
