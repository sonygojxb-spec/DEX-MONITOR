"""Watchlist table frame for the DEX Monitor GUI.

Displays a scrollable table of monitored tokens with columns for token name,
severity, bot percentage, liquidity, signal type, and signal score. Supports
single-row selection and retains stale data when updates fail.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter

if TYPE_CHECKING:
    from dex_agent.gui.thread import WatchlistRow


# Column definitions: (header_text, min_width)
_COLUMNS: list[tuple[str, int]] = [
    ("Token Name", 140),
    ("Severity", 90),
    ("Bot %", 70),
    ("Liquidity", 100),
    ("Signal Type", 100),
    ("Signal Score", 100),
]

_HEADER_BG = "#2B2B2B"
_ROW_BG = "#1E1E1E"
_ROW_SELECTED_BG = "#3A3A5A"
_HEADER_FG = "#CCCCCC"
_ROW_FG = "#DDDDDD"


class WatchlistTableFrame(customtkinter.CTkFrame):
    """Tabular display of monitored tokens.

    Uses a CTkScrollableFrame with a grid of CTkLabel widgets to render rows.
    Supports single-row selection (click to select/deselect) and preserves
    insertion order from the input list.
    """

    def __init__(self, master: any, **kwargs) -> None:
        super().__init__(master, **kwargs)

        # Internal state
        self._last_rows: list["WatchlistRow"] = []
        self._selected_index: int | None = None
        self._row_widgets: list[list[customtkinter.CTkLabel]] = []

        # Layout: header row (non-scrollable) + scrollable body
        self._build_header()
        self._scroll_frame = customtkinter.CTkScrollableFrame(
            self,
            fg_color=_ROW_BG,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Configure column weights in the scrollable frame
        for col_idx in range(len(_COLUMNS)):
            self._scroll_frame.columnconfigure(col_idx, weight=1, minsize=_COLUMNS[col_idx][1])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_rows(self, rows: list["WatchlistRow"]) -> None:
        """Refresh the table contents with the given rows.

        If *rows* is None or empty **and** we already have previously
        displayed data, the table retains the stale data (requirement 11.5).
        Rows are displayed in the same order as the input list (insertion
        order preservation per requirement 4.7).
        """
        # Staleness: retain old data if no new rows provided
        if not rows and self._last_rows:
            return

        if rows:
            self._last_rows = list(rows)

        self._selected_index = None
        self._rebuild_table()

    def get_selected_pair_id(self) -> str | None:
        """Return the pair_id of the currently selected row, or None."""
        if self._selected_index is None:
            return None
        if self._selected_index >= len(self._last_rows):
            return None
        return self._last_rows[self._selected_index].pair_id

    # ------------------------------------------------------------------
    # Internal: header
    # ------------------------------------------------------------------

    def _build_header(self) -> None:
        """Create the fixed header row."""
        header_frame = customtkinter.CTkFrame(self, fg_color=_HEADER_BG, height=30)
        header_frame.pack(fill="x", padx=0, pady=(0, 1))

        for col_idx, (text, min_w) in enumerate(_COLUMNS):
            header_frame.columnconfigure(col_idx, weight=1, minsize=min_w)
            lbl = customtkinter.CTkLabel(
                header_frame,
                text=text,
                text_color=_HEADER_FG,
                font=customtkinter.CTkFont(weight="bold", size=12),
                anchor="w",
                padx=8,
            )
            lbl.grid(row=0, column=col_idx, sticky="ew", padx=1, pady=2)

        # Prevent the header frame from shrinking
        header_frame.grid_propagate(False)
        header_frame.pack_propagate(False)

    # ------------------------------------------------------------------
    # Internal: table rebuild
    # ------------------------------------------------------------------

    def _rebuild_table(self) -> None:
        """Clear and rebuild all row widgets from _last_rows."""
        # Destroy existing row widgets
        for row_labels in self._row_widgets:
            for lbl in row_labels:
                lbl.destroy()
        self._row_widgets.clear()

        # Create new rows
        for row_idx, row in enumerate(self._last_rows):
            row_labels = self._create_row(row_idx, row)
            self._row_widgets.append(row_labels)

    def _create_row(self, row_idx: int, row: "WatchlistRow") -> list[customtkinter.CTkLabel]:
        """Create a single table row as a list of CTkLabel widgets."""
        fields = [
            self._display_value(row.token_name),
            self._display_value(row.severity),
            self._display_value(row.bot_pct),
            self._display_value(row.liquidity),
            self._display_value(row.signal_type),
            self._display_value(row.signal_score),
        ]

        labels: list[customtkinter.CTkLabel] = []
        for col_idx, text in enumerate(fields):
            lbl = customtkinter.CTkLabel(
                self._scroll_frame,
                text=text,
                text_color=_ROW_FG,
                font=customtkinter.CTkFont(size=12),
                anchor="w",
                padx=8,
            )
            lbl.grid(row=row_idx, column=col_idx, sticky="ew", padx=1, pady=1)
            # Bind click for row selection
            lbl.bind("<Button-1>", lambda event, idx=row_idx: self._on_row_click(idx))
            labels.append(lbl)

        return labels

    # ------------------------------------------------------------------
    # Internal: selection
    # ------------------------------------------------------------------

    def _on_row_click(self, row_idx: int) -> None:
        """Handle a click on a row — toggle selection."""
        if self._selected_index == row_idx:
            # Deselect
            self._selected_index = None
        else:
            self._selected_index = row_idx

        self._refresh_highlight()

    def _refresh_highlight(self) -> None:
        """Update visual highlighting of all rows based on selection state."""
        for idx, row_labels in enumerate(self._row_widgets):
            bg = _ROW_SELECTED_BG if idx == self._selected_index else _ROW_BG
            for lbl in row_labels:
                lbl.configure(fg_color=bg)

    # ------------------------------------------------------------------
    # Internal: display formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _display_value(value: str | None) -> str:
        """Return the display string for a cell value.

        Displays '-' for None or unavailable fields. The WatchlistRow
        dataclass already formats unavailable values as '-', but this
        provides a safety net for any None that may slip through.
        """
        if value is None:
            return "-"
        return value
