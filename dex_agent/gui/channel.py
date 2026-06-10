"""GUIChannel: routes alerts to the Alerts_Log widget via thread-safe scheduling.

Implements the :class:`~dex_agent.providers.interfaces.NotificationChannel`
abstract interface so the existing Notifier can dispatch alerts to the GUI
without any modification to the notification infrastructure.

The channel uses ``widget.after(0, callback)`` to schedule widget updates from
the Agent_Thread (background) to the Tkinter main thread. If the widget has
been destroyed (e.g. the user closed the window while an alert was in-flight),
the resulting ``TclError`` is caught gracefully and a non-delivered result is
returned — no exception ever escapes ``deliver()``.

The widget reference may be ``None`` at construction time because the GUI
layout may not be ready when the channel is first wired into the agent's
provider list. Call :meth:`set_widget` once the ``AlertsLogFrame`` is created.
"""

from __future__ import annotations

import tkinter
from typing import TYPE_CHECKING

from dex_agent.providers.interfaces import (
    Alert,
    DeliveryResult,
    NotificationChannel,
)
from dex_agent.result import Ok, Result

if TYPE_CHECKING:
    from dex_agent.gui.frames.alerts_log import AlertsLogFrame


class GUIChannel(NotificationChannel):
    """Routes alerts to the Alerts_Log widget via thread-safe scheduling.

    Attributes
    ----------
    name : str
        Channel identifier used in ``DeliveryResult.channel``.
    alerts_count : int
        Running total of successfully delivered alerts (used by AgentState).
    """

    name: str = "GUI"

    def __init__(self, alerts_log_widget: "AlertsLogFrame | None" = None) -> None:
        self._widget: "AlertsLogFrame | None" = alerts_log_widget
        self.alerts_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_widget(self, widget: "AlertsLogFrame") -> None:
        """Bind (or rebind) the Alerts_Log widget for deferred wiring.

        Called by the application once the frame is constructed and ready
        to receive alert entries.
        """
        self._widget = widget

    def deliver(self, alert: Alert) -> Result[DeliveryResult]:
        """Deliver *alert* to the Alerts_Log via thread-safe scheduling.

        Returns
        -------
        Ok(DeliveryResult)
            Always returns Ok — never raises.

            * ``delivered=True`` when the widget is available and the
              alert was scheduled for display.
            * ``delivered=False`` with a descriptive ``detail`` string
              when the widget is unavailable or destroyed.
        """
        if self._widget is None:
            return Ok(
                DeliveryResult(
                    channel=self.name,
                    delivered=False,
                    detail="widget unavailable",
                )
            )

        try:
            # Schedule the append on the Tkinter main thread.
            # widget.after(0, ...) enqueues the callback into Tk's event loop
            # and is safe to call from any thread.
            self._widget.after(
                0, self._widget.append_alert, alert.title, alert.body
            )
        except tkinter.TclError:
            # Widget has been destroyed between the None-check and the
            # after() call (race during shutdown). Swallow gracefully.
            return Ok(
                DeliveryResult(
                    channel=self.name,
                    delivered=False,
                    detail="widget unavailable",
                )
            )

        self.alerts_count += 1
        return Ok(
            DeliveryResult(
                channel=self.name,
                delivered=True,
                detail="",
            )
        )
