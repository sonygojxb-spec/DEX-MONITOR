"""Security inspection models.

Design reference: "Data Models" -> "Security". Covers :class:`SecurityIssueType`,
:class:`SecurityIssue`, and :class:`SecurityEvaluation`. The :class:`Severity`
rating lives in :mod:`dex_agent.models.severity`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from dex_agent.models.severity import Severity


class SecurityIssueType(Enum):
    """Categories of detected contract security issues (Requirement 2.4, 2.9).

    Mirrors the design's ``SecurityIssue.type`` enum
    ``{ MINTABLE, TRANSFER_DISABLE, FEE_MODIFIABLE, OWNERSHIP_PRIVILEGE,
    UNVERIFIED }``.
    """

    MINTABLE = "MINTABLE"
    TRANSFER_DISABLE = "TRANSFER_DISABLE"
    FEE_MODIFIABLE = "FEE_MODIFIABLE"
    OWNERSHIP_PRIVILEGE = "OWNERSHIP_PRIVILEGE"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class SecurityIssue:
    """A single detected security issue and its contributing severity.

    Requirement 2.6: each issue records its type, description, and contributing
    Severity_Rating.
    """

    type: SecurityIssueType
    description: str
    severity: Severity


@dataclass(frozen=True)
class SecurityEvaluation:
    """The result of inspecting a Token's contract.

    ``rating`` is the maximum contributing issue severity (default
    :attr:`Severity.NONE` when there are no issues; Requirements 2.5, 2.7).
    ``evaluated_at`` is recorded to second-level UTC precision (Requirement 2.8).
    ``unverified`` is ``True`` when the contract could not be retrieved/verified
    (Requirement 2.9).
    """

    token_address: str
    rating: Severity
    unverified: bool
    evaluated_at: datetime
    issues: tuple[SecurityIssue, ...] = field(default_factory=tuple)


__all__ = [
    "SecurityIssueType",
    "SecurityIssue",
    "SecurityEvaluation",
]
