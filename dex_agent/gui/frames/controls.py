"""Controls frame with Start, Stop, and Settings buttons."""

from __future__ import annotations

from typing import Callable

import customtkinter


class ControlsFrame(customtkinter.CTkFrame):
    """Start/Stop/Settings control buttons.

    Manages button states based on agent running/stopped/transitioning status:
    - Transitioning: both Start and Stop disabled
    - Running (not transitioning): Start disabled, Stop enabled
    - Stopped (not transitioning): Start enabled, Stop disabled
    - Settings button is always enabled
    """

    def __init__(
        self,
        master: any,
        on_start: Callable,
        on_stop: Callable,
        on_settings: Callable,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)

        self._on_start = on_start
        self._on_stop = on_stop
        self._on_settings = on_settings

        # Start button
        self._start_button = customtkinter.CTkButton(
            self,
            text="Start",
            width=100,
            command=self._handle_start,
        )
        self._start_button.pack(side="left", padx=(10, 5), pady=10)

        # Stop button (initially disabled since agent starts in stopped state)
        self._stop_button = customtkinter.CTkButton(
            self,
            text="Stop",
            width=100,
            command=self._handle_stop,
        )
        self._stop_button.pack(side="left", padx=5, pady=10)
        self._stop_button.configure(state="disabled")

        # Settings button (always enabled)
        self._settings_button = customtkinter.CTkButton(
            self,
            text="Settings",
            width=100,
            command=self._handle_settings,
        )
        self._settings_button.pack(side="left", padx=5, pady=10)

    def _handle_start(self) -> None:
        """Handle Start button click."""
        self._on_start()

    def _handle_stop(self) -> None:
        """Handle Stop button click."""
        self._on_stop()

    def _handle_settings(self) -> None:
        """Handle Settings button click."""
        self._on_settings()

    def update_button_states(self, is_running: bool, is_transitioning: bool) -> None:
        """Update button enabled/disabled states based on agent status.

        Args:
            is_running: Whether the agent is currently running.
            is_transitioning: Whether the agent is in a transitional state
                (booting or stopping).
        """
        if is_transitioning:
            # Both Start and Stop disabled during transitions
            self._start_button.configure(state="disabled")
            self._stop_button.configure(state="disabled")
        elif is_running:
            # Running: Start disabled, Stop enabled
            self._start_button.configure(state="disabled")
            self._stop_button.configure(state="normal")
        else:
            # Stopped: Start enabled, Stop disabled
            self._start_button.configure(state="normal")
            self._stop_button.configure(state="disabled")

        # Settings button is always enabled regardless of state
        self._settings_button.configure(state="normal")
