"""Typed error taxonomy used across component boundaries.

Per the design's "Error model": operations return an explicit ``Result`` (a
success value or a typed error) rather than throwing across component
boundaries. Provider / IO errors are typed so callers can apply retention and
retry policies deterministically. No failure path performs partial state
mutation.

These error types are plain immutable value objects (frozen dataclasses). They
are *not* raised as exceptions in normal control flow; instead they are carried
inside an ``Err`` ``Result``. They subclass ``AgentError`` (which is an
``Exception``) only so they may optionally be raised at the very edge of the
system if a caller chooses to (e.g. ``result.unwrap()``), but the canonical use
is as data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


class AgentError(Exception):
    """Base class for the typed error taxonomy.

    Subclassing ``Exception`` lets an error be raised at a system boundary
    (e.g. via ``Result.unwrap``) while still being usable as an immutable value
    object carried inside an ``Err`` result.
    """

    @property
    def message(self) -> str:
        """Human-readable description of the error."""
        # Dataclass subclasses define their own field; fall back to the class
        # name when no message is present.
        return getattr(self, "detail", "") or self.__class__.__name__


@dataclass(frozen=True)
class ProviderError(AgentError):
    """A data/trade provider returned an error or an unusable response.

    Attributes:
        detail: Human-readable description of what went wrong.
        provider: Optional name of the provider/adapter that failed.
        context: Optional structured context (endpoint, status code, etc.).
    """

    detail: str = ""
    provider: str | None = None
    context: Mapping[str, object] = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - trivial
        who = f"{self.provider}: " if self.provider else ""
        return f"ProviderError({who}{self.detail})"


@dataclass(frozen=True)
class TimedOut(AgentError):
    """An operation did not complete within its allotted time bound.

    Attributes:
        detail: Human-readable description of the operation that timed out.
        timeout_s: Optional configured timeout in seconds that was exceeded.
    """

    detail: str = ""
    timeout_s: float | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        bound = f" after {self.timeout_s}s" if self.timeout_s is not None else ""
        return f"TimedOut({self.detail}{bound})"


@dataclass(frozen=True)
class Unverified(AgentError):
    """A contract / artifact could not be verified or retrieved for analysis.

    Attributes:
        detail: Human-readable description of why verification failed.
        subject: Optional identifier of the unverified subject (e.g. address).
    """

    detail: str = ""
    subject: str | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        what = f" [{self.subject}]" if self.subject else ""
        return f"Unverified({self.detail}{what})"


@dataclass(frozen=True)
class NotFound(AgentError):
    """A requested entity (token, pair, record) could not be found.

    Attributes:
        detail: Human-readable description of what was not found.
        identifier: Optional identifier that was searched for.
    """

    detail: str = ""
    identifier: str | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        what = f" [{self.identifier}]" if self.identifier else ""
        return f"NotFound({self.detail}{what})"


@dataclass(frozen=True)
class ConcurrencyLimitExceeded(AgentError):
    """Admitting a Trading_Pair would exceed the concurrent-monitoring cap.

    Carried inside an ``Err`` result when the Monitoring Orchestrator rejects a
    pair because the active-pair registry is already at the 200-pair cap
    (Requirements 1.10, 1.11). The rejection never mutates the registry, so the
    cap invariant is preserved (Property 9).

    Attributes:
        detail: Human-readable description of the rejection.
        limit: The concurrency cap that would have been exceeded.
        identifier: Optional identifier of the pair that was rejected.
    """

    detail: str = ""
    limit: int | None = None
    identifier: str | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        what = f" [{self.identifier}]" if self.identifier else ""
        cap = f" (cap={self.limit})" if self.limit is not None else ""
        return f"ConcurrencyLimitExceeded({self.detail}{what}{cap})"


@dataclass(frozen=True)
class InvalidRange(AgentError):
    """A requested time range is invalid (its start is later than its end).

    Carried inside an ``Err`` result when a range query is rejected before any
    lookup runs, so the rejection never mutates stored data (Requirements 4.7,
    10.4). Reused by both the Metrics_Tracker and the Audit-trail query path.

    Attributes:
        detail: Human-readable description of why the range is invalid.
        start: Optional rejected start instant (ISO string or datetime repr).
        end: Optional rejected end instant.
    """

    detail: str = ""
    start: object | None = None
    end: object | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        span = ""
        if self.start is not None or self.end is not None:
            span = f" [{self.start!r}..{self.end!r}]"
        return f"InvalidRange({self.detail}{span})"


__all__ = [
    "AgentError",
    "ProviderError",
    "TimedOut",
    "Unverified",
    "NotFound",
    "ConcurrencyLimitExceeded",
    "InvalidRange",
]
