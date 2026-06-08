"""Notification layer: the Notifier and notification-channel policy.

Re-exports the :class:`~dex_agent.notify.notifier.Notifier` and its result
types so callers can ``from dex_agent.notify import Notifier``. Notification
channels themselves live behind the
:class:`~dex_agent.providers.interfaces.NotificationChannel` interface (Task 4);
the Notifier (Task 17) owns the multi-channel dispatch, retry, quiet-hours, and
final-status policy (Req 5.8, 8.1-8.6).
"""

from dex_agent.notify.notifier import (
    MAX_EXIT_ALERT_RETRIES,
    MIN_EXIT_ALERT_RETRIES,
    MIN_RETRY_INTERVAL_S,
    REGULAR_RETRIES,
    ChannelDelivery,
    DispatchResult,
    Notifier,
    PositionHeld,
    build_confirmation_alert,
    build_severity_alert,
)

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
