"""Authorization models.

Design reference: "Data Models" -> "Audit & Authorization". Covers
:class:`AuthStatus` and :class:`AuthorizationRecord`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AuthStatus(Enum):
    """Trading-authorization status changes (Requirements 11.1, 11.4, 11.5)."""

    ENABLED = "ENABLED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class AuthorizationRecord:
    """A recorded trading-authorization status change with its timestamp."""

    wallet_id: str
    status: AuthStatus
    changed_at: datetime


__all__ = [
    "AuthStatus",
    "AuthorizationRecord",
]
