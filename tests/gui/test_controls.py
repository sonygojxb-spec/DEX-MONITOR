"""Unit tests for ControlsFrame (dex_agent/gui/frames/controls.py).

Tests validate the controls frame's behavior: Start/Stop/Settings callbacks
and button state management based on agent running/stopped/transitioning states.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch


# Mock customtkinter before importing the module under test
_mock_ctk_module = MagicMock()
# We need CTkFrame to be a regular class that can be subclassed
_mock_ctk_module.CTkFrame = type("CTkFrame", (), {"__init__": lambda self, *a, **kw: None})
_mock_ctk_module.CTkButton = MagicMock


def _make_frame(on_start=None, on_stop=None, on_settings=None):
    """Create a ControlsFrame with mocked CustomTkinter widgets."""
    if on_start is None:
        on_start = MagicMock()
    if on_stop is None:
        on_stop = MagicMock()
    if on_settings is None:
        on_settings = MagicMock()

    mock_start_btn = MagicMock()
    mock_stop_btn = MagicMock()
    mock_settings_btn = MagicMock()

    with patch.dict(sys.modules, {"customtkinter": _mock_ctk_module}):
        # Patch CTkButton constructor to return our mocks in order
        with patch.object(
            _mock_ctk_module,
            "CTkButton",
            side_effect=[mock_start_btn, mock_stop_btn, mock_settings_btn],
        ):
            # Force reimport to pick up our patched module
            if "dex_agent.gui.frames.controls" in sys.modules:
                del sys.modules["dex_agent.gui.frames.controls"]

            from dex_agent.gui.frames.controls import ControlsFrame

            mock_master = MagicMock()
            frame = ControlsFrame(mock_master, on_start, on_stop, on_settings)

    return frame, mock_start_btn, mock_stop_btn, mock_settings_btn, on_start, on_stop, on_settings


class TestControlsFrameCallbacks:
    """Tests for button click callbacks."""

    def test_start_button_calls_on_start(self):
        """Start button calls the on_start callback."""
        frame, _, _, _, on_start, _, _ = _make_frame()

        frame._handle_start()

        on_start.assert_called_once()

    def test_stop_button_calls_on_stop(self):
        """Stop button calls the on_stop callback."""
        frame, _, _, _, _, on_stop, _ = _make_frame()

        frame._handle_stop()

        on_stop.assert_called_once()

    def test_settings_button_calls_on_settings(self):
        """Settings button calls the on_settings callback."""
        frame, _, _, _, _, _, on_settings = _make_frame()

        frame._handle_settings()

        on_settings.assert_called_once()


class TestControlsFrameInitialState:
    """Tests for initial button states."""

    def test_stop_button_initially_disabled(self):
        """Stop button is disabled on construction (agent starts stopped)."""
        frame, _, mock_stop_btn, _, _, _, _ = _make_frame()

        mock_stop_btn.configure.assert_called_with(state="disabled")


class TestControlsFrameUpdateButtonStates:
    """Tests for update_button_states method."""

    def test_transitioning_disables_both_start_and_stop(self):
        """When transitioning, both Start and Stop are disabled."""
        frame, mock_start_btn, mock_stop_btn, mock_settings_btn, _, _, _ = _make_frame()
        mock_start_btn.configure.reset_mock()
        mock_stop_btn.configure.reset_mock()
        mock_settings_btn.configure.reset_mock()

        frame.update_button_states(is_running=False, is_transitioning=True)

        mock_start_btn.configure.assert_called_with(state="disabled")
        mock_stop_btn.configure.assert_called_with(state="disabled")
        mock_settings_btn.configure.assert_called_with(state="normal")

    def test_running_disables_start_enables_stop(self):
        """When running (not transitioning), Start disabled and Stop enabled."""
        frame, mock_start_btn, mock_stop_btn, mock_settings_btn, _, _, _ = _make_frame()
        mock_start_btn.configure.reset_mock()
        mock_stop_btn.configure.reset_mock()
        mock_settings_btn.configure.reset_mock()

        frame.update_button_states(is_running=True, is_transitioning=False)

        mock_start_btn.configure.assert_called_with(state="disabled")
        mock_stop_btn.configure.assert_called_with(state="normal")
        mock_settings_btn.configure.assert_called_with(state="normal")

    def test_stopped_enables_start_disables_stop(self):
        """When stopped (not transitioning), Start enabled and Stop disabled."""
        frame, mock_start_btn, mock_stop_btn, mock_settings_btn, _, _, _ = _make_frame()
        mock_start_btn.configure.reset_mock()
        mock_stop_btn.configure.reset_mock()
        mock_settings_btn.configure.reset_mock()

        frame.update_button_states(is_running=False, is_transitioning=False)

        mock_start_btn.configure.assert_called_with(state="normal")
        mock_stop_btn.configure.assert_called_with(state="disabled")
        mock_settings_btn.configure.assert_called_with(state="normal")

    def test_settings_always_enabled_when_transitioning(self):
        """Settings button remains enabled even during transitioning."""
        frame, _, _, mock_settings_btn, _, _, _ = _make_frame()
        mock_settings_btn.configure.reset_mock()

        frame.update_button_states(is_running=True, is_transitioning=True)

        mock_settings_btn.configure.assert_called_with(state="normal")

    def test_settings_always_enabled_when_running(self):
        """Settings button remains enabled when agent is running."""
        frame, _, _, mock_settings_btn, _, _, _ = _make_frame()
        mock_settings_btn.configure.reset_mock()

        frame.update_button_states(is_running=True, is_transitioning=False)

        mock_settings_btn.configure.assert_called_with(state="normal")

    def test_settings_always_enabled_when_stopped(self):
        """Settings button remains enabled when agent is stopped."""
        frame, _, _, mock_settings_btn, _, _, _ = _make_frame()
        mock_settings_btn.configure.reset_mock()

        frame.update_button_states(is_running=False, is_transitioning=False)

        mock_settings_btn.configure.assert_called_with(state="normal")
