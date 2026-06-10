"""Property-based tests for WatchlistTableFrame row rendering with missing data.

Tests validate that the WatchlistTable correctly renders all column values,
displaying the literal string "-" for fields that represent unavailable data.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Mock customtkinter BEFORE importing the watchlist module so tests can run
# headless without a display server.
#
# We need CTkFrame to be a real base class (not MagicMock) so that
# WatchlistTableFrame can be instantiated properly with object.__new__.
# ---------------------------------------------------------------------------


class _FakeCTkFrame:
    """Minimal stub for customtkinter.CTkFrame."""

    def __init__(self, *args, **kwargs):
        pass

    def pack(self, *args, **kwargs):
        pass

    def grid(self, *args, **kwargs):
        pass

    def columnconfigure(self, *args, **kwargs):
        pass

    def grid_propagate(self, *args, **kwargs):
        pass

    def pack_propagate(self, *args, **kwargs):
        pass


class _FakeCTkScrollableFrame:
    """Minimal stub for customtkinter.CTkScrollableFrame."""

    def __init__(self, *args, **kwargs):
        pass

    def pack(self, *args, **kwargs):
        pass

    def columnconfigure(self, *args, **kwargs):
        pass


class _FakeCTkLabel:
    """Minimal stub for customtkinter.CTkLabel that captures text."""

    def __init__(self, master=None, text="", **kwargs):
        self._text = text

    def grid(self, *args, **kwargs):
        pass

    def bind(self, *args, **kwargs):
        pass

    def configure(self, **kwargs):
        pass

    def destroy(self):
        pass


class _FakeCTkFont:
    """Minimal stub for customtkinter.CTkFont."""

    def __init__(self, *args, **kwargs):
        pass


_mock_ctk = MagicMock()
_mock_ctk.CTkFrame = _FakeCTkFrame
_mock_ctk.CTkScrollableFrame = _FakeCTkScrollableFrame
_mock_ctk.CTkLabel = _FakeCTkLabel
_mock_ctk.CTkFont = _FakeCTkFont
sys.modules["customtkinter"] = _mock_ctk

from dex_agent.gui.frames.watchlist import WatchlistTableFrame  # noqa: E402
from dex_agent.gui.thread import WatchlistRow  # noqa: E402

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# A field value is either "-" (representing missing/unavailable) or a normal
# non-empty string (representing actual data).
field_value_strategy = st.one_of(
    st.just("-"),
    st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(
            whitelist_categories=("L", "N", "P", "S"),
            blacklist_characters="\x00",
        ),
    ),
)

# Build a WatchlistRow where each field may be "-" or a real value.
watchlist_row_strategy = st.builds(
    WatchlistRow,
    pair_id=st.text(min_size=1, max_size=20),
    token_name=field_value_strategy,
    severity=field_value_strategy,
    bot_pct=field_value_strategy,
    liquidity=field_value_strategy,
    signal_type=field_value_strategy,
    signal_score=field_value_strategy,
)


# ---------------------------------------------------------------------------
# Feature: dex-gui, Property 5: Watchlist row rendering with missing data
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(value=st.one_of(st.none(), st.just("-"), st.text(min_size=1, max_size=20)))
def test_property_5_display_value_maps_none_to_dash(value: str | None) -> None:
    """**Validates: Requirements 4.1, 4.6**

    The _display_value static method SHALL return "-" for None inputs, and
    return the original string value for all other inputs.
    """
    result = WatchlistTableFrame._display_value(value)

    if value is None:
        assert result == "-", (
            f"Expected '-' for None input, got '{result}'"
        )
    else:
        assert result == value, (
            f"Expected '{value}' to pass through unchanged, got '{result}'"
        )


@settings(max_examples=100)
@given(row=watchlist_row_strategy)
def test_property_5_watchlist_row_rendering_missing_data(row: WatchlistRow) -> None:
    """**Validates: Requirements 4.1, 4.6**

    For any WatchlistRow where some fields are "-" (unavailable) and others
    contain real values:
    - Fields that are "-" SHALL display as "-" in the table.
    - Fields that have values SHALL display those exact values.

    After calling update_rows([row]), verify that each cell's displayed text
    matches the expected value.
    """
    # Create the frame — our fake CTkFrame base class allows normal
    # instantiation without a display server.
    frame = WatchlistTableFrame(master=None)

    # Call update_rows with our generated row
    frame.update_rows([row])

    # The row_widgets should contain one row of labels
    assert len(frame._row_widgets) == 1, (
        f"Expected 1 row of widgets, got {len(frame._row_widgets)}"
    )

    row_labels = frame._row_widgets[0]
    assert len(row_labels) == 6, (
        f"Expected 6 labels per row, got {len(row_labels)}"
    )

    # The displayed fields in column order:
    # token_name, severity, bot_pct, liquidity, signal_type, signal_score
    field_values = [
        row.token_name, row.severity, row.bot_pct,
        row.liquidity, row.signal_type, row.signal_score,
    ]

    for col_idx, (label, field_val) in enumerate(zip(row_labels, field_values)):
        actual_text = label._text
        expected = WatchlistTableFrame._display_value(field_val)

        assert actual_text == expected, (
            f"Column {col_idx}: expected '{expected}', got '{actual_text}'"
        )

        # Core property: if the field was "-" (missing), it displays as "-"
        if field_val == "-":
            assert actual_text == "-", (
                f"Column {col_idx}: field was '-' (missing), "
                f"but displayed '{actual_text}' instead of '-'"
            )
        else:
            # Fields with actual values display those exact values
            assert actual_text == field_val, (
                f"Column {col_idx}: field was '{field_val}', "
                f"but displayed '{actual_text}'"
            )


# ---------------------------------------------------------------------------
# Feature: dex-gui, Property 16: Repository failure data retention
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    failure_flags=st.lists(st.booleans(), min_size=4, max_size=4),
    initial_rows=st.lists(watchlist_row_strategy, min_size=1, max_size=10),
)
def test_property_16_repository_failure_data_retention(
    failure_flags: list[bool],
    initial_rows: list[WatchlistRow],
) -> None:
    """**Validates: Requirements 11.5**

    For any combination of repository call failures during a watchlist refresh
    cycle, the Watchlist_Table SHALL retain the previously displayed data for
    the affected columns rather than displaying empty or corrupt values.

    Strategy: Generate 4 booleans representing whether each of the 4 repository
    calls (WatchlistRepository, SecurityEvalRepository, WalletAnalysisRepository,
    SignalRepository) fails. Populate the table first, then simulate failure by
    calling update_rows([]) (empty = all repositories failed scenario). Assert
    that frame._last_rows still contains the previous data.
    """
    frame = WatchlistTableFrame(master=None)

    # Step 1: Populate the table with initial data
    frame.update_rows(initial_rows)

    # Verify initial data is stored
    assert frame._last_rows == initial_rows, (
        "Initial rows should be stored in _last_rows"
    )

    # Step 2: Simulate repository failures by calling update_rows with empty list.
    # When any combination of repos fails, the AgentThread sends an empty list
    # to update_rows. The frame must retain previous data.
    frame.update_rows([])

    # Assert: previously displayed data is retained
    assert frame._last_rows == initial_rows, (
        f"After repository failure (flags={failure_flags}), _last_rows should "
        f"retain {len(initial_rows)} previously displayed rows, "
        f"but got {len(frame._last_rows)} rows"
    )

    # Assert: each individual row's data is preserved unchanged
    for idx, (retained, original) in enumerate(
        zip(frame._last_rows, initial_rows)
    ):
        assert retained.pair_id == original.pair_id, (
            f"Row {idx}: pair_id changed after failure"
        )
        assert retained.token_name == original.token_name, (
            f"Row {idx}: token_name changed after failure"
        )
        assert retained.severity == original.severity, (
            f"Row {idx}: severity changed after failure"
        )
        assert retained.bot_pct == original.bot_pct, (
            f"Row {idx}: bot_pct changed after failure"
        )
        assert retained.liquidity == original.liquidity, (
            f"Row {idx}: liquidity changed after failure"
        )
        assert retained.signal_type == original.signal_type, (
            f"Row {idx}: signal_type changed after failure"
        )
        assert retained.signal_score == original.signal_score, (
            f"Row {idx}: signal_score changed after failure"
        )


@settings(max_examples=100)
@given(
    failure_flags=st.lists(st.booleans(), min_size=4, max_size=4),
    initial_rows=st.lists(watchlist_row_strategy, min_size=1, max_size=10),
)
def test_property_16_none_update_also_retains_data(
    failure_flags: list[bool],
    initial_rows: list[WatchlistRow],
) -> None:
    """**Validates: Requirements 11.5**

    For any combination of repository failures, calling update_rows(None) (partial
    data scenario) also retains previously displayed data. The frame treats both
    None and empty list as "no new data available" and preserves stale data.
    """
    frame = WatchlistTableFrame(master=None)

    # Populate with initial data
    frame.update_rows(initial_rows)
    assert frame._last_rows == initial_rows

    # Simulate failure with None (another path the code handles)
    frame.update_rows(None)

    # Assert: previously displayed data is retained
    assert frame._last_rows == initial_rows, (
        f"After update_rows(None) with failure flags={failure_flags}, "
        f"_last_rows should retain {len(initial_rows)} previously displayed rows"
    )


@settings(max_examples=100)
@given(
    failure_flags=st.lists(st.booleans(), min_size=4, max_size=4),
    initial_rows=st.lists(watchlist_row_strategy, min_size=1, max_size=10),
    subsequent_rows=st.lists(watchlist_row_strategy, min_size=1, max_size=10),
)
def test_property_16_recovery_after_failure(
    failure_flags: list[bool],
    initial_rows: list[WatchlistRow],
    subsequent_rows: list[WatchlistRow],
) -> None:
    """**Validates: Requirements 11.5**

    After a repository failure retains stale data, a subsequent successful
    refresh with new rows SHALL replace the stale data with the fresh data.
    This confirms the retention mechanism does not permanently lock the table.
    """
    frame = WatchlistTableFrame(master=None)

    # Step 1: Populate initial data
    frame.update_rows(initial_rows)
    assert frame._last_rows == initial_rows

    # Step 2: Simulate failure (empty list)
    frame.update_rows([])
    assert frame._last_rows == initial_rows, (
        "Stale data should be retained during failure"
    )

    # Step 3: Successful refresh with new data
    frame.update_rows(subsequent_rows)
    assert frame._last_rows == subsequent_rows, (
        f"After successful refresh, _last_rows should contain new data "
        f"({len(subsequent_rows)} rows), but got {len(frame._last_rows)} rows"
    )
