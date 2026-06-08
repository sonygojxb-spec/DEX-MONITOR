"""Decision layer: Signal_Engine and Risk_Manager.

Public names are re-exported here for convenient importing, e.g.
``from dex_agent.decision import SignalEngine``.
"""

from __future__ import annotations

from dex_agent.decision.risk_manager import (
    BuyApprovalRequest,
    PriceLookup,
    RejectionReason,
    RiskDecision,
    RiskManager,
    SellRequest,
    SellRequester,
    evaluate_buy,
    should_stop_loss,
    unrealized_loss_pct,
)
from dex_agent.decision.signal_engine import (
    AlertSink,
    ComputeOutcome,
    PositionHeld,
    SignalEngine,
    SignalInputs,
    SkipRecord,
    is_dump,
    is_eligible,
    is_rug_pull,
    liquidity_drop_pct,
    score_entry,
)

__all__ = [
    "SignalEngine",
    "SignalInputs",
    "SkipRecord",
    "ComputeOutcome",
    "PositionHeld",
    "AlertSink",
    "is_eligible",
    "is_rug_pull",
    "is_dump",
    "liquidity_drop_pct",
    "score_entry",
    # Risk_Manager (Task 13)
    "RiskManager",
    "RiskDecision",
    "RejectionReason",
    "BuyApprovalRequest",
    "SellRequest",
    "SellRequester",
    "PriceLookup",
    "evaluate_buy",
    "unrealized_loss_pct",
    "should_stop_loss",
]
