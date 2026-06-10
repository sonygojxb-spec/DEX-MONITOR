"""Property-based tests for the GUIChannel deliver contract.

Tests validate that GUIChannel.deliver() returns the correct DeliveryResult
based on the widget's availability state, as specified in the design document.
"""

from __future__ import annotations

import tkinter
from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.gui.channel import GUIChannel
from dex_agent.models import Severity
from dex_agent.providers.interfaces import Alert, DeliveryResult
from dex_agent.result import Ok

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

alert_strategy = st.builds(
    Alert,
    title=st.text(min_size=0, max_size=100),
    body=st.text(min_size=0, max_size=500),
    severity=st.sampled_from(list(Severity)),
    pair_id=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    is_exit_signal=st.booleans(),
)


# ---------------------------------------------------------------------------
# Feature: dex-gui, Property 11: GUIChannel deliver contract
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(alert=alert_strategy, widget_available=st.booleans())
def test_property_11_gui_channel_deliver_contract(
    alert: Alert, widget_available: bool
) -> None:
    """**Validates: Requirements 7.4, 7.6**

    For any Alert delivered via GUIChannel.deliver():
    - If the widget is available, the result SHALL be Ok(DeliveryResult)
      with channel="GUI", delivered=True, and detail="".
    - If the widget is unavailable (None), the result SHALL be
      Ok(DeliveryResult) with delivered=False and detail="widget unavailable",
      without raising an exception.
    """
    channel = GUIChannel()

    if widget_available:
        # Simulate a live widget with a working after() method
        mock_widget = MagicMock()
        mock_widget.after = MagicMock()
        channel.set_widget(mock_widget)
    else:
        # Widget is None (not bound yet or explicitly unavailable)
        pass  # channel._widget remains None from __init__

    result = channel.deliver(alert)

    # Result is always Ok — never Err
    assert isinstance(result, Ok), (
        f"Expected Ok result, got {type(result).__name__}"
    )

    delivery: DeliveryResult = result.value

    # Channel name is always "GUI"
    assert delivery.channel == "GUI", (
        f"Expected channel='GUI', got '{delivery.channel}'"
    )

    if widget_available:
        assert delivery.delivered is True, (
            f"Expected delivered=True when widget available, got {delivery.delivered}"
        )
        assert delivery.detail == "", (
            f"Expected empty detail when delivered, got '{delivery.detail}'"
        )
    else:
        assert delivery.delivered is False, (
            f"Expected delivered=False when widget unavailable, got {delivery.delivered}"
        )
        assert delivery.detail == "widget unavailable", (
            f"Expected detail='widget unavailable', got '{delivery.detail}'"
        )


@settings(max_examples=100)
@given(alert=alert_strategy)
def test_property_11_gui_channel_deliver_destroyed_widget(alert: Alert) -> None:
    """**Validates: Requirements 7.4, 7.6**

    For any Alert delivered via GUIChannel.deliver() when the widget has been
    destroyed (after() raises TclError), the result SHALL be Ok(DeliveryResult)
    with delivered=False and a non-empty detail string, without raising.
    """
    channel = GUIChannel()

    # Simulate a destroyed widget where after() raises TclError
    mock_widget = MagicMock()
    mock_widget.after = MagicMock(side_effect=tkinter.TclError("widget destroyed"))
    channel.set_widget(mock_widget)

    result = channel.deliver(alert)

    # Result is always Ok — never Err
    assert isinstance(result, Ok), (
        f"Expected Ok result, got {type(result).__name__}"
    )

    delivery: DeliveryResult = result.value

    # Channel name is always "GUI"
    assert delivery.channel == "GUI", (
        f"Expected channel='GUI', got '{delivery.channel}'"
    )

    # Destroyed widget means delivery failed gracefully
    assert delivery.delivered is False, (
        f"Expected delivered=False when widget destroyed, got {delivery.delivered}"
    )
    assert delivery.detail != "", (
        "Expected non-empty detail when widget destroyed"
    )
    assert delivery.detail == "widget unavailable", (
        f"Expected detail='widget unavailable', got '{delivery.detail}'"
    )
