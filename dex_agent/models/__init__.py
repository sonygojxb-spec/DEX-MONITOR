"""Data models and enums for the DEX Trading Agent.

This sub-package implements the design's "Data Models" section as immutable
(frozen) dataclasses and enums, organized into cohesive modules:

* :mod:`~dex_agent.models.severity`   - ``Severity`` ordered enum + ``max_by_ordinal``
* :mod:`~dex_agent.models.market`     - identity & market models (Network, Token,
  TradingPair, WatchlistEntry, PairSnapshot, AuditInfo) + quote-asset validation
* :mod:`~dex_agent.models.security`   - SecurityIssue / SecurityEvaluation
* :mod:`~dex_agent.models.wallet`     - WalletClassification / WalletAnalysis / HolderBalance
* :mod:`~dex_agent.models.metrics`    - MetricKind / MetricEntry / MISSING
* :mod:`~dex_agent.models.signal`     - SignalType / ExitClass / Signal
* :mod:`~dex_agent.models.position`   - Position / PerOrderSize / RiskProfile
* :mod:`~dex_agent.models.order`      - OrderKind / OrderStatus / OrderRecord / InFlightRegistry
* :mod:`~dex_agent.models.config`     - Configuration / TimeWindow
* :mod:`~dex_agent.models.audit`      - ActionType / AuditRecord
* :mod:`~dex_agent.models.auth`       - AuthStatus / AuthorizationRecord
* :mod:`~dex_agent.models.timestamps` - UTC precision helpers

The public names are re-exported here for convenient importing, e.g.
``from dex_agent.models import Severity, TradingPair``.
"""

from __future__ import annotations

from dex_agent.models.audit import ActionType, AuditRecord
from dex_agent.models.auth import AuthorizationRecord, AuthStatus
from dex_agent.models.config import Configuration, TimeWindow
from dex_agent.models.market import (
    SUPPORTED_QUOTE_ASSETS,
    AuditInfo,
    Network,
    PairSnapshot,
    Token,
    TradingPair,
    WatchlistEntry,
    WatchlistSource,
    make_trading_pair,
)
from dex_agent.models.metrics import (
    MISSING,
    MetricEntry,
    MetricKind,
    MetricValue,
)
from dex_agent.models.order import (
    TERMINAL_ORDER_STATUS,
    InFlightRegistry,
    OrderKind,
    OrderRecord,
    OrderStatus,
)
from dex_agent.models.position import (
    PerOrderSize,
    PerOrderSizeKind,
    Position,
    PositionStatus,
    RiskProfile,
)
from dex_agent.models.security import (
    SecurityEvaluation,
    SecurityIssue,
    SecurityIssueType,
)
from dex_agent.models.severity import (
    SEVERITY_ORDER,
    Severity,
    max_by_ordinal,
)
from dex_agent.models.signal import ExitClass, Signal, SignalType
from dex_agent.models.timestamps import (
    to_millis_precision,
    to_second_precision,
    utc_now,
    utc_now_millis,
    utc_now_seconds,
)
from dex_agent.models.wallet import (
    HolderBalance,
    WalletAnalysis,
    WalletClassification,
)

__all__ = [
    # severity
    "Severity",
    "SEVERITY_ORDER",
    "max_by_ordinal",
    # market / identity
    "Network",
    "SUPPORTED_QUOTE_ASSETS",
    "WatchlistSource",
    "AuditInfo",
    "Token",
    "TradingPair",
    "WatchlistEntry",
    "PairSnapshot",
    "make_trading_pair",
    # security
    "SecurityIssueType",
    "SecurityIssue",
    "SecurityEvaluation",
    # wallet
    "WalletClassification",
    "WalletAnalysis",
    "HolderBalance",
    # metrics
    "MetricKind",
    "MISSING",
    "MetricValue",
    "MetricEntry",
    # signals
    "SignalType",
    "ExitClass",
    "Signal",
    # positions & risk
    "PositionStatus",
    "Position",
    "PerOrderSizeKind",
    "PerOrderSize",
    "RiskProfile",
    # orders / execution
    "OrderKind",
    "OrderStatus",
    "TERMINAL_ORDER_STATUS",
    "OrderRecord",
    "InFlightRegistry",
    # config
    "TimeWindow",
    "Configuration",
    # audit
    "ActionType",
    "AuditRecord",
    # auth
    "AuthStatus",
    "AuthorizationRecord",
    # timestamps
    "utc_now",
    "utc_now_seconds",
    "utc_now_millis",
    "to_second_precision",
    "to_millis_precision",
]
