"""Status bar frame displaying real-time operational metrics.

Shows active pairs count, uptime (HH:MM:SS), last tick time, and alerts
count in a horizontal bar. The uptime counter ticks every second while the
agent is running.
"""

from __future__ import annotations

import customtkinter

from dex_agent.gui.thread import AgentState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def format_duration(seconds: float) -> str:
    """Convert a duration in seconds to HH:MM:SS format.

    Hours may exceed 23 (i.e. no day wrapping). Minutes and seconds are
    always in the 00–59 range.

    Args:
        seconds: Non-negative duration in seconds (fractional part is
            truncated).

    Returns:
        String formatted as ``HH:MM:SS``.
    """
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# ---------------------------------------------------------------------------
# StatusBarFrame
# ---------------------------------------------------------------------------


class StatusBarFrame(customtkinter.CTkFrame):
    """Horizontal bar showing active pairs, uptime, last tick, alert count.

    The frame displays four labeled metrics in a row. It receives state
    updates from the main application via :meth:`update_state` and maintains
    a 1-second uptime ticker via :meth:`_tick_uptime` while the agent is
    running.
    """

    def __init__(self, master: customtkinter.CTkBaseClass, **kwargs) -> None:
        super().__init__(master, **kwargs)

        # Internal state tracking
        self._is_running: bool = False
        self._uptime_seconds: float = 0.0
        self._last_tick_time: str | None = None
        self._after_id: str | None = None

        # --- Layout: 4 metric groups in a horizontal row ---
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Active pairs
        self._pairs_title = customtkinter.CTkLabel(
            self, text="Active Pairs", font=("", 11)
        )
        self._pairs_title.grid(row=0, column=0, padx=10, pady=(5, 0))
        self._pairs_value = customtkinter.CTkLabel(
            self, text="0", font=("", 14, "bold")
        )
        self._pairs_value.grid(row=1, column=0, padx=10, pady=(0, 5))

        # Uptime
        self._uptime_title = customtkinter.CTkLabel(
            self, text="Uptime", font=("", 11)
        )
        self._uptime_title.grid(row=0, column=1, padx=10, pady=(5, 0))
        self._uptime_value = customtkinter.CTkLabel(
            self, text="00:00:00", font=("", 14, "bold")
        )
        self._uptime_value.grid(row=1, column=1, padx=10, pady=(0, 5))

        # Last tick
        self._tick_title = customtkinter.CTkLabel(
            self, text="Last Tick", font=("", 11)
        )
        self._tick_title.grid(row=0, column=2, padx=10, pady=(5, 0))
        self._tick_value = customtkinter.CTkLabel(
            self, text="--:--:--", font=("", 14, "bold")
        )
        self._tick_value.grid(row=1, column=2, padx=10, pady=(0, 5))

        # Alerts count
        self._alerts_title = customtkinter.CTkLabel(
            self, text="Alerts", font=("", 11)
        )
        self._alerts_title.grid(row=0, column=3, padx=10, pady=(5, 0))
        self._alerts_value = customtkinter.CTkLabel(
            self, text="0", font=("", 14, "bold")
        )
        self._alerts_value.grid(row=1, column=3, padx=10, pady=(0, 5))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_state(self, state: AgentState) -> None:
        """Refresh all status labels from an agent state snapshot.

        When the agent is running, this starts the uptime ticker if not
        already running. When the agent stops, the ticker is cancelled and
        the uptime/last-tick values freeze at their last values. The alert
        count is always retained.

        Args:
            state: The latest :class:`AgentState` snapshot from the queue.
        """
        # Always update pairs and alerts
        self._pairs_value.configure(text=str(state.active_pairs))
        self._alerts_value.configure(text=str(state.alerts_count))

        if state.is_running:
            # Update internal tracking for the ticker
            self._uptime_seconds = state.uptime_seconds
            self._uptime_value.configure(
                text=format_duration(self._uptime_seconds)
            )

            # Update last tick time if available
            if state.last_tick_time is not None:
                self._last_tick_time = state.last_tick_time
                self._tick_value.configure(text=self._last_tick_time)

            # Start the uptime ticker if not already running
            if not self._is_running:
                self._is_running = True
                self._start_uptime_ticker()
        else:
            # Agent stopped — freeze uptime and last tick at current values
            if self._is_running:
                # Transition from running → stopped
                self._is_running = False
                self._cancel_uptime_ticker()
                # Freeze uptime at current value (already displayed)
                # Freeze last tick at current value (already displayed)

            # When agent has never started, show zeros as per requirement 3.7
            if state.uptime_seconds == 0.0 and self._last_tick_time is None:
                self._pairs_value.configure(text="0")
                self._uptime_value.configure(text="00:00:00")
                self._tick_value.configure(text="--:--:--")

    # ------------------------------------------------------------------
    # Internal: uptime ticker
    # ------------------------------------------------------------------

    def _start_uptime_ticker(self) -> None:
        """Start the 1-second uptime counter via after() scheduling."""
        self._cancel_uptime_ticker()
        self._tick_uptime()

    def _tick_uptime(self) -> None:
        """Increment and display the uptime counter every 1 second.

        Schedules itself via ``self.after(1000, ...)`` to produce a live
        ticking display. Only runs while ``_is_running`` is True.
        """
        if not self._is_running:
            self._after_id = None
            return

        self._uptime_seconds += 1.0
        self._uptime_value.configure(text=format_duration(self._uptime_seconds))
        self._after_id = self.after(1000, self._tick_uptime)

    def _cancel_uptime_ticker(self) -> None:
        """Cancel any pending uptime after() callback."""
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
