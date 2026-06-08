"""The Notifier: multi-channel alert dispatch with retry and quiet hours.

Design references: "Notifier" and "Alerting". The Notifier delivers each
:class:`~dex_agent.providers.interfaces.Alert` to **every enabled channel**
(Req 8.3), retrying per channel up to a bounded number of attempts at least 5
seconds apart (Req 8.4) and recording the final per-channel status as delivered
or undelivered, surfacing an undelivered indication without blocking delivery on
the other enabled channels (Req 8.5). During a configured quiet-hours window it
suppresses only alerts that are **neither** Critical **nor** an Exit_Signal alert
for a Trading_Pair in which a Position is held; Critical and held-position
Exit_Signal alerts are always delivered (Req 8.6).

Retry budget:

* Regular alerts use 1 initial attempt + up to 3 retries = **4 attempts**
  (Req 8.4).
* Exit_Signal alerts use 1 initial attempt + the user-configured exit-signal
  retry budget ``N`` (``1..10``, default ``3``) = ``1 + N`` attempts (Req 5.8).

Seams for testing (no real sleeps in tests):

* ``clock``  - returns "now" for quiet-hours evaluation and record timestamps.
* ``sleep``  - the >=5s inter-attempt wait; injected so property tests run
  without real elapsed time. Defaults to :func:`time.sleep` for production.
* ``position_held`` - predicate over ``pair_id`` reporting whether a Position is
  currently held in that Trading_Pair (drives the held-position exit policy).

All channels are accessed only through the
:class:`~dex_agent.providers.interfaces.NotificationChannel` interface, so the
in-memory fakes exercise the policy at scale.
"""

from __future__ import annotations

import time as _time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Callable, Sequence

from dex_agent.errors import AgentError
from dex_agent.models import (
    OrderKind,
    Severity,
    TimeWindow,
    utc_now_seconds,
)
from dex_agent.providers.interfaces import Alert, NotificationChannel

# A predicate reporting whether a Position is currently held in ``pair_id``
# (Req 8.6 held-position Exit_Signal policy). Injected so the Notifier stays
# decoupled from the Position store; tests inject a simple set membership.
PositionHeld = Callable[[str | None], bool]

# Number of *retries* allowed for a regular (non exit-signal) alert beyond the
# first attempt (Req 8.4: "up to 3 additional times").
REGULAR_RETRIES: int = 3

# Minimum interval between delivery attempts on a channel (Req 8.4).
MIN_RETRY_INTERVAL_S: float = 5.0

# Exit-signal retry-budget bounds (Req 5.8).
MIN_EXIT_ALERT_RETRIES: int = 1
MAX_EXIT_ALERT_RETRIES: int = 10


# ---------------------------------------------------------------------------
# Result records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChannelDelivery:
    """The final, recorded delivery status for one channel (Req 8.4/8.5).

    Attributes:
        channel: A stable label identifying the channel.
        delivered: ``True`` iff some attempt succeeded; ``False`` (undelivered)
            iff every attempt failed.
        attempts: The number of delivery attempts made (1..max). Bounded by the
            alert's retry budget (Property 26).
        last_error: The typed error from the final failed attempt, or ``None``
            when delivered (or when the channel reported a non-delivery without
            a typed error).
    """

    channel: str
    delivered: bool
    attempts: int
    last_error: AgentError | None = None


@dataclass(frozen=True)
class DispatchResult:
    """The outcome of dispatching one alert across all enabled channels.

    Attributes:
        alert: The alert that was dispatched.
        suppressed: ``True`` when the alert was suppressed entirely by quiet
            hours (Req 8.6); no channel deliveries were attempted.
        channels: The per-channel final statuses (empty when suppressed).
        dispatched_at: The clock instant at which dispatch began.
    """

    alert: Alert
    suppressed: bool
    channels: tuple[ChannelDelivery, ...] = field(default_factory=tuple)
    dispatched_at: datetime | None = None

    @property
    def all_delivered(self) -> bool:
        """True iff the alert reached every enabled channel."""
        return bool(self.channels) and all(c.delivered for c in self.channels)

    @property
    def any_undelivered(self) -> bool:
        """True iff at least one channel recorded an undelivered status."""
        return any(not c.delivered for c in self.channels)

    @property
    def undelivered_channels(self) -> tuple[str, ...]:
        """The labels of channels whose final status is undelivered (Req 8.5)."""
        return tuple(c.channel for c in self.channels if not c.delivered)


# ---------------------------------------------------------------------------
# Alert builders (content)
# ---------------------------------------------------------------------------


def build_confirmation_alert(
    *,
    pair_id: str,
    order_kind: OrderKind,
    executed_price: Decimal,
    quantity: Decimal,
) -> Alert:
    """Build an order-confirmation alert (Req 8.1).

    The confirmation message contains the Trading_Pair, order type, executed
    price, and quantity. It is a normal-severity, non exit-signal alert.
    """
    kind = order_kind.value if isinstance(order_kind, OrderKind) else str(order_kind)
    title = f"Order {kind} confirmed: {pair_id}"
    body = (
        f"pair={pair_id} type={kind} "
        f"price={executed_price} qty={quantity}"
    )
    return Alert(
        title=title,
        body=body,
        severity=Severity.NONE,
        pair_id=pair_id,
        is_exit_signal=False,
    )


def build_severity_alert(*, pair_id: str, severity: Severity, detail: str = "") -> Alert:
    """Build a High/Critical severity alert for a monitored Token (Req 8.2)."""
    title = f"{severity.name} severity: {pair_id}"
    body = detail or f"pair={pair_id} severity={severity.name}"
    return Alert(title=title, body=body, severity=severity, pair_id=pair_id)


