"""Trade_Executor: safety-critical order execution (Task 15).

Design reference: "Trade_Executor", "Trade Execution with Risk Approval",
"Signer / Key Handling", "Security Considerations", and "Concurrency". Maps to
Requirements 6.1-6.10 (with 2.3, 7.1, 7.2, 8.1, 11.3, 12.1-12.4).

The Trade_Executor is the *only* component that can authorize value transfer, so
it is built around a set of hard gates that must all pass before any order is
submitted (and before the injected signer is ever invoked). Following the design
pseudocode::

    submit_entry(pair, order):
        if not (authz.trading_enabled() and automated_trading_enabled()):
            send recommendation; return MONITORING_ONLY                  # Req 6.3, 11.3
        if severity_for(token) is None: return NO_SEVERITY_RATING        # Req 2.3
        if position_open(pair) or in_flight.has_in_flight(pair):
            return SUPPRESSED_DUPLICATE_ENTRY                            # Req 12.1, 12.2
        size = resolve_order_size(profile.per_order_size, pair)          # Req 6.9
        size = cap_to_risk_limits(size, token, profile)                  # Req 6.9 (per-token+total)
        if size <= 0 or not risk_manager.approve_buy(...).approved:
            return RISK_REJECTED                                         # Req 7.2-7.4
        if available_quote_balance() < size:
            record(INSUFFICIENT_BALANCE); notify; return ...            # Req 6.10
        return _dispatch(pair, BUY, order, size)

    submit_exit(pair, order):
        if not (authz.trading_enabled() and automated_trading_enabled()):
            send recommendation; return MONITORING_ONLY                  # Req 6.3, 11.3
        if in_flight.has_in_flight(pair) and marker.kind == SELL:
            return SUPPRESSED_DUPLICATE_SELL                            # Req 12.3
        return _dispatch(pair, SELL, order)

    _dispatch(pair, kind, order, size):
        order = order with max_slippage + signed_transaction             # Req 6.4, signer
        submitted = venue.submit_order(order)                            # only after all gates
        if submission fails: record FAILED; notify <=5s; NO state change # Req 6.7
        in_flight.mark(pair, submitted)                                  # Req 12.1
        conf = venue.poll_confirmation(tx, timeout)                      # Req 6.6 (10..600s)
        if timed out / not confirmed: record TIMED_OUT/FAILED; clear; notify; NO change # Req 6.6
        if executed_slippage > max_slippage: record CANCELLED; clear; notify; NO change # Req 6.8
        on confirmation: record type/price/qty/fee/tx_id+ts; clear; update position; notify # Req 6.5

**Signer / key handling (design "Signer / Key Handling").** The executor holds an
injected :class:`Signer` capability (an env keypair, or an external/remote
KMS/HSM signer). It is invoked *only* inside :meth:`_dispatch`, i.e. only after
every gate has passed, so the signing path is reachable only when an authorized
wallet is connected AND automated trading is enabled (Property 23). The signer
returns an opaque *signed transaction*; only that signed string crosses the
:class:`~dex_agent.providers.interfaces.TradeVenueProvider` boundary - never raw
key material - and the executor never persists or logs key material.

**No-partial-mutation guarantee.** Any non-confirmed outcome (monitoring-only,
severity reject, duplicate suppression, insufficient balance, risk reject,
submission failure, timeout, slippage breach) leaves the Position store and the
wallet balance completely unchanged (Req 6.6, 6.7, 6.8; Property 25). State is
mutated *only* on a confirmed, within-slippage fill.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Callable

from dex_agent.decision.risk_manager import (
    BuyApprovalRequest,
    RejectionReason,
    RiskManager,
)
from dex_agent.models import (
    InFlightRegistry,
    OrderKind,
    OrderRecord,
    OrderStatus,
    Position,
    PerOrderSizeKind,
    PositionStatus,
    Severity,
    utc_now_seconds,
)
from dex_agent.providers.interfaces import (
    Alert,
    Confirmation,
    OrderRequest,
    SubmittedOrder,
    TradeVenueProvider,
)
from dex_agent.repositories.interfaces import (
    OrderRepository,
    PositionRepository,
)
from dex_agent.result import Result

# ---------------------------------------------------------------------------
# Injected seams
# ---------------------------------------------------------------------------

# Reports whether an authorized trading wallet is connected (Req 11.3). The
# Authorization_Manager (Task 14) is wired here; tests inject a stub.
TradingGate = Callable[[], bool]

# Reports whether the user has enabled automated trading (Req 6.3). Sourced from
# the validated Configuration; defaults to false (monitoring-only).
AutomatedTradingFlag = Callable[[], bool]

# Returns the Token's currently assigned Severity_Rating, or ``None`` when no
# rating has been assigned yet (Req 2.3). ``Severity.NONE`` is an *assigned*
# rating and is distinct from ``None`` (not assigned).
SeverityLookup = Callable[[str], "Severity | None"]

# Returns the available Quote_Asset wallet balance (Req 6.9 percent sizing /
# Req 6.10 sufficiency). Injected so the executor stays decoupled from the wallet.
BalanceLookup = Callable[[], Decimal]

# A sink that delivers an :class:`Alert` (recommendation / failure / confirmation
# notifications). Task 17 wires the real Notifier behind this seam; tests inject
# a recording sink (Req 6.3, 6.7, 6.10, 8.1).
AlertSink = Callable[[Alert], None]


class Signer(ABC):
    """An injected signing capability (design "Signer / Key Handling").

    Concrete signers wrap an env-provided Solana keypair or an external/remote
    KMS/HSM signing service. The executor invokes :meth:`sign_transaction` only
    after every gate has passed; the returned *signed transaction* is the only
    artifact that crosses the trade-venue boundary. Implementations MUST NOT
    expose, persist, or log raw private-key material.
    """

    @property
    @abstractmethod
    def public_key(self) -> str:
        """The signer's public address (safe to log; never the private key)."""

    @abstractmethod
    def sign_transaction(self, serialized_tx: str) -> str:
        """Sign ``serialized_tx`` and return an opaque signed transaction.

        ``serialized_tx`` is the unsigned serialized transaction (in live wiring,
        the Jupiter Swap API output). The return value carries no key material.
        """


