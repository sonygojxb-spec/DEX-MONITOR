"""Property-based tests for SettingsDialog (dex_agent/gui/dialogs/settings.py).

Tests validate the settings dialog's type coercion behavior on save: integer-typed
parameters are coerced to int, decimal-typed parameters to Decimal.
Also validates that the dialog fields match PARAM_RANGES exhaustively (Property 12).
"""

from __future__ import annotations

import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.config import PARAM_RANGES
from dex_agent.result import Ok


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Build a mock customtkinter module for headless testing
_mock_ctk_module = MagicMock()


class _MockWidget:
    """A base mock widget that supports pack/grid/place and configure."""

    def __init__(self, *args, **kwargs):
        pass

    def pack(self, *args, **kwargs):
        pass

    def grid(self, *args, **kwargs):
        pass

    def place(self, *args, **kwargs):
        pass

    def configure(self, *args, **kwargs):
        pass

    def insert(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        return ""

    def delete(self, *args, **kwargs):
        pass


class _MockCTkToplevel(_MockWidget):
    """Mock CTkToplevel."""

    def title(self, *a, **kw):
        pass

    def geometry(self, *a, **kw):
        pass

    def resizable(self, *a, **kw):
        pass

    def transient(self, *a, **kw):
        pass

    def grab_set(self, *a, **kw):
        pass

    def grab_release(self, *a, **kw):
        pass

    def destroy(self, *a, **kw):
        pass


_mock_ctk_module.CTkFrame = type(
    "CTkFrame", (_MockWidget,), {"__init__": lambda self, *a, **kw: None}
)
_mock_ctk_module.CTkToplevel = _MockCTkToplevel
_mock_ctk_module.CTkScrollableFrame = lambda *a, **kw: _MockWidget()
_mock_ctk_module.CTkLabel = lambda *a, **kw: _MockWidget()
_mock_ctk_module.CTkEntry = lambda *a, **kw: _MockWidget()
_mock_ctk_module.CTkButton = lambda *a, **kw: _MockWidget()


def _make_settings_dialog(entry_values: dict[str, str]):
    """Create a SettingsDialog with mocked entries returning provided values.

    Args:
        entry_values: mapping from param_name to the string the entry returns
                      on `.get()`.

    Returns:
        (dialog, mock_config_manager) tuple. The mock_config_manager.save
        captures the inputs dict so assertions can inspect coerced types.
    """
    mock_config_manager = MagicMock()
    mock_config_manager.active = None  # Force DEFAULTS path for pre-population

    # Make save() return Ok so the dialog closes cleanly
    mock_config_manager.save.return_value = Ok(MagicMock())

    with patch.dict(sys.modules, {"customtkinter": _mock_ctk_module}):
        # Clear cached import
        if "dex_agent.gui.dialogs.settings" in sys.modules:
            del sys.modules["dex_agent.gui.dialogs.settings"]

        from dex_agent.gui.dialogs.settings import SettingsDialog

        mock_master = MagicMock()

        # Create the dialog (this will build entries internally)
        dialog = SettingsDialog(mock_master, mock_config_manager)

        # Now override the entries with mocked widgets that return our values
        for param_name, text_value in entry_values.items():
            mock_entry = MagicMock()
            mock_entry.get.return_value = text_value
            dialog._entries[param_name] = mock_entry

    return dialog, mock_config_manager


# ---------------------------------------------------------------------------
# Strategies: generate valid numeric values per PARAM_RANGES
# ---------------------------------------------------------------------------

def _integer_params():
    """Return list of (param_name, ParamRange) for integer-typed params."""
    return [(name, pr) for name, pr in PARAM_RANGES.items() if pr.integer]


def _decimal_params():
    """Return list of (param_name, ParamRange) for decimal-typed params."""
    return [(name, pr) for name, pr in PARAM_RANGES.items() if not pr.integer]


@st.composite
def valid_entry_values(draw):
    """Generate a dict of param_name -> string value, where each value is valid
    for its parameter's range.

    For integer params: draw an int in [low, high], convert to str.
    For decimal params: draw a Decimal in [low, high], convert to str.
    """
    values = {}
    for param_name, prange in PARAM_RANGES.items():
        if prange.integer:
            val = draw(
                st.integers(
                    min_value=int(prange.low),
                    max_value=int(prange.high),
                )
            )
            values[param_name] = str(val)
        else:
            # Generate a decimal in the valid range
            val = draw(
                st.decimals(
                    min_value=prange.low,
                    max_value=prange.high,
                    allow_nan=False,
                    allow_infinity=False,
                    places=2,
                )
            )
            values[param_name] = str(val)
    return values


# ---------------------------------------------------------------------------
# Property-Based Tests (Hypothesis)
# ---------------------------------------------------------------------------


# Feature: dex-gui, Property 14: Settings type coercion on save
class TestSettingsTypeCoercionOnSaveProperty:
    """Property 14: For any set of valid user-entered numeric values in the
    SettingsDialog, the config_manager.save() call SHALL receive integer values
    for integer-typed parameters (ParamRange.integer=True) and Decimal values
    for decimal-typed parameters (ParamRange.integer=False).

    **Validates: Requirements 10.4**
    """

    @given(entry_vals=valid_entry_values())
    @settings(max_examples=100)
    def test_save_receives_correct_types_for_all_params(self, entry_vals: dict[str, str]):
        """For any valid numeric entries, save() receives int for integer params
        and Decimal for decimal params."""
        dialog, mock_config_manager = _make_settings_dialog(entry_vals)

        # Trigger save
        dialog._save()

        # Verify save was called
        mock_config_manager.save.assert_called_once()
        captured_inputs = mock_config_manager.save.call_args[0][0]

        # Check every parameter has the correct type
        for param_name, prange in PARAM_RANGES.items():
            value = captured_inputs[param_name]
            if prange.integer:
                assert isinstance(value, int), (
                    f"Expected int for integer param '{param_name}', "
                    f"got {type(value).__name__}: {value!r}"
                )
            else:
                assert isinstance(value, Decimal), (
                    f"Expected Decimal for decimal param '{param_name}', "
                    f"got {type(value).__name__}: {value!r}"
                )


# ---------------------------------------------------------------------------
# Feature: dex-gui, Property 12: Settings dialog fields match PARAM_RANGES
# ---------------------------------------------------------------------------


def _build_dialog_for_field_check():
    """Construct a SettingsDialog with mocked customtkinter and active=None.

    Uses a FakeEntry class that supports insert/get so the dialog builds
    its entries normally (without overriding them afterwards).
    """

    class _FakeEntry:
        """Minimal fake CTkEntry that tracks inserted text."""

        def __init__(self, *args, **kwargs):
            self._text = ""

        def pack(self, *args, **kwargs):
            pass

        def insert(self, index, text):
            self._text = str(text)

        def get(self):
            return self._text

        def delete(self, start, end):
            self._text = ""

        def configure(self, *args, **kwargs):
            pass

    # Build a customtkinter mock that uses our FakeEntry
    mock_ctk = MagicMock()
    mock_ctk.CTkToplevel = _mock_ctk_module.CTkToplevel
    mock_ctk.CTkFrame = MagicMock(return_value=MagicMock())
    mock_ctk.CTkScrollableFrame = MagicMock(return_value=MagicMock())
    mock_ctk.CTkLabel = MagicMock(return_value=MagicMock())
    mock_ctk.CTkButton = MagicMock(return_value=MagicMock())
    mock_ctk.CTkEntry = _FakeEntry

    mock_config_manager = MagicMock()
    mock_config_manager.active = None

    with patch.dict(sys.modules, {"customtkinter": mock_ctk}):
        if "dex_agent.gui.dialogs.settings" in sys.modules:
            del sys.modules["dex_agent.gui.dialogs.settings"]

        from dex_agent.gui.dialogs.settings import SettingsDialog

        mock_master = MagicMock()
        dialog = SettingsDialog(mock_master, mock_config_manager)

    return dialog


class TestSettingsDialogFieldsMatchParamRanges:
    """Property 12: Exhaustive check that every key in PARAM_RANGES has a
    corresponding labeled entry field in the SettingsDialog.

    **Validates: Requirements 10.2**

    This is an exhaustive test (not Hypothesis) since PARAM_RANGES is a fixed set.
    """

    # Feature: dex-gui, Property 12: Settings dialog fields match PARAM_RANGES

    def test_dialog_entries_keys_match_param_ranges_keys(self) -> None:
        """The dialog's _entries dict must contain exactly the same keys as
        PARAM_RANGES — no missing, no extra."""
        # Feature: dex-gui, Property 12: Settings dialog fields match PARAM_RANGES
        dialog = _build_dialog_for_field_check()

        dialog_keys = set(dialog._entries.keys())
        param_keys = set(PARAM_RANGES.keys())

        assert dialog_keys == param_keys, (
            f"Mismatch between dialog entries and PARAM_RANGES.\n"
            f"  Missing from dialog: {param_keys - dialog_keys}\n"
            f"  Extra in dialog: {dialog_keys - param_keys}"
        )

    def test_every_param_range_key_has_corresponding_entry(self) -> None:
        """For each individual key in PARAM_RANGES, the dialog has a corresponding
        entry. Provides per-key diagnostics on failure."""
        # Feature: dex-gui, Property 12: Settings dialog fields match PARAM_RANGES
        dialog = _build_dialog_for_field_check()

        for key in PARAM_RANGES:
            assert key in dialog._entries, (
                f"PARAM_RANGES key '{key}' has no corresponding entry "
                f"in SettingsDialog._entries"
            )

    def test_no_extra_entries_beyond_param_ranges(self) -> None:
        """The dialog must not contain any extra entries beyond what PARAM_RANGES
        defines — exactly 1:1 correspondence."""
        # Feature: dex-gui, Property 12: Settings dialog fields match PARAM_RANGES
        dialog = _build_dialog_for_field_check()

        extra_keys = set(dialog._entries.keys()) - set(PARAM_RANGES.keys())
        assert not extra_keys, (
            f"Dialog contains entries not in PARAM_RANGES: {extra_keys}"
        )

    def test_entry_count_matches_param_ranges_count(self) -> None:
        """The number of entries equals the number of PARAM_RANGES entries."""
        # Feature: dex-gui, Property 12: Settings dialog fields match PARAM_RANGES
        dialog = _build_dialog_for_field_check()

        assert len(dialog._entries) == len(PARAM_RANGES), (
            f"Entry count {len(dialog._entries)} != "
            f"PARAM_RANGES count {len(PARAM_RANGES)}"
        )



# ---------------------------------------------------------------------------
# Feature: dex-gui, Property 15: Settings save error retention
# ---------------------------------------------------------------------------

from dex_agent.config import (
    ConfigValidationError,
    ConfigPersistenceError,
    DEFAULTS,
    REASON_MISSING,
    REASON_NON_NUMERIC,
    REASON_OUT_OF_RANGE,
)
from dex_agent.result import Err


# Strategy for parameter names (any non-empty identifier-like text)
_param_name_st = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(whitelist_categories=("L", "N", "Pc"), whitelist_characters="_"),
)

