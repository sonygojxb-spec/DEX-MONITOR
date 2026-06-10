"""Unit tests for DEXMonitorApp (dex_agent/gui/app.py).

Tests validate application wiring and button state transitions:
- Start/Stop button enable/disable logic
- on_closing triggers agent stop
- Initial state (zeros, empty table)
- add_token error routing to Alerts_Log

Requirements validated: 8.3, 8.4, 8.7, 5.3
"""

from __future__ import annotations

import queue
import sys
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Mock customtkinter before importing the module under test.
# We replicate the pattern used in other GUI tests in this project.
# ---------------------------------------------------------------------------

_mock_ctk_module = MagicMock()

# CTk and CTkFrame need to be subclassable classes (not MagicMock instances)
_mock_ctk_module.CTk = type(
    "CTk",
    (),
    {
        "__init__": lambda self, *a, **kw: None,
        "title": lambda self, *a, **kw: None,
        "minsize": lambda self, *a, **kw: None,
        "protocol": lambda self, *a, **kw: None,
        "after": lambda self, *a, **kw: None,
        "destroy": lambda self, *a, **kw: None,
    },
)
_mock_ctk_module.CTkFrame = type(
    "CTkFrame",
    (),
    {
        "__init__": lambda self, *a, **kw: None,
        "pack": lambda self, *a, **kw: None,
    },
)
_mock_ctk_module.set_appearance_mode = MagicMock()


def _build_app():
    """Construct a DEXMonitorApp with all dependencies mocked.

    Returns a tuple of:
        (app, mock_agent, mock_agent_thread_class, mock_controls,
         mock_token_input, mock_alerts_log, mock_status_bar, mock_watchlist)
    """
    # Mock frames and dialogs
    mock_status_bar = MagicMock()
    mock_watchlist = MagicMock()
    mock_token_input = MagicMock()
    mock_controls = MagicMock()
    mock_alerts_log = MagicMock()
    mock_gui_channel = MagicMock()
    mock_agent_thread_class = MagicMock()

    # Mock the Agent
    mock_agent = MagicMock()
    mock_agent.add_token = MagicMock()
    mock_agent.remove_pair = MagicMock()

    patches = {
        "customtkinter": _mock_ctk_module,
    }

    with patch.dict(sys.modules, patches):
        # Remove cached module to force reimport with mocks
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("dex_agent.gui"):
                del sys.modules[mod_name]

        with (
            patch(
                "dex_agent.gui.frames.status_bar.StatusBarFrame",
                return_value=mock_status_bar,
            ),
            patch(
                "dex_agent.gui.frames.watchlist.WatchlistTableFrame",
                return_value=mock_watchlist,
            ),
            patch(
                "dex_agent.gui.frames.token_input.TokenInputFrame",
                return_value=mock_token_input,
            ),
            patch(
                "dex_agent.gui.frames.controls.ControlsFrame",
                return_value=mock_controls,
            ),
            patch(
                "dex_agent.gui.frames.alerts_log.AlertsLogFrame",
                return_value=mock_alerts_log,
            ),
            patch(
                "dex_agent.gui.channel.GUIChannel",
                return_value=mock_gui_channel,
            ),
            patch(
                "dex_agent.gui.thread.AgentThread",
                mock_agent_thread_class,
            ),
        ):
            from dex_agent.gui.app import DEXMonitorApp

            app = DEXMonitorApp(mock_agent)

    return (
        app,
        mock_agent,
        mock_agent_thread_class,
        mock_controls,
        mock_token_input,
        mock_alerts_log,
        mock_status_bar,
        mock_watchlist,
    )


# ===========================================================================
# Test: Start/Stop button enable/disable logic (Req 8.3, 8.4, 8.7)
# ===========================================================================


