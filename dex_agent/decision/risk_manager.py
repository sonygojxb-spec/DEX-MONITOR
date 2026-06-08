"""Risk_Manager: pre-trade buy approval + stop-loss + risk-profile updates.

Design reference: "Risk_Manager" and "Concurrency / shared-state safety".
Maps to Requirements 7.1-7.7.

The Risk_Manager is the mandatory pre-trade gatekeeper (safety-critical). Every
buy passes through :meth:`RiskManager.approve_buy`, which can only ever approve
orders that keep the Token's resulting position size **and** the resulting total
exposure within the configured :class:`~dex_agent.models.RiskProfile` limits and
whose Severity_Rating is acceptable; rejection is the default outcome of any
ambiguity. It also drives stop-loss monitoring and applies Risk_Profile updates
non-retroactively, following the design pseudocode::

    approve_buy(order) -> Decision within 2s:                             # Req 7.3
        if token.severity > profile.max_severity:
            return Reject(SEVERITY_EXCEEDED)                              # Req 7.8
        new_token_size = current_position(token) + order.notional
        new_total = current_total_exposure() + order.notional
        if new_total > profile.max_total_exposure:
            return Reject(TOTAL_EXPOSURE_EXCEEDED)                        # Req 7.4
        if new_token_size > profile.max_position_per_token:
            return Reject(PER_TOKEN_EXCEEDED)                            # Req 7.5
        return Approve                                                    # Req 7.3
    monitor_stop_loss():  # evaluated every <=60s                         # Req 7.6
        for pos in open_positions:
            if unrealized_loss_pct(pos) >= profile.stop_loss_pct:
                request_sell_full(pos) within 5s
    update_profile(new):  # applies only to decisions after completion    # Req 7.7

The decision logic and the stop-loss test are exposed as pure module-level
functions so they can be exercised exactly (iff) by the Correctness Properties:

* :func:`evaluate_buy`        - Property 19 (risk approval predicate, Req 7.2-7.4, 7.7).
* :func:`unrealized_loss_pct` / :func:`should_stop_loss`
                              - Property 21 (stop-loss full-position sell, Req 7.5).

``approve_buy`` is a pure read over shared state: it never mutates positions or
the total-exposure accumulator (Property 20, Req 7.3, 7.4). The actual position
update on a confirmed fill is the Trade_Executor's responsibility (Task 15); the
Risk_Manager exposes ``approve_buy`` and a stop-loss ``sell_requester`` seam so
the Trade_Executor can be wired in later without the Risk_Manager importing it.

Shared-state safety (design "Concurrency / shared-state safety"): the active
:class:`RiskProfile` and the exposure reads are guarded by a single lock so that
exposure checks and profile updates are linearizable. This underpins Property 22
(profile updates apply only to later decisions) and the exposure invariant in
Property 19.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Mapping

from dex_agent.models import (
    Position,
    RiskProfile,
    Severity,
    utc_now_seconds,
)
from dex_agent.repositories.interfaces import (
    PositionRepository,
    RiskProfileRepository,
)


class RejectionReason(Enum):
    """Why the Risk_Manager rejected a buy order (Requirements 7.4, 7.5, 7.8)."""

    SEVERITY_EXCEEDED = "SEVERITY_EXCEEDED"
    TOTAL_EXPOSURE_EXCEEDED = "TOTAL_EXPOSURE_EXCEEDED"
    PER_TOKEN_EXCEEDED = "PER_TOKEN_EXCEEDED"


@dataclass(frozen=True)
class RiskDecision:
    """An approve/reject decision returned by :meth:`RiskManager.approve_buy`.

    Immutable by construction so a decision already returned can never be altered
    by a later Risk_Profile update (Requirement 7.7 / Property 22).

    Attributes:
        approved: ``True`` iff the order keeps both per-Token position and total
            exposure within limits and severity is acceptable.
        reason: The :class:`RejectionReason` when ``approved`` is ``False``; ``None``
            on approval.
    """

    approved: bool
    reason: RejectionReason | None = None

    @classmethod
    def approve(cls) -> "RiskDecision":
        """An approval decision (Req 7.3)."""
        return cls(approved=True, reason=None)

    @classmethod
    def reject(cls, reason: RejectionReason) -> "RiskDecision":
        """A rejection decision carrying the specific ``reason`` (Req 7.4, 7.5, 7.8)."""
        return cls(approved=False, reason=reason)


@dataclass(frozen=True)
class BuyApprovalRequest:
    """A request to approve a buy order (input to :meth:`RiskManager.approve_buy`).

    Attributes:
        token_address: The Token the buy is for; used to look up the current
            per-Token position size.
        notional: The order's notional cost in Quote_Asset terms (``>= 0``); the
            amount the position and total exposure would grow by if filled.
        severity: The Token's current Severity_Rating, checked against the
            profile's maximum acceptable severity (Req 7.8).
        pair_id: Optional Trading_Pair identifier (informational).
    """

    token_address: str
    notional: Decimal
    severity: Severity
    pair_id: str | None = None


@dataclass(frozen=True)
class SellRequest:
    """A request to sell a full Position, raised by stop-loss (Requirement 7.6).

    Attributes:
        pair_id: The Trading_Pair whose Position should be exited.
        token_address: The Token held.
        quantity: The full Position quantity to sell.
        reason: Why the sell was requested (always ``"STOP_LOSS"`` here).
        requested_at: When the request was raised (second-precision UTC).
    """

    pair_id: str
    token_address: str
    quantity: Decimal
    reason: str
    requested_at: datetime


# A sink that receives a stop-loss :class:`SellRequest`. Task 15 wires the real
# Trade_Executor behind this seam; tests inject a recording sink (Req 7.5).
SellRequester = Callable[[SellRequest], None]

# A callable returning the current price for a Trading_Pair, or ``None`` when no
# price is available (stop-loss is skipped for that pair). Injected so the
# Risk_Manager stays decoupled from the market-data layer.
PriceLookup = Callable[[str], Decimal | None]


# ---------------------------------------------------------------------------
# Pure decision logic (exercised exactly by Properties 19 & 21)
# ---------------------------------------------------------------------------


def evaluate_buy(
    *,
    severity: Severity,
    current_token_notional: Decimal,
    current_total_notional: Decimal,
    order_notional: Decimal,
    profile: RiskProfile,
) -> RiskDecision:
    """Pure pre-trade approval predicate (Req 7.2-7.4, 7.7, 7.8; Property 19).

    Approves the order **if and only if** all three hold:

    * the Token's ``severity`` is at or below ``profile.max_acceptable_severity``;
    * the resulting total exposure (``current_total_notional + order_notional``)
      is ``<= profile.max_total_exposure``; and
    * the resulting per-Token position size (``current_token_notional +
      order_notional``) is ``<= profile.max_position_per_token``.

    Otherwise it rejects with the corresponding :class:`RejectionReason`. When
    more than one limit is violated the reason follows the design's evaluation
    order (severity, then total exposure, then per-Token), so the decision is
    deterministic.
    """
    if severity > profile.max_acceptable_severity:
        return RiskDecision.reject(RejectionReason.SEVERITY_EXCEEDED)

    new_total = current_total_notional + order_notional
    if new_total > profile.max_total_exposure:
        return RiskDecision.reject(RejectionReason.TOTAL_EXPOSURE_EXCEEDED)

    new_token = current_token_notional + order_notional
    if new_token > profile.max_position_per_token:
        return RiskDecision.reject(RejectionReason.PER_TOKEN_EXCEEDED)

    return RiskDecision.approve()


def unrealized_loss_pct(avg_entry_price: Decimal, current_price: Decimal) -> Decimal:
    """Percentage by which a Position is *down* from its average entry price.

    Returns ``100 * (avg_entry_price - current_price) / avg_entry_price`` when the
    price has fallen, and ``0`` when the price held steady or rose (no unrealized
    loss). Returns ``0`` when ``avg_entry_price <= 0`` (no meaningful basis).
    """
    if avg_entry_price <= 0:
        return Decimal(0)
    loss = (avg_entry_price - current_price) / avg_entry_price * Decimal(100)
    return loss if loss > 0 else Decimal(0)


def should_stop_loss(
    avg_entry_price: Decimal,
    current_price: Decimal,
    stop_loss_pct: Decimal,
) -> bool:
    """Stop-loss trigger predicate (Req 7.5; Property 21).

    True **iff** the Position's unrealized loss percentage *reaches or exceeds*
    the configured stop-loss percentage::

        stop_loss  <=>  unrealized_loss_pct(entry, price) >= stop_loss_pct

    While the loss is below the stop-loss percentage no sell is requested.
    """
    return unrealized_loss_pct(avg_entry_price, current_price) >= stop_loss_pct


# ---------------------------------------------------------------------------
# Risk_Manager
# ---------------------------------------------------------------------------


class RiskManager:
    """Pre-trade gatekeeper + stop-loss driver (Requirements 7.1-7.8).

    Args:
        profile: The active :class:`RiskProfile` (per-order size, per-Token and
            total exposure limits, max acceptable severity, stop-loss percent).
        positions: The :class:`PositionRepository` providing the open positions
            used to compute current per-Token and total exposure.
        sell_requester: Sink that receives a stop-loss :class:`SellRequest`
            (Req 7.5). Task 15 wires the real Trade_Executor here; defaults to a
            no-op so stop-loss can be inspected via :meth:`monitor_stop_loss`'s
            return value alone.
        profile_repo: Optional :class:`RiskProfileRepository`; when supplied,
            :meth:`update_profile` persists the new profile (latest-wins).
        eval_interval_s: The stop-loss evaluation interval in seconds; must be
            ``<= 60`` (Req 7.5). Informational - the Orchestrator polls
            :meth:`monitor_stop_loss` at or below this cadence.
        clock: Callable returning the current second-precision UTC timestamp used
            to stamp sell requests; injectable for tests.
    """

    #: The maximum permitted stop-loss evaluation interval (Req 7.5).
    MAX_EVAL_INTERVAL_S: float = 60.0

    def __init__(
        self,
        profile: RiskProfile,
        positions: PositionRepository,
        *,
        sell_requester: SellRequester | None = None,
        profile_repo: RiskProfileRepository | None = None,
        eval_interval_s: float = 60.0,
        clock: Callable[[], datetime] = utc_now_seconds,
    ) -> None:
        if eval_interval_s <= 0 or eval_interval_s > self.MAX_EVAL_INTERVAL_S:
            raise ValueError(
                "eval_interval_s must be in (0, 60] seconds (Req 7.5); "
                f"got {eval_interval_s}"
            )
        self._profile = profile
        self._positions = positions
        self._sell_requester = sell_requester
        self._profile_repo = profile_repo
        self._eval_interval_s = eval_interval_s
        self._clock = clock
        # Single lock makes profile reads/updates and exposure checks
        # linearizable (design "Concurrency / shared-state safety").
        self._lock = threading.Lock()

    @property
    def profile(self) -> RiskProfile:
        """The active :class:`RiskProfile` (snapshot read)."""
        with self._lock:
            return self._profile

    @property
    def eval_interval_s(self) -> float:
        """The stop-loss evaluation interval in seconds (``<= 60``; Req 7.5)."""
        return self._eval_interval_s

    # ------------------------------------------------------------------
    # Pre-trade approval (Req 7.2-7.4, 7.7, 7.8)
    # ------------------------------------------------------------------
    def approve_buy(self, request: BuyApprovalRequest) -> RiskDecision:
        """Approve or reject a buy order within the decision bound (Req 7.3).

        Reads the current per-Token and total exposure from the open positions and
        applies :func:`evaluate_buy` against the active profile. The whole read +
        decision happens under the lock so it is linearizable against a concurrent
        :meth:`update_profile` (Req 7.7). It is a pure read: no position or
        exposure state is mutated, so a rejection leaves all positions and total
        exposure unchanged (Req 7.3, 7.4; Property 20). The body is synchronous and
        allocation-free of any I/O, so it returns well within the 2-second bound.
        """
        with self._lock:
            profile = self._profile
            open_positions = self._positions.list_open()
            current_token = _token_notional(open_positions, request.token_address)
            current_total = _total_notional(open_positions)
            return evaluate_buy(
                severity=request.severity,
                current_token_notional=current_token,
                current_total_notional=current_total,
                order_notional=request.notional,
                profile=profile,
            )

    # ------------------------------------------------------------------
    # Stop-loss monitoring (Req 7.5)
    # ------------------------------------------------------------------
    def monitor_stop_loss(
        self,
        price_for: PriceLookup,
        *,
        now: datetime | None = None,
    ) -> list[SellRequest]:
        """Request a full-position sell for every Position at/over its stop-loss.

        For each open Position, computes the unrealized loss percentage from the
        Position's average entry price and the current price (via ``price_for``);
        when the loss *reaches or exceeds* the active profile's stop-loss percent
        (:func:`should_stop_loss`), a :class:`SellRequest` for the **full** Position
        quantity is built, dispatched through the ``sell_requester`` seam, and
        returned (Req 7.5). Positions with no available price are skipped. Intended
        to be polled at an interval of at most :attr:`eval_interval_s` (``<= 60s``).
        """
        ts = now or self._clock()
        with self._lock:
            stop_loss_pct = self._profile.stop_loss_pct
            open_positions = self._positions.list_open()

        requests: list[SellRequest] = []
        for position in open_positions:
            price = price_for(position.pair_id)
            if price is None:
                continue
            if should_stop_loss(position.avg_entry_price, price, stop_loss_pct):
                request = SellRequest(
                    pair_id=position.pair_id,
                    token_address=position.token_address,
                    quantity=position.quantity,
                    reason="STOP_LOSS",
                    requested_at=ts,
                )
                requests.append(request)
                if self._sell_requester is not None:
                    self._sell_requester(request)
        return requests

    # ------------------------------------------------------------------
    # Non-retroactive profile updates (Req 7.6)
    # ------------------------------------------------------------------
    def update_profile(self, new_profile: RiskProfile) -> RiskProfile:
        """Swap in an updated Risk_Profile, applied only to later decisions (Req 7.6).

        The swap is performed under the lock, so any approval decision already
        returned was computed against the previous profile and is never altered;
        only decisions *initiated after this call completes* see ``new_profile``.
        When a :class:`RiskProfileRepository` was injected the new profile is also
        persisted (latest-wins).
        """
        with self._lock:
            self._profile = new_profile
            if self._profile_repo is not None:
                self._profile_repo.save(new_profile)
            return self._profile


# ---------------------------------------------------------------------------
# Exposure helpers (pure reads over a snapshot of open positions)
# ---------------------------------------------------------------------------


def _token_notional(positions: list[Position], token_address: str) -> Decimal:
    """Sum the notional cost of open positions in ``token_address`` (per-Token size)."""
    total = Decimal(0)
    for position in positions:
        if position.token_address == token_address:
            total += position.notional_cost
    return total


def _total_notional(positions: list[Position]) -> Decimal:
    """Sum the notional cost across all open positions (current total exposure)."""
    total = Decimal(0)
    for position in positions:
        total += position.notional_cost
    return total


__all__ = [
    "RejectionReason",
    "RiskDecision",
    "BuyApprovalRequest",
    "SellRequest",
    "SellRequester",
    "PriceLookup",
    "RiskManager",
    "evaluate_buy",
    "unrealized_loss_pct",
    "should_stop_loss",
]
