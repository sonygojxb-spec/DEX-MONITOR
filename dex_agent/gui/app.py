"""DEXMonitorApp: root application window for the DEX Monitor GUI.

Design reference: "DEXMonitorApp (app.py)" — the root CTk window that owns all
frames, the AgentThread, and orchestrates the GUI lifecycle.

Requirements validated: 2.1, 2.2, 2.3, 2.4, 2.5, 5.2, 5.3, 5.4, 5.5, 5.6,
8.1, 8.3, 8.4, 8.6, 11.3.
"""

from __future__ import annotations

import queue
from typing import TYPE_CHECKING

import customtkinter

from dex_agent.gui.channel import GUIChannel
from dex_agent.gui.dialogs.settings import SettingsDialog
from dex_agent.gui.frames.alerts_log import AlertsLogFrame
from dex_agent.gui.frames.controls import ControlsFrame
from dex_agent.gui.frames.status_bar import StatusBarFrame
from dex_agent.gui.frames.token_input import TokenInputFrame
from dex_agent.gui.frames.watchlist import WatchlistTableFrame
from dex_agent.gui.thread import AgentThread, AgentState
from dex_agent.models import Network

if TYPE_CHECKING:
    from dex_agent.agent import Agent


class DEXMonitorApp(customtkinter.CTk):
    """Root application window. Owns all frames and the AgentThread."""

    def __init__(self, agent: "Agent") -> None:
        # Dark mode must be set before creating the CTk instance
        customtkinter.set_appearance_mode("dark")

        super().__init__()

        self._agent = agent
        self._agent_thread: AgentThread | None = None
        self._state_queue: queue.Queue[AgentState] = queue.Queue()

        # Window configuration (Req 2.3, 2.5)
        self.title("DEX Monitor")
        self.minsize(1100, 700)

        # GUIChannel: instantiated early, widget wired after AlertsLogFrame is created
        self._gui_channel = GUIChannel()

        # --- Frame layout (top to bottom) ---

        # Status bar at the top
        self.status_bar = StatusBarFrame(self)
        self.status_bar.pack(fill="x", padx=10, pady=(10, 5))

        # Watchlist table (expands to fill available space)
        self.watchlist_table = WatchlistTableFrame(self)
        self.watchlist_table.pack(fill="both", expand=True, padx=10, pady=5)

        # Middle row: TokenInput + Controls side by side
        middle_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        middle_frame.pack(fill="x", padx=10, pady=5)

        self.token_input = TokenInputFrame(
            middle_frame,
            on_add=self._on_add,
            on_remove=self._on_remove,
        )
        self.token_input.pack(side="left", fill="x", expand=True)

        self.controls = ControlsFrame(
            middle_frame,
            on_start=self.start_agent,
            on_stop=self.stop_agent,
            on_settings=self._open_settings,
        )
        self.controls.pack(side="right", padx=(10, 0))

        # Alerts log at the bottom
        self.alerts_log = AlertsLogFrame(self)
        self.alerts_log.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Wire the GUIChannel to the alerts log widget now that it's created
        self._gui_channel.set_widget(self.alerts_log)

        # Initially disable token input (agent not running yet — Req 5.6)
        self.token_input.set_enabled(False)

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def start_agent(self) -> None:
        """Start the agent background thread (Req 8.1).

        Creates the AgentThread, begins polling, and updates button states.
        """
        if self._agent_thread is not None and self._agent_thread.is_running():
            return

        # Fresh state queue for this session
        self._state_queue = queue.Queue()

        # Create and start the agent thread
        self._agent_thread = AgentThread(
            self._agent, self._state_queue, self._gui_channel
        )
        self._agent_thread.start()

        # Transitioning state: both buttons disabled (Req 8.7)
        self.controls.update_button_states(is_running=False, is_transitioning=True)

        # Start polling the state queue
        self._poll_state_queue()

        # Enable token input buttons (Req 5.6 inverse — enabled when running)
        self.token_input.set_enabled(True)

    def stop_agent(self) -> None:
        """Signal the agent thread to stop (Req 8.2).

        Requests a graceful stop and updates button/input states.
        """
        if self._agent_thread is None:
            return

        # Update button states to transitioning
        self.controls.update_button_states(is_running=True, is_transitioning=True)

        # Disable token input while stopping (Req 5.6)
        self.token_input.set_enabled(False)

        # Signal the thread to stop (blocks up to 60s internally)
        self._agent_thread.request_stop()

        # Final state update: stopped
        self.controls.update_button_states(is_running=False, is_transitioning=False)

    def on_closing(self) -> None:
        """Handle window close: stop agent if running, then destroy (Req 8.6)."""
        if self._agent_thread is not None and self._agent_thread.is_running():
            self._agent_thread.request_stop()
        self.destroy()

    # ------------------------------------------------------------------
    # State polling
    # ------------------------------------------------------------------

    def _poll_state_queue(self) -> None:
        """Poll the state queue every 200ms via after(), updating the UI.

        Drains all pending states and applies the latest one.
        """
        latest_state: AgentState | None = None

        # Drain all pending states from the queue
        while True:
            try:
                latest_state = self._state_queue.get_nowait()
            except queue.Empty:
                break

        # Update UI with the latest state if any was received
        if latest_state is not None:
            self._update_ui_state(latest_state)

            # Update button states based on running/transitioning
            is_running = latest_state.is_running
            is_transitioning = (
                self._agent_thread.is_transitioning()
                if self._agent_thread is not None
                else False
            )
            self.controls.update_button_states(
                is_running=is_running, is_transitioning=is_transitioning
            )

            # If the agent has stopped (e.g. crash), disable token input
            if not is_running and not is_transitioning:
                self.token_input.set_enabled(False)

        # Schedule next poll (continuous while agent thread exists)
        if self._agent_thread is not None and (
            self._agent_thread.is_running() or self._agent_thread.is_transitioning()
        ):
            self.after(200, self._poll_state_queue)

    def _update_ui_state(self, state: AgentState) -> None:
        """Route state snapshot to StatusBar and WatchlistTable.

        Also surfaces errors in the Alerts Log.
        """
        self.status_bar.update_state(state)
        self.watchlist_table.update_rows(state.watchlist_rows)

        if state.error:
            self.alerts_log.append_message(f"Error: {state.error}")

    # ------------------------------------------------------------------
    # Token input callbacks
    # ------------------------------------------------------------------

    def _on_add(self, mint_address: str) -> None:
        """Handle Add button: submit add_token to the agent thread.

        On Ok → clear input (Req 5.5).
        On Err → append error to Alerts_Log, keep input (Req 5.3).
        """
        if self._agent_thread is None or not self._agent_thread.is_running():
            return

        # Call add_token directly — it's thread-safe via the agent's repositories
        # but per design we submit it on the agent thread to avoid data races.
        result = self._agent.add_token(mint_address, Network.SOLANA)

        if result.is_ok():
            self.token_input.clear_input()
        else:
            error_msg = str(result.error)
            self.alerts_log.append_message(f"Add token error: {error_msg}")

    def _on_remove(self) -> None:
        """Handle Remove button: remove the selected pair from the watchlist.

        No-op if no row is selected (Req 5.8).
        """
        if self._agent_thread is None or not self._agent_thread.is_running():
            return

        pair_id = self.watchlist_table.get_selected_pair_id()
        if pair_id is None:
            return

        self._agent.remove_pair(pair_id)

    # ------------------------------------------------------------------
    # Settings dialog
    # ------------------------------------------------------------------

    def _open_settings(self) -> None:
        """Open the Settings modal dialog."""
        SettingsDialog(self, self._agent.config_manager)
