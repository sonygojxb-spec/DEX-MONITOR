"""Token input frame with mint address entry and Add/Remove buttons."""

from __future__ import annotations

from typing import Callable

import customtkinter


class TokenInputFrame(customtkinter.CTkFrame):
    """Mint address input + Add/Remove buttons.

    Provides a single-line text entry (1–44 characters for Solana mint address)
    with Add and Remove buttons. Add rejects empty/whitespace-only input.
    """

    def __init__(
        self,
        master: any,
        on_add: Callable[[str], None],
        on_remove: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)

        self._on_add = on_add
        self._on_remove = on_remove
        self._enabled = True

        # Entry field for mint address (single-line, max 44 chars)
        self._entry = customtkinter.CTkEntry(
            self,
            placeholder_text="Solana mint address",
            width=350,
        )
        self._entry.pack(side="left", padx=(10, 5), pady=10)

        # Register validation to limit input to 44 characters
        self._entry.bind("<KeyRelease>", self._enforce_max_length)

        # Add button
        self._add_button = customtkinter.CTkButton(
            self,
            text="Add",
            width=80,
            command=self._handle_add,
        )
        self._add_button.pack(side="left", padx=5, pady=10)

        # Remove button
        self._remove_button = customtkinter.CTkButton(
            self,
            text="Remove",
            width=80,
            command=self._handle_remove,
        )
        self._remove_button.pack(side="left", padx=5, pady=10)

    def _enforce_max_length(self, event=None) -> None:
        """Truncate entry text to 44 characters max."""
        current = self._entry.get()
        if len(current) > 44:
            self._entry.delete(44, "end")

    def _handle_add(self) -> None:
        """Handle Add button click. Reject empty/whitespace-only input."""
        if not self._enabled:
            return

        text = self._entry.get().strip()
        if not text:
            # No-op for empty or whitespace-only input
            return

        self._on_add(text)

    def _handle_remove(self) -> None:
        """Handle Remove button click."""
        if not self._enabled:
            return

        self._on_remove()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable both buttons.

        When disabled, button clicks produce no effect.
        """
        self._enabled = enabled
        state = "normal" if enabled else "disabled"
        self._add_button.configure(state=state)
        self._remove_button.configure(state=state)

    def clear_input(self) -> None:
        """Clear the entry field to an empty string."""
        self._entry.delete(0, "end")

    def get_input(self) -> str:
        """Return the current text in the entry field."""
        return self._entry.get()