# ---------------------------------------------------------------------------
# Execution outcomes
# ---------------------------------------------------------------------------


class ExecutionStatus(Enum):
    """The outcome of a :meth:`TradeExecutor.submit_entry`/``submit_exit`` call."""

    # ----- confirmed (the only state-mutating outcome) -----
    CONFIRMED = "CONFIRMED"
    # ----- deliberate no-ops (no order submitted) -----
    MONITORING_ONLY = "MONITORING_ONLY"                       # Req 6.3, 11.3
    NO_SEVERITY_RATING = "NO_SEVERITY_RATING"                 # Req 2.3
    SUPPRESSED_DUPLICATE_ENTRY = "SUPPRESSED_DUPLICATE_ENTRY"  # Req 12.1, 12.2
    SUPPRESSED_DUPLICATE_SELL = "SUPPRESSED_DUPLICATE_SELL"    # Req 12.3
    RISK_REJECTED = "RISK_REJECTED"                           # Req 7.2-7.4
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"             # Req 6.10
    # ----- submitted but not confirmed (cancelled, no state change) -----
    SUBMISSION_FAILED = "SUBMISSION_FAILED"                   # Req 6.7
    TIMED_OUT = "TIMED_OUT"                                   # Req 6.6
    SLIPPAGE_EXCEEDED = "SLIPPAGE_EXCEEDED"                   # Req 6.8

    def submitted_to_venue(self) -> bool:
        """True iff an order actually reached the trade venue."""
        return self in {
            ExecutionStatus.CONFIRMED,
            ExecutionStatus.SUBMISSION_FAILED,
            ExecutionStatus.TIMED_OUT,
            ExecutionStatus.SLIPPAGE_EXCEEDED,
        }

    def mutated_state(self) -> bool:
        """True iff this outcome changed Position/balance state (confirmed only)."""
        return self is ExecutionStatus.CONFIRMED