class TestStartStopButtonStates:
    """Tests for Start/Stop button state transitions via controls frame."""

    def test_start_agent_sets_transitioning_state(self):
        """After start_agent(), controls show transitioning (both buttons disabled)."""
        app, _, mock_at_class, mock_controls, mock_token_input, _, _, _ = _build_app()

        # Configure mock AgentThread instance
        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = False
        mock_at_instance.is_transitioning.return_value = True
        mock_at_class.return_value = mock_at_instance

        # Reset to track calls during start_agent
        mock_controls.update_button_states.reset_mock()

        app.start_agent()

        # Should have called update_button_states with transitioning=True
        mock_controls.update_button_states.assert_called_with(
            is_running=False, is_transitioning=True
        )

    def test_stop_agent_sets_transitioning_then_stopped(self):
        """After stop_agent(), controls transition then settle to stopped state."""
        app, _, mock_at_class, mock_controls, mock_token_input, _, _, _ = _build_app()

        # First start the agent so we have an _agent_thread
        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = True
        mock_at_instance.is_transitioning.return_value = False
        mock_at_class.return_value = mock_at_instance
        app.start_agent()

        mock_controls.update_button_states.reset_mock()

        app.stop_agent()

        # Should have been called with transitioning=True first, then stopped state
        calls = mock_controls.update_button_states.call_args_list
        assert len(calls) == 2
        # First call: transitioning
        assert calls[0].kwargs == {"is_running": True, "is_transitioning": True} or \
               calls[0] == ((), {"is_running": True, "is_transitioning": True})
        # Second call: final stopped state
        assert calls[1].kwargs == {"is_running": False, "is_transitioning": False} or \
               calls[1] == ((), {"is_running": False, "is_transitioning": False})

    def test_stop_agent_calls_request_stop(self):
        """stop_agent() calls request_stop() on the AgentThread."""
        app, _, mock_at_class, _, _, _, _, _ = _build_app()

        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = True
        mock_at_class.return_value = mock_at_instance
        app.start_agent()

        app.stop_agent()

        mock_at_instance.request_stop.assert_called_once()

    def test_start_agent_enables_token_input(self):
        """start_agent() enables the token input frame."""
        app, _, mock_at_class, _, mock_token_input, _, _, _ = _build_app()

        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = False
        mock_at_class.return_value = mock_at_instance

        mock_token_input.set_enabled.reset_mock()
        app.start_agent()

        mock_token_input.set_enabled.assert_called_with(True)

    def test_stop_agent_disables_token_input(self):
        """stop_agent() disables the token input frame."""
        app, _, mock_at_class, _, mock_token_input, _, _, _ = _build_app()

        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = True
        mock_at_class.return_value = mock_at_instance
        app.start_agent()

        mock_token_input.set_enabled.reset_mock()
        app.stop_agent()

        mock_token_input.set_enabled.assert_called_with(False)

    def test_start_agent_no_op_when_already_running(self):
        """start_agent() is a no-op if agent is already running."""
        app, _, mock_at_class, mock_controls, _, _, _, _ = _build_app()

        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = True
        mock_at_class.return_value = mock_at_instance

        # First start
        app.start_agent()
        # Now the _agent_thread is set and is_running returns True

        # Second start should be no-op
        mock_at_class.reset_mock()
        app.start_agent()

        # AgentThread constructor should NOT have been called again
        mock_at_class.assert_not_called()


# ===========================================================================
# Test: on_closing triggers agent stop (Req 8.6)
# ===========================================================================


class TestOnClosing:
    """Tests for on_closing method."""

    def test_on_closing_stops_running_agent(self):
        """on_closing() calls request_stop() if agent is running."""
        app, _, mock_at_class, _, _, _, _, _ = _build_app()

        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = True
        mock_at_class.return_value = mock_at_instance
        app.start_agent()

        app.on_closing()

        mock_at_instance.request_stop.assert_called_once()

    def test_on_closing_does_not_stop_if_not_running(self):
        """on_closing() does not call request_stop() if no agent thread."""
        app, _, _, _, _, _, _, _ = _build_app()

        # No start_agent() called, so _agent_thread is None
        # Should not raise
        app.on_closing()

    def test_on_closing_destroys_window(self):
        """on_closing() always destroys the window."""
        app, _, mock_at_class, _, _, _, _, _ = _build_app()

        # Patch destroy on the instance
        app.destroy = MagicMock()

        app.on_closing()

        app.destroy.assert_called_once()

    def test_on_closing_destroys_window_after_stopping_agent(self):
        """on_closing() stops the agent before destroying the window."""
        app, _, mock_at_class, _, _, _, _, _ = _build_app()

        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = True
        mock_at_class.return_value = mock_at_instance
        app.start_agent()

        # Track call order
        call_order = []
        mock_at_instance.request_stop.side_effect = lambda: call_order.append("stop")
        app.destroy = MagicMock(side_effect=lambda: call_order.append("destroy"))

        app.on_closing()

        assert call_order == ["stop", "destroy"]


