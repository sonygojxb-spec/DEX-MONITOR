"""Execution layer: Trade_Executor (safety-critical order execution).

Public names are re-exported here for convenient importing, e.g.
``from dex_agent.execution import TradeExecutor``.
"""

from __future__ import annotations

from dex_agent.execution.trade_executor import (
    AlertSink,
    AutomatedTradingFlag,
    BalanceLookup,
    ExecutionResult,
    ExecutionStatus,
    SeverityLookup,
    Signer,
    TradeExecutor,
    TradingGate,
    cap_to_risk_limits,
    resolve_order_size,
)

__all__ = [
    "TradeExecutor",
    "ExecutionResult",
    "ExecutionStatus",
    "Signer",
    "TradingGate",
    "AutomatedTradingFlag",
    "SeverityLookup",
    "BalanceLookup",
    "AlertSink",
    "resolve_order_size",
    "cap_to_risk_limits",
]