@dataclass(frozen=True)
class ExecutionResult:
    """The result of an entry/exit attempt.

    Attributes:
        status: The :class:`ExecutionStatus` describing the outcome.
        submitted: Whether an order was submitted to the trade venue.
        order: The recorded :class:`OrderRecord` for outcomes that produced one
            (confirmed / failed / timed-out / slippage-cancelled / insufficient
            balance); ``None`` for pure gate no-ops.
        reason: A human-readable reason for non-confirmed outcomes.
        risk_reason: The Risk_Manager :class:`RejectionReason` when the order was
            rejected by risk approval.
        prepared_size: The capped order size that was prepared (buys only).
    """

    status: ExecutionStatus
    submitted: bool
    order: OrderRecord | None = None
    reason: str | None = None
    risk_reason: RejectionReason | None = None
    prepared_size: Decimal | None = None

    @property
    def confirmed(self) -> bool:
        return self.status is ExecutionStatus.CONFIRMED


# ---------------------------------------------------------------------------
# Pure sizing helpers (exercised by Property 34)
# ---------------------------------------------------------------------------


def resolve_order_size(
    per_order_size,
    *,
    available_quote_balance: Decimal,
) -> Decimal:
    """Derive the raw buy size from the Per_Order_Size (Req 6.9, 7.2).

    * ``FIXED_QUOTE``     -> the fixed Quote_Asset amount.
    * ``PERCENT_BALANCE`` -> ``available_quote_balance * value / 100``.
    """
    if per_order_size.kind == PerOrderSizeKind.FIXED_QUOTE:
        return per_order_size.value
    return available_quote_balance * per_order_size.value / Decimal(100)


def cap_to_risk_limits(
    size: Decimal,
    *,
    current_token_notional: Decimal,
    current_total_notional: Decimal,
    max_position_per_token: Decimal,
    max_total_exposure: Decimal,
) -> Decimal:
    """Cap ``size`` so the resulting per-Token and total exposure stay in limits.

    Returns ``min(size, per_token_room, total_room)`` where each *room* is the
    remaining headroom under the corresponding Risk_Profile limit (never
    negative). The capped size therefore keeps both ``current_token + size <=
    max_position_per_token`` and ``current_total + size <= max_total_exposure``
    (Req 6.9, 7.1, 7.2).
    """
    per_token_room = max(Decimal(0), max_position_per_token - current_token_notional)
    total_room = max(Decimal(0), max_total_exposure - current_total_notional)
    capped = min(size, per_token_room, total_room)
    return capped if capped > 0 else Decimal(0)


# ---------------------------------------------------------------------------
# Trade_Executor
# ---------------------------------------------------------------------------