# Strategy for reason strings
_reason_st = st.sampled_from([REASON_MISSING, REASON_NON_NUMERIC, REASON_OUT_OF_RANGE])

# Strategy to generate ConfigValidationError instances
_validation_error_st = st.builds(
    ConfigValidationError,
    parameter=_param_name_st,
    reason=_reason_st,
    allowed_low=st.one_of(
        st.none(),
        st.decimals(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
    ),
    allowed_high=st.one_of(
        st.none(),
        st.decimals(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
    ),
)

# Strategy to generate ConfigPersistenceError instances
_persistence_error_st = st.builds(
    ConfigPersistenceError,
    detail=st.text(
        min_size=0,
        max_size=100,
        alphabet=st.characters(blacklist_categories=("Cs",)),
    ),
)


def _make_error_dialog(save_result):
    """Create a SettingsDialog where save() returns the given error result.

    Uses FakeEntry widgets that track their text values so we can verify
    value preservation after a save failure.

    Returns (dialog, entry_values_before_save) where entry_values_before_save
    is a dict of {param_name: str_value} captured before _save() is called.
    """

    class _FakeEntry:
        """Minimal fake CTkEntry that tracks inserted/set text."""

        def __init__(self, *args, **kwargs):
            self._text = ""

        def pack(self, *args, **kwargs):
            pass

        def insert(self, index, text):
            self._text = str(text)

        def get(self):
            return self._text

        def delete(self, start, end):
            self._text = ""

        def configure(self, *args, **kwargs):
            pass

    class _FakeLabel:
        """Minimal fake CTkLabel that tracks configure(text=...) calls."""

        def __init__(self, *args, **kwargs):
            self._text = ""

        def pack(self, *args, **kwargs):
            pass

        def configure(self, **kwargs):
            if "text" in kwargs:
                self._text = kwargs["text"]

    mock_ctk = MagicMock()
    mock_ctk.CTkToplevel = _mock_ctk_module.CTkToplevel
    mock_ctk.CTkFrame = MagicMock(return_value=MagicMock())
    mock_ctk.CTkScrollableFrame = MagicMock(return_value=MagicMock())

    # We need to return a real FakeLabel for the error_label specifically
    # The SettingsDialog creates labels for each param row AND the error label.
    # The error label is the LAST CTkLabel created (after all param labels).
    label_instances = []

    def _make_label(*args, **kwargs):
        lbl = _FakeLabel(*args, **kwargs)
        label_instances.append(lbl)
        return lbl

    mock_ctk.CTkLabel = _make_label
    mock_ctk.CTkButton = MagicMock(return_value=MagicMock())
    mock_ctk.CTkEntry = _FakeEntry

    mock_config_manager = MagicMock()
    mock_config_manager.active = None  # Use DEFAULTS path
    mock_config_manager.save.return_value = save_result

    with patch.dict(sys.modules, {"customtkinter": mock_ctk}):
        if "dex_agent.gui.dialogs.settings" in sys.modules:
            del sys.modules["dex_agent.gui.dialogs.settings"]

        from dex_agent.gui.dialogs.settings import SettingsDialog

        mock_master = MagicMock()
        dialog = SettingsDialog(mock_master, mock_config_manager)

    # The error_label is the last CTkLabel instance created
    error_label = label_instances[-1]
    dialog._error_label = error_label

    # Set valid values in each entry so type coercion in _save() succeeds
    # (we need _save to get past the coercion step to reach save())
    for param_name, entry in dialog._entries.items():
        prange = PARAM_RANGES[param_name]
        if prange.integer:
            entry._text = str(int(prange.low))
        else:
            entry._text = str(prange.low)

    # Capture entry values before save
    values_before = {name: entry.get() for name, entry in dialog._entries.items()}

    return dialog, error_label, values_before


class TestSettingsSaveErrorRetentionProperty:
    """Property 15: For any ConfigValidationError or ConfigPersistenceError
    returned by config_manager.save(), the Settings_Dialog SHALL display the
    error's message property, SHALL remain open, and SHALL preserve all
    user-entered values in their respective input fields without modification.

    **Validates: Requirements 10.5, 10.6**
    """

    # Feature: dex-gui, Property 15: Settings save error retention

    @given(error=_validation_error_st)
    @settings(max_examples=100)
    def test_validation_error_displays_message(self, error: ConfigValidationError):
        """For any ConfigValidationError, the error.message is displayed in
        the error label."""
        dialog, error_label, _ = _make_error_dialog(Err(error))

        dialog._save()

        assert error.message in error_label._text, (
            f"Expected error message '{error.message}' in label text "
            f"'{error_label._text}'"
        )

    @given(error=_validation_error_st)
    @settings(max_examples=100)
    def test_validation_error_dialog_remains_open(self, error: ConfigValidationError):
        """For any ConfigValidationError, the dialog is NOT destroyed
        (grab_release and destroy are not called)."""
        dialog, error_label, _ = _make_error_dialog(Err(error))

        # Replace destroy/grab_release with mocks to track calls
        dialog.destroy = MagicMock()
        dialog.grab_release = MagicMock()

        dialog._save()

        dialog.destroy.assert_not_called()
        dialog.grab_release.assert_not_called()

    @given(error=_validation_error_st)
    @settings(max_examples=100)
    def test_validation_error_preserves_field_values(self, error: ConfigValidationError):
        """For any ConfigValidationError, all field values remain unchanged
        after the save attempt."""
        dialog, error_label, values_before = _make_error_dialog(Err(error))

        dialog._save()

        for param_name, entry in dialog._entries.items():
            assert entry.get() == values_before[param_name], (
                f"Field '{param_name}' value changed from "
                f"'{values_before[param_name]}' to '{entry.get()}' after error"
            )

    @given(error=_persistence_error_st)
    @settings(max_examples=100)
    def test_persistence_error_displays_message(self, error: ConfigPersistenceError):
        """For any ConfigPersistenceError, the error.message is displayed in
        the error label."""
        dialog, error_label, _ = _make_error_dialog(Err(error))

        dialog._save()

        assert error.message in error_label._text, (
            f"Expected error message '{error.message}' in label text "
            f"'{error_label._text}'"
        )

    @given(error=_persistence_error_st)
    @settings(max_examples=100)
    def test_persistence_error_dialog_remains_open(self, error: ConfigPersistenceError):
        """For any ConfigPersistenceError, the dialog is NOT destroyed."""
        dialog, error_label, _ = _make_error_dialog(Err(error))

        dialog.destroy = MagicMock()
        dialog.grab_release = MagicMock()

        dialog._save()

        dialog.destroy.assert_not_called()
        dialog.grab_release.assert_not_called()

    @given(error=_persistence_error_st)
    @settings(max_examples=100)
    def test_persistence_error_preserves_field_values(self, error: ConfigPersistenceError):
        """For any ConfigPersistenceError, all field values remain unchanged
        after the save attempt."""
        dialog, error_label, values_before = _make_error_dialog(Err(error))

        dialog._save()

        for param_name, entry in dialog._entries.items():
            assert entry.get() == values_before[param_name], (
                f"Field '{param_name}' value changed from "
                f"'{values_before[param_name]}' to '{entry.get()}' after error"
            )
