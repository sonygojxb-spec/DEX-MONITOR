"""The ordered ``Severity`` rating and the ``max_by_ordinal`` aggregation helper.

Design references: "Data Models" (``Severity: enum ordered { None=0, Low=1,
Medium=2, High=3, Critical=4 }``) and ``SEVERITY_ORDER`` in the
"Security_Inspector" / "External Integrations" sections.

Python's ``None`` is a reserved literal and cannot be an enum member name, so
the design's ``None`` rating maps to :attr:`Severity.NONE` (ordinal ``0``). All
other names and ordinals match the design exactly. ``Severity`` is an
:class:`enum.IntEnum`, so members compare by their ordinal (``Low < High``),
which the Signal_Engine and Risk_Manager rely on for ``severity <= max_severity``
checks in later tasks.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Iterable


class Severity(IntEnum):
    """Ordered risk classification assigned to a Token (Requirement 2.1).

    The members are ordered by ordinal value, lowest (:attr:`NONE`) to highest
    (:attr:`CRITICAL`). Because this is an :class:`~enum.IntEnum`, ``<``, ``>``,
    ``min`` and ``max`` operate on the ordinal directly.
    """

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# The ordered list of severities (index == ordinal). Mirrors the design's
# ``SEVERITY_ORDER = [None, Low, Medium, High, Critical]``.
SEVERITY_ORDER: tuple[Severity, ...] = (
    Severity.NONE,
    Severity.LOW,
    Severity.MEDIUM,
    Severity.HIGH,
    Severity.CRITICAL,
)


def max_by_ordinal(severities: Iterable[Severity]) -> Severity:
    """Return the highest severity by ordinal, defaulting to ``NONE`` if empty.

    Used to set a Token's overall Severity_Rating to the maximum contributing
    issue severity (Requirements 2.5, 2.7). For an empty input the result is
    :attr:`Severity.NONE` (the design's ``default=None``).

    Args:
        severities: Any iterable of :class:`Severity` values (possibly empty).

    Returns:
        The member with the greatest ordinal, or :attr:`Severity.NONE` when no
        severities are supplied.
    """
    highest = Severity.NONE
    for severity in severities:
        if severity.value > highest.value:
            highest = severity
    return highest


__all__ = [
    "Severity",
    "SEVERITY_ORDER",
    "max_by_ordinal",
]
