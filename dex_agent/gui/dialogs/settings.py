"""Settings dialog: modal editor for agent configuration parameters.

Design reference: "SettingsDialog" (Requirements 10.1-10.8). Displays labeled
input fields for each parameter in ``ConfigManager.PARAM_RANGES``, pre-populated
from the active configuration or documented DEFAULTS. Save coerces values to the
correct numeric type and calls ``config_manager.save(inputs)``; errors are shown
inline without closing the dialog.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import customtkinter

from dex_agent.config import (
    ConfigManager,
    ConfigPersistenceError,
    ConfigValidationError,
    DEFAULTS,
    PARAM_RANGES,
)


class SettingsDialog(customtkinter.CTkToplevel):
    """Modal dialog for editing agent configuration parameters."""

    def __init__(self, master, config_manager: ConfigManager) -> None:
        super().__init__(master)
        self._config_manager = config_manager
        self._entries: dict[str, customtkinter.CTkEntry] = {}

        # Window setup
        self.title("Settings")
        self.geometry("500x650")
        self.resizable(False, False)

        # Make modal: block interaction with parent window
        self.transient(master)
        self.grab_set()

        # Determine pre-population source
        active = config_manager.active
        defaults = DEFAULTS

        # Scrollable container for the parameter fields
        self._scroll_frame = customtkinter.CTkScrollableFrame(self, width=460, height=480)
        self._scroll_frame.pack(padx=10, pady=(10, 5), fill="both", expand=True)

        # Generate labeled input fields for each parameter in PARAM_RANGES
        for param_name, param_range in PARAM_RANGES.items():
            row_frame = customtkinter.CTkFrame(self._scroll_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=5, pady=3)

            # Label with parameter name and allowed range
            range_hint = f"[{param_range.low}, {param_range.high}]"
            label_text = f"{param_name} {range_hint}"
            label = customtkinter.CTkLabel(row_frame, text=label_text, anchor="w")
            label.pack(side="left", padx=(0, 10))

            # Entry field
            entry = customtkinter.CTkEntry(row_frame, width=120)
            entry.pack(side="right")

            # Pre-populate from active config or DEFAULTS
            if active is not None and hasattr(active, param_name):
                value = getattr(active, param_name)
            else:
                value = defaults.get(param_name, "")

            entry.insert(0, str(value))
            self._entries[param_name] = entry

        # Error message label (shown at the bottom)
        self._error_label = customtkinter.CTkLabel(
            self, text="", text_color="red", wraplength=460, anchor="w"
        )
        self._error_label.pack(padx=10, pady=(0, 5), fill="x")

        # Button row
        button_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        button_frame.pack(padx=10, pady=(0, 10), fill="x")

        cancel_btn = customtkinter.CTkButton(
            button_frame, text="Cancel", command=self._cancel
        )
        cancel_btn.pack(side="right", padx=(5, 0))

        save_btn = customtkinter.CTkButton(
            button_frame, text="Save", command=self._save
        )
        save_btn.pack(side="right")

    def _save(self) -> None:
        """Read field values, coerce types, call config_manager.save()."""
        self._error_label.configure(text="")

        inputs: dict[str, object] = {}
        for param_name, entry in self._entries.items():
            raw_value = entry.get().strip()
            param_range = PARAM_RANGES[param_name]

            try:
                if param_range.integer:
                    inputs[param_name] = int(raw_value)
                else:
                    inputs[param_name] = Decimal(raw_value)
            except (ValueError, InvalidOperation):
                # Show a type coercion error immediately
                self._error_label.configure(
                    text=f"'{param_name}' must be a valid "
                    f"{'integer' if param_range.integer else 'decimal'} number."
                )
                return

        result = self._config_manager.save(inputs)

        if result.is_ok():
            # Success: close the dialog
            self.grab_release()
            self.destroy()
        else:
            # Display error message; keep dialog open with values preserved
            error = result.error
            if isinstance(error, (ConfigValidationError, ConfigPersistenceError)):
                self._error_label.configure(text=error.message)
            else:
                self._error_label.configure(text=str(error))

    def _cancel(self) -> None:
        """Close dialog without saving."""
        self.grab_release()
        self.destroy()
