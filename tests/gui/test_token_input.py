"""Unit tests for TokenInputFrame (dex_agent/gui/frames/token_input.py).

Tests validate the token input frame's behavior: Add/Remove callbacks,
whitespace rejection, enable/disable, clear_input, and get_input.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch


# Mock customtkinter before importing the module under test
_mock_ctk_module = MagicMock()
# We need CTkFrame to be a regular class that can be subclassed
_mock_ctk_module.CTkFrame = type("CTkFrame", (), {"__init__": lambda self, *a, **kw: None})
_mock_ctk_module.CTkEntry = MagicMock
_mock_ctk_module.CTkButton = MagicMock


def _make_frame(on_add=None, on_remove=None):
    """Create a TokenInputFrame with mocked CustomTkinter widgets."""
    if on_add is None:
        on_add = MagicMock()
    if on_remove is None:
        on_remove = MagicMock()

    mock_entry = MagicMock()
    mock_add_btn = MagicMock()
    mock_remove_btn = MagicMock()

    with patch.dict(sys.modules, {"customtkinter": _mock_ctk_module}):
        # Patch the CTkEntry and CTkButton constructors to return our mocks
        with (
            patch.object(_mock_ctk_module, "CTkEntry", return_value=mock_entry),
            patch.object(
                _mock_ctk_module,
                "CTkButton",
                side_effect=[mock_add_btn, mock_remove_btn],
            ),
        ):
            # Force reimport to pick up our patched module
            if "dex_agent.gui.frames.token_input" in sys.modules:
                del sys.modules["dex_agent.gui.frames.token_input"]

            from dex_agent.gui.frames.token_input import TokenInputFrame

            mock_master = MagicMock()
            frame = TokenInputFrame(mock_master, on_add, on_remove)

    return frame, mock_entry, on_add, on_remove


class TestTokenInputFrameAdd:
    """Tests for the Add button behavior."""

    def test_add_calls_on_add_with_stripped_text(self):
        """Add button calls on_add with stripped mint address."""
        frame, mock_entry, on_add, _ = _make_frame()
        mock_entry.get.return_value = "  So11111111111111111111111111111111111111112  "

        frame._handle_add()

        on_add.assert_called_once_with(
            "So11111111111111111111111111111111111111112"
        )

    def test_add_with_valid_address_calls_on_add(self):
        """Add button calls on_add with the exact stripped text."""
        frame, mock_entry, on_add, _ = _make_frame()
        mock_entry.get.return_value = "TokenMintAddress123"

        frame._handle_add()

        on_add.assert_called_once_with("TokenMintAddress123")

    def test_add_with_empty_string_is_noop(self):
        """Add button with empty input does not call on_add."""
        frame, mock_entry, on_add, _ = _make_frame()
        mock_entry.get.return_value = ""

        frame._handle_add()

        on_add.assert_not_called()

    def test_add_with_whitespace_only_is_noop(self):
        """Add button with whitespace-only input does not call on_add."""
        frame, mock_entry, on_add, _ = _make_frame()
        mock_entry.get.return_value = "   \t\n  "

        frame._handle_add()

        on_add.assert_not_called()

    def test_add_when_disabled_is_noop(self):
        """Add button does nothing when frame is disabled."""
        frame, mock_entry, on_add, _ = _make_frame()
        mock_entry.get.return_value = "ValidAddress123"
        frame.set_enabled(False)

        frame._handle_add()

        on_add.assert_not_called()


class TestTokenInputFrameRemove:
    """Tests for the Remove button behavior."""

    def test_remove_calls_on_remove(self):
        """Remove button calls on_remove callback."""
        frame, _, _, on_remove = _make_frame()

        frame._handle_remove()

        on_remove.assert_called_once()

    def test_remove_when_disabled_is_noop(self):
        """Remove button does nothing when frame is disabled."""
        frame, _, _, on_remove = _make_frame()
        frame.set_enabled(False)

        frame._handle_remove()

        on_remove.assert_not_called()


class TestTokenInputFrameSetEnabled:
    """Tests for set_enabled behavior."""

    def test_set_enabled_false_disables_buttons(self):
        """set_enabled(False) configures both buttons to disabled state."""
        frame, _, _, _ = _make_frame()

        frame.set_enabled(False)

        frame._add_button.configure.assert_called_with(state="disabled")
        frame._remove_button.configure.assert_called_with(state="disabled")

    def test_set_enabled_true_enables_buttons(self):
        """set_enabled(True) configures both buttons to normal state."""
        frame, _, _, _ = _make_frame()
        frame.set_enabled(False)
        frame._add_button.configure.reset_mock()
        frame._remove_button.configure.reset_mock()

        frame.set_enabled(True)

        frame._add_button.configure.assert_called_with(state="normal")
        frame._remove_button.configure.assert_called_with(state="normal")


class TestTokenInputFrameClearAndGetInput:
    """Tests for clear_input and get_input methods."""

    def test_clear_input_deletes_entry_content(self):
        """clear_input() calls delete(0, 'end') on the entry widget."""
        frame, mock_entry, _, _ = _make_frame()

        frame.clear_input()

        mock_entry.delete.assert_called_once_with(0, "end")

    def test_get_input_returns_entry_text(self):
        """get_input() returns the current entry text."""
        frame, mock_entry, _, _ = _make_frame()
        mock_entry.get.return_value = "SomeAddress"

        result = frame.get_input()

        assert result == "SomeAddress"


# ---------------------------------------------------------------------------
# Property-Based Tests (Hypothesis)
# ---------------------------------------------------------------------------
from hypothesis import given, settings
from hypothesis import strategies as st


# Feature: dex-gui, Property 7: Add token workflow correctness
class TestAddTokenWorkflowProperty:
    """Property test: for any non-empty, non-whitespace mint address,
    on_add is called with the exact stripped string.

    Validates: Requirements 5.2, 5.3, 5.5
    """

    @given(
        text=st.text(
            min_size=1,
            max_size=44,
            alphabet=st.characters(blacklist_categories=("Cs",)),
        ).filter(lambda t: t.strip() != "")
    )
    @settings(max_examples=100)
    def test_on_add_called_with_exact_stripped_text(self, text: str):
        """For any non-empty non-whitespace text, _handle_add calls on_add
        with the exact stripped string."""
        frame, mock_entry, on_add, _ = _make_frame()
        mock_entry.get.return_value = text

        frame._handle_add()

        on_add.assert_called_once_with(text.strip())


# ---------------------------------------------------------------------------
# Property-Based Tests (Hypothesis)
# ---------------------------------------------------------------------------

from hypothesis import given, settings
from hypothesis import strategies as st


# Feature: dex-gui, Property 8: Whitespace input rejection
class TestWhitespaceInputRejectionProperty:
    """Property 8: For any string composed entirely of whitespace characters
    (including empty string), clicking Add SHALL NOT invoke add_token and
    SHALL leave the Token_Input text unchanged.

    **Validates: Requirements 5.7**
    """

    @given(whitespace_input=st.from_regex(r"^\s*$", fullmatch=True))
    @settings(max_examples=100)
    def test_whitespace_only_input_never_calls_on_add(self, whitespace_input: str):
        """For any whitespace-only string, _handle_add never invokes on_add."""
        frame, mock_entry, on_add, _ = _make_frame()
        mock_entry.get.return_value = whitespace_input

        frame._handle_add()

        on_add.assert_not_called()

    @given(whitespace_input=st.from_regex(r"^\s*$", fullmatch=True))
    @settings(max_examples=100)
    def test_whitespace_only_input_leaves_text_unchanged(self, whitespace_input: str):
        """For any whitespace-only string, _handle_add does not modify the entry."""
        frame, mock_entry, on_add, _ = _make_frame()
        mock_entry.get.return_value = whitespace_input

        frame._handle_add()

        # Entry text should NOT be cleared (delete should not be called)
        mock_entry.delete.assert_not_called()
