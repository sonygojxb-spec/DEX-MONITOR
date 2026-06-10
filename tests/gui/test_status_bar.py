"""Property-based tests for the Status Bar frame (dex_agent.gui.frames.status_bar).

Tests validate that the StatusBarFrame correctly displays numeric values and
formatted time durations as specified in the design document.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Mock customtkinter before importing any GUI modules
# ---------------------------------------------------------------------------

_mock_ctk = MagicMock()


class FakeCTkLabel:
    """Minimal fake CTkLabel that stores text via configure()."""

    def __init__(self, *args, **kwargs):
        self._text = kwargs.get("text", "")

    def configure(self, **kwargs):
        if "text" in kwargs:
            self._text = kwargs["text"]

    def cget(self, key):
        if key == "text":
            return self._text
        return None

    def grid(self, **kwargs):
        pass


class FakeCTkFrame:
    """Minimal fake CTkFrame base class."""

    def __init__(self, *args, **kwargs):
        pass

    def grid_columnconfigure(self, *args, **kwargs):
        pass

    def after(self, ms, func=None):
        """Fake after() — return a dummy ID without scheduling."""
        return "fake_after_id"

    def after_cancel(self, after_id):
        pass


# Patch the module so imports resolve correctly
_mock_ctk.CTkFrame = FakeCTkFrame
_mock_ctk.CTkLabel = FakeCTkLabel
_mock_ctk.CTkBaseClass = object

sys.modules.setdefault("customtkinter", _mock_ctk)

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.gui.thread import AgentState, WatchlistRow
from dex_agent.gui.frames.status_bar import StatusBarFrame, format_duration


# ---------------------------------------------------------------------------
# Feature: dex-gui, Property 3: Status bar numeric accuracy
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    active_pairs=st.integers(min_value=0, max_value=10000),
    alerts_count=st.integers(min_value=0, max_value=10000),
)
def test_property_3_status_bar_numeric_accuracy(
    active_pairs: int,
    alerts_count: int,
) -> None:
    """**Validates: Requirements 3.1, 3.4**

    For any AgentState with an active_pairs count and alerts_count, the
    Status_Bar SHALL display those exact integer values in their respective
    labels.
    """
    # Create a StatusBarFrame instance (uses our fake CTk classes)
    frame = StatusBarFrame.__new__(StatusBarFrame)
    # Manually initialize since __init__ relies on CTkFrame.__init__
    frame._is_running = False
    frame._uptime_seconds = 0.0
    frame._last_tick_time = None
    frame._after_id = None
    frame._pairs_title = FakeCTkLabel(text="Active Pairs")
    frame._pairs_value = FakeCTkLabel(text="0")
    frame._uptime_title = FakeCTkLabel(text="Uptime")
    frame._uptime_value = FakeCTkLabel(text="00:00:00")
    frame._tick_title = FakeCTkLabel(text="Last Tick")
    frame._tick_value = FakeCTkLabel(text="--:--:--")
    frame._alerts_title = FakeCTkLabel(text="Alerts")
    frame._alerts_value = FakeCTkLabel(text="0")
    # Provide after/after_cancel stubs for the uptime ticker
    frame.after = lambda ms, func=None: "fake_after_id"
    frame.after_cancel = lambda after_id: None

    # Create an AgentState with the generated values
    state = AgentState(
        active_pairs=active_pairs,
        uptime_seconds=42.0,
        last_tick_time="12:00:00",
        alerts_count=alerts_count,
        watchlist_rows=[],
        is_running=True,
    )

    # Call update_state
    frame.update_state(state)

    # Assert displayed values match input integers exactly
    displayed_pairs = frame._pairs_value.cget("text")
    displayed_alerts = frame._alerts_value.cget("text")

    assert displayed_pairs == str(active_pairs), (
        f"Expected pairs '{active_pairs}', displayed '{displayed_pairs}'"
    )
    assert displayed_alerts == str(alerts_count), (
        f"Expected alerts '{alerts_count}', displayed '{displayed_alerts}'"
    )