# ---------------------------------------------------------------------------
# Notifier
# ---------------------------------------------------------------------------


class Notifier:
    """Dispatches alerts to every enabled channel with retry + quiet hours."""

    def __init__(
        self,
        *,
        channels: Sequence[NotificationChannel],
        position_held: PositionHeld | None = None,
        quiet_hours: TimeWindow | None = None,
        exit_alert_retries: int = 3,
        retry_interval_s: float = MIN_RETRY_INTERVAL_S,
        clock: Callable[[], datetime] = utc_now_seconds,
        sleep: Callable[[float], None] = _time.sleep,
    ) -> None:
        if not (
            MIN_EXIT_ALERT_RETRIES <= exit_alert_retries <= MAX_EXIT_ALERT_RETRIES
        ):
            raise ValueError(
                "exit_alert_retries must be in [1, 10] (Req 5.8); "
                f"got {exit_alert_retries}"
            )
        if retry_interval_s < MIN_RETRY_INTERVAL_S:
            raise ValueError(
                "retry_interval_s must be at least 5 seconds (Req 8.4); "
                f"got {retry_interval_s}"
            )
        self._channels = tuple(channels)
        self._position_held: PositionHeld = position_held or (lambda _pair: False)
        self._quiet_hours = quiet_hours
        self._exit_alert_retries = exit_alert_retries
        self._retry_interval_s = retry_interval_s
        self._clock = clock
        self._sleep = sleep

    # -- introspection ------------------------------------------------------

    @property
    def channels(self) -> tuple[NotificationChannel, ...]:
        """The enabled notification channels (Req 8.3)."""
        return self._channels

    def max_attempts(self, alert: Alert) -> int:
        """The bounded number of attempts allowed for ``alert`` (Property 26).

        Exit_Signal alerts use ``1 + exit_alert_retries`` (Req 5.8); all other
        alerts use ``1 + 3`` regular retries (Req 8.4).
        """
        if alert.is_exit_signal:
            return 1 + self._exit_alert_retries
        return 1 + REGULAR_RETRIES

    # -- quiet-hours policy -------------------------------------------------

    def _always_deliver(self, alert: Alert) -> bool:
        """Critical alerts and held-position Exit_Signal alerts (Req 8.6)."""
        if alert.severity == Severity.CRITICAL:
            return True
        return alert.is_exit_signal and self._position_held(alert.pair_id)

    def in_quiet_hours(self, now: datetime | None = None) -> bool:
        """Whether ``now`` (wall-clock) falls within the configured quiet hours.

        Handles windows that wrap past midnight (``start > end``). Returns
        ``False`` when no quiet-hours window is configured.
        """
        window = self._quiet_hours
        if window is None:
            return False
        moment = (now or self._clock()).time()
        start, end = window.start, window.end
        if start == end:
            # Degenerate window: treat as the entire day being quiet.
            return True
        if start < end:
            return start <= moment < end
        # Wraps past midnight, e.g. 22:00..06:00.
        return moment >= start or moment < end

    # -- dispatch -----------------------------------------------------------

    def send(self, alert: Alert) -> DispatchResult:
        """Dispatch ``alert`` to every enabled channel (Req 8.3-8.6, 5.8).

        Applies quiet-hours suppression, then attempts delivery on each enabled
        channel up to the alert's bounded retry budget, recording the final
        per-channel status. A per-channel failure never blocks the remaining
        channels (Req 8.5).
        """
        dispatched_at = self._clock()

        if self.in_quiet_hours(dispatched_at) and not self._always_deliver(alert):
            return DispatchResult(
                alert=alert,
                suppressed=True,
                channels=(),
                dispatched_at=dispatched_at,
            )

        max_attempts = self.max_attempts(alert)
        records: list[ChannelDelivery] = []
        for index, channel in enumerate(self._channels):
            records.append(self._deliver_to_channel(channel, alert, index, max_attempts))

        return DispatchResult(
            alert=alert,
            suppressed=False,
            channels=tuple(records),
            dispatched_at=dispatched_at,
        )

    def _deliver_to_channel(
        self,
        channel: NotificationChannel,
        alert: Alert,
        index: int,
        max_attempts: int,
    ) -> ChannelDelivery:
        """Attempt delivery on one channel up to ``max_attempts`` times."""
        label = self._channel_label(channel, index)
        attempts = 0
        delivered = False
        last_error: AgentError | None = None

        while attempts < max_attempts:
            attempts += 1
            result = channel.deliver(alert)
            if result.is_ok() and result.value.delivered:
                delivered = True
                last_error = None
                break
            last_error = result.error if result.is_err() else None
            if attempts < max_attempts:
                # Wait >= 5s between attempts (Req 8.4); injected seam in tests.
                self._sleep(self._retry_interval_s)

        return ChannelDelivery(
            channel=label,
            delivered=delivered,
            attempts=attempts,
            last_error=last_error,
        )

    @staticmethod
    def _channel_label(channel: NotificationChannel, index: int) -> str:
        """Derive a stable label for a channel for status recording."""
        name = getattr(channel, "name", None)
        if name:
            return str(name)
        return f"{channel.__class__.__name__}#{index}"


__all__ = [
    "Notifier",
    "DispatchResult",
    "ChannelDelivery",
    "PositionHeld",
    "build_confirmation_alert",
    "build_severity_alert",
    "REGULAR_RETRIES",
    "MIN_RETRY_INTERVAL_S",
    "MIN_EXIT_ALERT_RETRIES",
    "MAX_EXIT_ALERT_RETRIES",
]
