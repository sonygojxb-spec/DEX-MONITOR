"""Analysis layer: Security_Inspector, Backend_Analyzer, Metrics_Tracker.

Public names are re-exported here for convenient importing, e.g.
``from dex_agent.analysis import SecurityInspector``.
"""

from __future__ import annotations

from dex_agent.analysis.backend_analyzer import (
    DEFAULT_BOT_HEURISTICS,
    WINDOW_MINUTES_MAX,
    WINDOW_MINUTES_MIN,
    AlertSink,
    BackendAnalyzer,
    BotHeuristics,
)
from dex_agent.analysis.metrics_tracker import (
    FALLBACK_AUDIT_PROVIDER,
    PERIOD_KINDS,
    PRIMARY_AUDIT_PROVIDER,
    REFRESH_KINDS,
    MetricsTracker,
    RecordResult,
    build_audit_info,
)
from dex_agent.analysis.security_inspector import (
    ISSUE_SEVERITY,
    SecurityInspector,
)

__all__ = [
    "SecurityInspector",
    "ISSUE_SEVERITY",
    "BackendAnalyzer",
    "BotHeuristics",
    "DEFAULT_BOT_HEURISTICS",
    "AlertSink",
    "WINDOW_MINUTES_MIN",
    "WINDOW_MINUTES_MAX",
    "MetricsTracker",
    "RecordResult",
    "build_audit_info",
    "PRIMARY_AUDIT_PROVIDER",
    "FALLBACK_AUDIT_PROVIDER",
    "REFRESH_KINDS",
    "PERIOD_KINDS",
]
