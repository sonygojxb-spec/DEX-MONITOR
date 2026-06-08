"""Persistence abstractions and in-memory repository implementations.

Design reference: "Persistence Layer (repositories)" and "Concurrency /
Idempotent persistence". This sub-package defines:

* **Repository interfaces** (:mod:`~dex_agent.repositories.interfaces`) for the
  twelve durable stores in the design's persistence diagram - Tokens, Pairs,
  Watchlist, SecurityEval, WalletAnalysis, Metrics time-series, Signals,
  Positions, RiskProfile, Config, Audit, and Authorization. All components
  depend only on these abstractions; concrete backends are injected.
* **In-memory implementations** (:mod:`~dex_agent.repositories.memory`) with
  idempotent appends so retries cannot create duplicate records.
* **Shared query primitives** (:mod:`~dex_agent.repositories.query`):
  :func:`entries_in_range` (inclusive, ascending range query) and
  :func:`older_than` (strictly-older-than retention boundary), reused by both
  the Metrics and Audit repositories.

Public names are re-exported here for convenient importing, e.g.
``from dex_agent.repositories import InMemoryMetricsRepository, entries_in_range``.
"""

from __future__ import annotations

from dex_agent.repositories.interfaces import (
    AuditRepository,
    AuthorizationRepository,
    ConfigRepository,
    MetricsRepository,
    OrderRepository,
    PairRepository,
    PositionRepository,
    RiskProfileRepository,
    SecurityEvalRepository,
    SignalRepository,
    TokenRepository,
    WalletAnalysisRepository,
    WatchlistRepository,
)
from dex_agent.repositories.memory import (
    InMemoryAuditRepository,
    InMemoryAuthorizationRepository,
    InMemoryConfigRepository,
    InMemoryMetricsRepository,
    InMemoryOrderRepository,
    InMemoryPairRepository,
    InMemoryPositionRepository,
    InMemoryRiskProfileRepository,
    InMemorySecurityEvalRepository,
    InMemorySignalRepository,
    InMemoryTokenRepository,
    InMemoryWalletAnalysisRepository,
    InMemoryWatchlistRepository,
)
from dex_agent.repositories.query import entries_in_range, older_than

__all__ = [
    # shared query primitives
    "entries_in_range",
    "older_than",
    # interfaces
    "TokenRepository",
    "PairRepository",
    "WatchlistRepository",
    "SecurityEvalRepository",
    "WalletAnalysisRepository",
    "SignalRepository",
    "MetricsRepository",
    "PositionRepository",
    "OrderRepository",
    "RiskProfileRepository",
    "ConfigRepository",
    "AuditRepository",
    "AuthorizationRepository",
    # in-memory implementations
    "InMemoryTokenRepository",
    "InMemoryPairRepository",
    "InMemoryWatchlistRepository",
    "InMemorySecurityEvalRepository",
    "InMemoryWalletAnalysisRepository",
    "InMemorySignalRepository",
    "InMemoryMetricsRepository",
    "InMemoryPositionRepository",
    "InMemoryOrderRepository",
    "InMemoryRiskProfileRepository",
    "InMemoryConfigRepository",
    "InMemoryAuditRepository",
    "InMemoryAuthorizationRepository",
]
