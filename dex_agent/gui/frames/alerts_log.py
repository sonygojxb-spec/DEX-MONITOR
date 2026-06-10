"""Scrollable read-only text area for timestamped alert messages."""

from __future__ import annotations

from datetime import datetime

import customtkinter


class AlertsLogFrame(customtkinter.CTkFrame):
    """Scrollable read-only text area for timestamped alert messages.

    Displays alerts in the format: YYYY-MM-DD HH:MM:SS [title] body
    Auto-scrolls to bottom unless user has scrolled up.
    Enforces a maximum of 10,000 entries, removing oldest when exceeded.
    """

    MAX_ENTRIES: int = 10_000

    def __init__(self, master: customtkinter.CTkBaseClass, **kwargs) -> None:
        super().__init__(master, **kwargs)

        self._entry_count: int = 0

        # Create scrollable read-only textbox
        self._textbox = customtkinter.CTkTextbox(self, state="disabled", wrap="word")
        self._textbox.pack(fill="both", expand=True, padx=5, pady=5)

    @property
    def entry_count(self) -> int:
        """Return the current number of entries in the log."""
        return self._entry_count

    def append_alert(self, title: str, body: str) -> None:
        """Append a formatted alert entry: YYYY-MM-DD HH:MM:SS [title] body."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} [{title}] {body}\n"
        self._append_line(line)

    def append_message(self, message: str) -> None:
        """Append a general timestamped message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} {message}\n"
        self._append_line(line)

    def _append_line(self, line: str) -> None:
        """Internal method to append a line with auto-scroll and capacity management."""
        # Check if user is at the bottom before inserting
        should_scroll = self._is_at_bottom()

        # Enable editing temporarily
        self._textbox.configure(state="normal")

        # If at capacity, remove the oldest entry (first line)
        if self._entry_count >= self.MAX_ENTRIES:
            self._textbox.delete("1.0", "2.0")
        else:
            self._entry_count += 1

        # Insert new line at the end
        self._textbox.insert("end", line)

        # Disable editing again
        self._textbox.configure(state="disabled")

        # Auto-scroll to bottom if user was at the bottom
        if should_scroll:
            self._textbox.see("end")

    def _is_at_bottom(self) -> bool:
        """Check if the textbox view is scrolled to the bottom."""
        try:
            yview = self._textbox.yview()
            # yview() returns (top, bottom) fractions.
            # If bottom is at or very near 1.0, user is at the bottom.
            return yview[1] >= 0.99
        except Exception:
            # If anything goes wrong (e.g., widget not yet rendered), default to auto-scroll
            return True