# ===========================================================================
# Test: Initial state (Req 3.7, 5.6)
# ===========================================================================


class TestInitialState:
    """Tests for initial application state before agent is started."""

    def test_token_input_initially_disabled(self):
        """Token input is disabled on construction (agent not running)."""
        app, _, _, _, mock_token_input, _, _, _ = _build_app()

        # set_enabled(False) should have been called during __init__
        mock_token_input.set_enabled.assert_called_with(False)

    def test_initial_agent_thread_is_none(self):
        """_agent_thread is None before start_agent is called."""
        app, _, _, _, _, _, _, _ = _build_app()

        assert app._agent_thread is None

    def test_state_queue_initially_empty(self):
        """State queue is empty on construction."""
        app, _, _, _, _, _, _, _ = _build_app()

        assert app._state_queue.empty()


# ===========================================================================
# Test: add_token error routing to Alerts_Log (Req 5.3)
# ===========================================================================


class TestAddTokenErrorRouting:
    """Tests for _on_add error handling — errors routed to Alerts_Log."""

    def test_add_token_error_appended_to_alerts_log(self):
        """When add_token returns Err, the error message is appended to alerts_log."""
        app, mock_agent, mock_at_class, _, _, mock_alerts_log, _, _ = _build_app()

        # Set up agent thread as running
        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = True
        mock_at_class.return_value = mock_at_instance
        app.start_agent()

        # Mock add_token to return an Err result
        mock_result = MagicMock()
        mock_result.is_ok.return_value = False
        mock_result.error = "Token not found on Solana"
        mock_agent.add_token.return_value = mock_result

        mock_alerts_log.append_message.reset_mock()

        app._on_add("InvalidMintAddress123")

        mock_alerts_log.append_message.assert_called_once_with(
            "Add token error: Token not found on Solana"
        )

    def test_add_token_error_preserves_input_text(self):
        """When add_token returns Err, the token input text is NOT cleared."""
        app, mock_agent, mock_at_class, _, mock_token_input, _, _, _ = _build_app()

        # Set up agent thread as running
        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = True
        mock_at_class.return_value = mock_at_instance
        app.start_agent()

        # Mock add_token to return an Err result
        mock_result = MagicMock()
        mock_result.is_ok.return_value = False
        mock_result.error = "Token not found"
        mock_agent.add_token.return_value = mock_result

        mock_token_input.clear_input.reset_mock()

        app._on_add("SomeMintAddress")

        # clear_input should NOT have been called
        mock_token_input.clear_input.assert_not_called()

    def test_add_token_success_clears_input(self):
        """When add_token returns Ok, the token input is cleared."""
        app, mock_agent, mock_at_class, _, mock_token_input, _, _, _ = _build_app()

        # Set up agent thread as running
        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = True
        mock_at_class.return_value = mock_at_instance
        app.start_agent()

        # Mock add_token to return Ok result
        mock_result = MagicMock()
        mock_result.is_ok.return_value = True
        mock_agent.add_token.return_value = mock_result

        mock_token_input.clear_input.reset_mock()

        app._on_add("ValidMintAddress123")

        mock_token_input.clear_input.assert_called_once()

    def test_add_token_success_does_not_append_to_alerts(self):
        """When add_token returns Ok, nothing is appended to alerts_log."""
        app, mock_agent, mock_at_class, _, _, mock_alerts_log, _, _ = _build_app()

        # Set up agent thread as running
        mock_at_instance = MagicMock()
        mock_at_instance.is_running.return_value = True
        mock_at_class.return_value = mock_at_instance
        app.start_agent()

        # Mock add_token to return Ok result
        mock_result = MagicMock()
        mock_result.is_ok.return_value = True
        mock_agent.add_token.return_value = mock_result

        mock_alerts_log.append_message.reset_mock()

        app._on_add("ValidMintAddress123")

        mock_alerts_log.append_message.assert_not_called()

    def test_on_add_no_op_when_agent_not_running(self):
        """_on_add does nothing if agent thread is not running."""
        app, mock_agent, _, _, _, _, _, _ = _build_app()

        # No start_agent() — _agent_thread is None
        app._on_add("SomeMintAddress")

        mock_agent.add_token.assert_not_called()