class TradeExecutor:
    """Safety-critical order execution gated by authorization + risk (Req 6.x)."""

    #: Confirmation-timeout bounds in seconds (Req 6.6).
    MIN_CONFIRMATION_TIMEOUT_S: int = 10
    MAX_CONFIRMATION_TIMEOUT_S: int = 600

    def __init__(
        self,
        *,
        venue: TradeVenueProvider,
        signer: Signer,
        risk_manager: RiskManager,
        positions: PositionRepository,
        orders: OrderRepository,
        trading_enabled: TradingGate,
        automated_trading_enabled: AutomatedTradingFlag,
        severity_for: SeverityLookup,
        available_quote_balance: BalanceLookup,
        max_slippage: Decimal,
        alert_sink: AlertSink | None = None,
        in_flight: InFlightRegistry | None = None,
        confirmation_timeout_s: int = 60,
        clock: Callable[[], datetime] = utc_now_seconds,
    ) -> None:
        if not (
            self.MIN_CONFIRMATION_TIMEOUT_S
            <= confirmation_timeout_s
            <= self.MAX_CONFIRMATION_TIMEOUT_S
        ):
            raise ValueError(
                "confirmation_timeout_s must be in [10, 600] seconds (Req 6.6); "
                f"got {confirmation_timeout_s}"
            )
        self._venue = venue
        self._signer = signer
        self._risk = risk_manager
        self._positions = positions
        self._orders = orders
        self._trading_enabled = trading_enabled
        self._automated_trading_enabled = automated_trading_enabled
        self._severity_for = severity_for
        self._balance = available_quote_balance
        self._max_slippage = max_slippage
        self._alert_sink = alert_sink
        self._in_flight = in_flight if in_flight is not None else InFlightRegistry()
        self._timeout = timedelta(seconds=confirmation_timeout_s)
        self._clock = clock

    # -- introspection -----------------------------------------------------

    @property
    def in_flight(self) -> InFlightRegistry:
        """The in-flight registry projection (at most one order per pair)."""
        return self._in_flight

    def _gate_open(self) -> bool:
        """Both gates: authorized wallet connected AND automated trading on."""
        return bool(self._trading_enabled()) and bool(
            self._automated_trading_enabled()
        )

    # -- entry (buy) -------------------------------------------------------

    def submit_entry(self, order: OrderRequest) -> ExecutionResult:
        """Attempt to submit a buy for an eligible entry signal (Req 6.1, 6.9).

        Applies, in order: the monitoring-only gate (Req 6.3, 11.3), the
        severity-presence guard (Req 2.3), the in-flight/idempotency guard
        (Req 12.1, 12.2), position sizing capped to risk limits (Req 6.9),
        independent Risk_Manager approval (Req 7.2-7.4), and the balance
        sufficiency check (Req 6.10). Only when all pass does it dispatch the
        order (and only then is the signer invoked).
        """
        pair_id = order.pair_id
        token_address = order.output_mint  # the Token being bought

        # ---- monitoring-only gate (Req 6.3, 11.3; Property 23) ----
        if not self._gate_open():
            self._send_recommendation(pair_id, OrderKind.BUY)
            return ExecutionResult(ExecutionStatus.MONITORING_ONLY, submitted=False)

        # ---- severity-presence guard (Req 2.3; Property 4) ----
        if self._severity_for(token_address) is None:
            return ExecutionResult(
                ExecutionStatus.NO_SEVERITY_RATING,
                submitted=False,
                reason="no Severity_Rating assigned to token",
            )

        # ---- in-flight / idempotency guard (Req 12.1, 12.2; Property 32) ----
        if self._position_open(pair_id) or self._in_flight.has_in_flight(pair_id):
            return ExecutionResult(
                ExecutionStatus.SUPPRESSED_DUPLICATE_ENTRY,
                submitted=False,
                reason="position open or order already in flight",
            )

        # ---- position sizing from Per_Order_Size, capped to risk limits ----
        profile = self._risk.profile
        current_token = self._token_notional(token_address)
        current_total = self._total_notional()
        raw_size = resolve_order_size(
            profile.per_order_size,
            available_quote_balance=self._balance(),
        )
        size = cap_to_risk_limits(
            raw_size,
            current_token_notional=current_token,
            current_total_notional=current_total,
            max_position_per_token=profile.max_position_per_token,
            max_total_exposure=profile.max_total_exposure,
        )
        if size <= 0:
            return ExecutionResult(
                ExecutionStatus.RISK_REJECTED,
                submitted=False,
                reason="no room within Risk_Profile limits",
                prepared_size=Decimal(0),
            )

        # ---- independent Risk_Manager approval (Req 7.2-7.4; Property 19/20) ----
        severity = self._severity_for(token_address) or Severity.NONE
        decision = self._risk.approve_buy(
            BuyApprovalRequest(
                token_address=token_address,
                notional=size,
                severity=severity,
                pair_id=pair_id,
            )
        )
        if not decision.approved:
            return ExecutionResult(
                ExecutionStatus.RISK_REJECTED,
                submitted=False,
                reason=str(decision.reason.value if decision.reason else "rejected"),
                risk_reason=decision.reason,
                prepared_size=size,
            )

        # ---- balance sufficiency (Req 6.10) ----
        if self._balance() < size:
            rec = self._record_order(
                pair_id=pair_id,
                kind=OrderKind.BUY,
                requested_qty=size,
                notional=size,
                status=OrderStatus.CANCELLED,
                reason="INSUFFICIENT_BALANCE",
            )
            self._notify_failure(pair_id, "INSUFFICIENT_BALANCE")
            return ExecutionResult(
                ExecutionStatus.INSUFFICIENT_BALANCE,
                submitted=False,
                order=rec,
                reason="insufficient Quote_Asset balance",
                prepared_size=size,
            )

        return self._dispatch(
            pair_id=pair_id,
            kind=OrderKind.BUY,
            token_address=token_address,
            order=replace(order, amount=size),
            notional=size,
            requested_qty=size,
        )

    # -- exit (sell) -------------------------------------------------------

    def submit_exit(self, order: OrderRequest) -> ExecutionResult:
        """Attempt to submit a sell for an exit signal (Req 6.2).

        Applies the monitoring-only gate (Req 6.3, 11.3) and the duplicate-sell
        guard (Req 12.3): no second sell is submitted while a sell is already in
        flight for the pair. A confirmed sell closes the held Position.
        """
        pair_id = order.pair_id
        token_address = order.input_mint  # the Token being sold

        if not self._gate_open():
            self._send_recommendation(pair_id, OrderKind.SELL)
            return ExecutionResult(ExecutionStatus.MONITORING_ONLY, submitted=False)

        # ---- duplicate-sell guard (Req 12.3; Property 32) ----
        marker = self._in_flight.get(pair_id)
        if marker is not None and marker.kind == OrderKind.SELL:
            return ExecutionResult(
                ExecutionStatus.SUPPRESSED_DUPLICATE_SELL,
                submitted=False,
                reason="a sell order is already in flight for this pair",
            )

        requested_qty = order.amount
        return self._dispatch(
            pair_id=pair_id,
            kind=OrderKind.SELL,
            token_address=token_address,
            order=order,
            notional=self._position_notional(pair_id),
            requested_qty=requested_qty,
        )

    # -- dispatch (submission + confirmation + terminal handling) ----------

    def _dispatch(
        self,
        *,
        pair_id: str,
        kind: OrderKind,
        token_address: str,
        order: OrderRequest,
        notional: Decimal,
        requested_qty: Decimal,
    ) -> ExecutionResult:
        """Submit, confirm, and finalize an order with no partial mutation.

        The injected signer is invoked here and *only* here - after every gate -
        so the signing path is reachable only when authorized + enabled
        (Property 23). On any non-confirmed outcome the Position store and
        balance are left unchanged (Property 25); the in-flight marker is set on
        submission and cleared exactly on a terminal status (Req 12.1, 12.4).
        """
        # Attach the user-configured max slippage tolerance (Req 6.4; Property 24)
        # and sign via the injected signer. Only the signed tx crosses the venue
        # boundary - never key material (design "Signer / Key Handling").
        signed_tx = self._signer.sign_transaction(self._serialize_unsigned(order))
        order = replace(order, max_slippage=self._max_slippage, signed_transaction=signed_tx)

        submitted_result: Result[SubmittedOrder] = self._venue.submit_order(order)
        if submitted_result.is_err():
            # Submission failure (Req 6.7): record reason, notify <=5s, NO state
            # change, and DO NOT set an in-flight marker for a failed submission.
            rec = self._record_order(
                pair_id=pair_id,
                kind=kind,
                requested_qty=requested_qty,
                notional=notional,
                status=OrderStatus.FAILED,
                max_slippage=self._max_slippage,
                reason=f"SUBMISSION_FAILED: {submitted_result.error}",
            )
            self._notify_failure(pair_id, "SUBMISSION_FAILED")
            return ExecutionResult(
                ExecutionStatus.SUBMISSION_FAILED,
                submitted=True,
                order=rec,
                reason="order submission failed",
            )

        submitted = submitted_result.value

        # Mark exactly one in-flight order per pair (Req 12.1).
        marker = OrderRecord(
            pair_id=pair_id,
            kind=kind,
            requested_qty=requested_qty,
            notional=notional,
            max_slippage=self._max_slippage,
            status=OrderStatus.SUBMITTED,
            recorded_at=self._clock(),
            tx_id=submitted.tx_id,
        )
        self._in_flight.mark(pair_id, marker)

        conf_result: Result[Confirmation] = self._venue.poll_confirmation(
            submitted.tx_id, self._timeout
        )
        if conf_result.is_err():
            # Confirmation timeout (Req 6.6): cancel, record timeout, NO state
            # change, clear the in-flight marker (Req 12.4).
            rec = self._record_order(
                pair_id=pair_id,
                kind=kind,
                requested_qty=requested_qty,
                notional=notional,
                status=OrderStatus.TIMED_OUT,
                max_slippage=self._max_slippage,
                tx_id=submitted.tx_id,
                reason=f"TIMED_OUT: {conf_result.error}",
            )
            self._in_flight.clear(pair_id)
            self._notify_failure(pair_id, "TIMED_OUT")
            return ExecutionResult(
                ExecutionStatus.TIMED_OUT,
                submitted=True,
                order=rec,
                reason="confirmation timed out",
            )

        conf = conf_result.value

        if not conf.confirmed:
            # Not confirmed on-chain: treat as a failure (Req 6.7) - no state
            # change, clear marker.
            rec = self._record_order(
                pair_id=pair_id,
                kind=kind,
                requested_qty=requested_qty,
                notional=notional,
                status=OrderStatus.FAILED,
                max_slippage=self._max_slippage,
                tx_id=submitted.tx_id,
                reason="not confirmed on-chain",
            )
            self._in_flight.clear(pair_id)
            self._notify_failure(pair_id, "SUBMISSION_FAILED")
            return ExecutionResult(
                ExecutionStatus.SUBMISSION_FAILED,
                submitted=True,
                order=rec,
                reason="order not confirmed",
            )

        if (
            conf.executed_slippage is not None
            and conf.executed_slippage > self._max_slippage
        ):
            # Executed slippage breach (Req 6.8): cancel, record reason, NO state
            # change, clear marker (Req 12.4).
            rec = self._record_order(
                pair_id=pair_id,
                kind=kind,
                requested_qty=requested_qty,
                notional=notional,
                status=OrderStatus.CANCELLED,
                max_slippage=self._max_slippage,
                tx_id=submitted.tx_id,
                reason=(
                    f"SLIPPAGE_EXCEEDED: executed {conf.executed_slippage} "
                    f"> max {self._max_slippage}"
                ),
            )
            self._in_flight.clear(pair_id)
            self._notify_failure(pair_id, "SLIPPAGE_EXCEEDED")
            return ExecutionResult(
                ExecutionStatus.SLIPPAGE_EXCEEDED,
                submitted=True,
                order=rec,
                reason="executed slippage exceeded maximum",
            )

        # Confirmed within slippage: record full execution (Req 6.5), clear the
        # in-flight marker (terminal, Req 12.4), update the Position, notify.
        rec = self._record_order(
            pair_id=pair_id,
            kind=kind,
            requested_qty=requested_qty,
            notional=notional,
            status=OrderStatus.CONFIRMED,
            max_slippage=self._max_slippage,
            tx_id=conf.tx_id,
            executed_price=conf.executed_price,
            executed_qty=conf.executed_qty,
            fee=conf.fee,
            recorded_at=conf.confirmed_at,
        )
        self._in_flight.clear(pair_id)
        self._update_position(kind, pair_id, token_address, conf, notional)
        self._notify_confirmation(rec)
        return ExecutionResult(
            ExecutionStatus.CONFIRMED, submitted=True, order=rec, prepared_size=notional
        )

    # -- position update (only on a confirmed fill) -----------------------

    def _update_position(
        self,
        kind: OrderKind,
        pair_id: str,
        token_address: str,
        conf: Confirmation,
        notional: Decimal,
    ) -> None:
        """Update the Position store on a confirmed fill (Req 6.5)."""
        if kind == OrderKind.BUY:
            self._positions.upsert(
                Position(
                    pair_id=pair_id,
                    token_address=token_address,
                    quantity=conf.executed_qty or Decimal(0),
                    avg_entry_price=conf.executed_price or Decimal(0),
                    notional_cost=notional,
                    opened_at=conf.confirmed_at,
                    status=PositionStatus.OPEN,
                )
            )
        else:  # SELL -> close the held position (full-position exit)
            existing = self._positions.get(pair_id)
            if existing.is_ok():
                self._positions.upsert(
                    replace(
                        existing.value,
                        quantity=Decimal(0),
                        notional_cost=Decimal(0),
                        status=PositionStatus.CLOSED,
                    )
                )

    # -- order recording ---------------------------------------------------

    def _record_order(
        self,
        *,
        pair_id: str,
        kind: OrderKind,
        requested_qty: Decimal,
        notional: Decimal,
        status: OrderStatus,
        max_slippage: Decimal | None = None,
        tx_id: str | None = None,
        executed_price: Decimal | None = None,
        executed_qty: Decimal | None = None,
        fee: Decimal | None = None,
        reason: str | None = None,
        recorded_at: datetime | None = None,
    ) -> OrderRecord:
        """Build and persist an :class:`OrderRecord` (append is idempotent)."""
        rec = OrderRecord(
            pair_id=pair_id,
            kind=kind,
            requested_qty=requested_qty,
            notional=notional,
            max_slippage=max_slippage if max_slippage is not None else self._max_slippage,
            status=status,
            recorded_at=recorded_at or self._clock(),
            executed_price=executed_price,
            executed_qty=executed_qty,
            fee=fee,
            tx_id=tx_id,
            reason=reason,
        )
        self._orders.append(rec)
        return rec

    # -- notifications (Notifier seam; Task 17 wires the real Notifier) ----

    def _send_recommendation(self, pair_id: str, kind: OrderKind) -> None:
        """Send a trade recommendation instead of an order (Req 6.3)."""
        if self._alert_sink is None:
            return
        self._alert_sink(
            Alert(
                title="Trade recommendation (monitoring-only)",
                body=(
                    f"{kind.value} opportunity for {pair_id}; automated trading "
                    "is disabled or no wallet is authorized - no order submitted."
                ),
                pair_id=pair_id,
            )
        )

    def _notify_failure(self, pair_id: str, reason: str) -> None:
        """Notify the user of an execution failure within the bound (Req 6.7, 6.10)."""
        if self._alert_sink is None:
            return
        self._alert_sink(
            Alert(
                title=f"Order not executed: {reason}",
                body=f"Order for {pair_id} was not executed ({reason}).",
                pair_id=pair_id,
            )
        )

    def _notify_confirmation(self, rec: OrderRecord) -> None:
        """Send an order-confirmation message (Req 8.1)."""
        if self._alert_sink is None:
            return
        self._alert_sink(
            Alert(
                title=f"Order confirmed: {rec.kind.value}",
                body=(
                    f"{rec.kind.value} {rec.pair_id} executed @ {rec.executed_price} "
                    f"qty {rec.executed_qty} (tx {rec.tx_id})."
                ),
                pair_id=rec.pair_id,
            )
        )

    # -- exposure / position helpers --------------------------------------

    def _position_open(self, pair_id: str) -> bool:
        result = self._positions.get(pair_id)
        return result.is_ok() and result.value.status == PositionStatus.OPEN

    def _position_notional(self, pair_id: str) -> Decimal:
        result = self._positions.get(pair_id)
        return result.value.notional_cost if result.is_ok() else Decimal(0)

    def _token_notional(self, token_address: str) -> Decimal:
        total = Decimal(0)
        for position in self._positions.list_open():
            if position.token_address == token_address:
                total += position.notional_cost
        return total

    def _total_notional(self) -> Decimal:
        total = Decimal(0)
        for position in self._positions.list_open():
            total += position.notional_cost
        return total

    @staticmethod
    def _serialize_unsigned(order: OrderRequest) -> str:
        """Produce the unsigned serialized-tx stand-in handed to the signer.

        In live wiring this is the serialized transaction returned by the Jupiter
        Swap API; here it is a deterministic descriptor. It carries no key
        material and is never persisted.
        """
        return (
            f"unsigned:{order.pair_id}:{order.kind.value}:{order.input_mint}"
            f"->{order.output_mint}:{order.amount}"
        )


__all__ = [
    "Signer",
    "TradingGate",
    "AutomatedTradingFlag",
    "SeverityLookup",
    "BalanceLookup",
    "AlertSink",
    "ExecutionStatus",
    "ExecutionResult",
    "TradeExecutor",
    "resolve_order_size",
    "cap_to_risk_limits",
]
