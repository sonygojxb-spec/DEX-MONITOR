"""Unit tests for AlertsLogFrame.

Tests validate the core functionality of the alerts log frame:
- append_alert formatting
- append_message formatting
- MAX_ENTRIES capacity enforcement
- entry_count tracking
- read-only state
"""

from __future__ import annotations

import re
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Mock customtkinter before importing AlertsLogFrame
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_ctk(monkeypatch):
    """Mock customtkinter to avoid needing a display server."""
    mock_ctk_module = MagicMock()

    # Create a real-enough CTkFrame base class
    class FakeCTkFrame:
        def __init__(self, master=None, **kwargs):
            pass

    # Create a fake CTkTextbox that stores text in memory
    class FakeCTkTextbox:
        def __init__(self, master=None, **kwargs):
            self._state = kwargs.get("state", "normal")
            self._content = ""
            self._wrap = kwargs.get("wrap", "none")

        def configure(self, **kwargs):
            if "state" in kwargs:
                self._state = kwargs["state"]

        def pack(self, **kwargs):
            pass

        def insert(self, index, text):
            if index == "end":
                self._content += text
            else:
                self._content = text + self._content

        def delete(self, start, end):
            # Simulate deleting the first line
            if start == "1.0" and end == "2.0":
                lines = self._content.split("\n", 1)
                if len(lines) > 1:
                    self._content = lines[1]
                else:
                    self._content = ""

        def get(self, start, end):
            return self._content

        def see(self, index):
            pass

        def yview(self):
            return (0.0, 1.0)  # Default: at bottom

    mock_ctk_module.CTkFrame = FakeCTkFrame
    mock_ctk_module.CTkBaseClass = object
    mock_ctk_module.CTkTextbox = FakeCTkTextbox

    monkeypatch.setitem(
        __import__("sys").modules, "customtkinter", mock_ctk_module
    )

    # Need to reimport after mocking
    return mock_ctk_module


def _make_frame(mock_ctk):
    """Create an AlertsLogFrame with mocked customtkinter."""
    # Import after mocking
    import importlib
    import dex_agent.gui.frames.alerts_log as mod

    importlib.reload(mod)
    frame = mod.AlertsLogFrame(master=None)
    return frame


class TestAlertFormatting:
    """Tests for append_alert format."""

    def test_append_alert_format(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        frame.append_alert("TestTitle", "Test body message")

        content = frame._textbox._content
        # Check format: YYYY-MM-DD HH:MM:SS [TestTitle] Test body message
        pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[TestTitle\] Test body message\n"
        assert re.match(pattern, content), f"Content didn't match expected format: {content!r}"

    def test_append_alert_uses_current_timestamp(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        before = datetime.now()
        frame.append_alert("Alert", "body")
        after = datetime.now()

        content = frame._textbox._content
        timestamp_str = content[:19]  # YYYY-MM-DD HH:MM:SS
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        assert before.replace(microsecond=0) <= timestamp <= after.replace(microsecond=0) or \
            before.replace(microsecond=0) <= timestamp

    def test_append_alert_brackets_title(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        frame.append_alert("MyTitle", "my body")

        content = frame._textbox._content
        assert "[MyTitle]" in content


class TestMessageFormatting:
    """Tests for append_message format."""

    def test_append_message_format(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        frame.append_message("General log message")

        content = frame._textbox._content
        pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} General log message\n"
        assert re.match(pattern, content), f"Content didn't match: {content!r}"

    def test_append_message_no_brackets(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        frame.append_message("No brackets here")

        content = frame._textbox._content
        # Should not have square brackets (that's only for alerts)
        assert "[" not in content.split(" ", 2)[-1].split("]")[0] or \
            "[No brackets here]" not in content


class TestEntryCount:
    """Tests for entry_count tracking."""

    def test_initial_entry_count_is_zero(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        assert frame.entry_count == 0

    def test_entry_count_increments_on_alert(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        frame.append_alert("Title", "Body")
        assert frame.entry_count == 1

    def test_entry_count_increments_on_message(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        frame.append_message("msg")
        assert frame.entry_count == 1

    def test_entry_count_multiple(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        for i in range(5):
            frame.append_alert(f"Title{i}", f"Body{i}")
        assert frame.entry_count == 5


class TestCapacityManagement:
    """Tests for MAX_ENTRIES enforcement."""

    def test_max_entries_value(self, mock_ctk):
        import dex_agent.gui.frames.alerts_log as mod
        import importlib
        importlib.reload(mod)
        assert mod.AlertsLogFrame.MAX_ENTRIES == 10_000

    def test_entry_count_does_not_exceed_max(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        # Simulate being at capacity
        frame._entry_count = 10_000
        frame.append_alert("New", "entry")
        assert frame.entry_count == 10_000

    def test_oldest_removed_when_at_capacity(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        # Add a first entry manually
        frame._textbox._content = "2024-01-01 00:00:00 [Old] first entry\n"
        frame._entry_count = 10_000

        frame.append_alert("New", "entry")

        content = frame._textbox._content
        assert "Old" not in content
        assert "New" in content
        assert frame.entry_count == 10_000


class TestReadOnly:
    """Tests for read-only state."""

    def test_textbox_starts_disabled(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        assert frame._textbox._state == "disabled"

    def test_textbox_disabled_after_append(self, mock_ctk):
        frame = _make_frame(mock_ctk)
        frame.append_alert("Title", "Body")
        assert frame._textbox._state == "disabled"


# ---------------------------------------------------------------------------
# Property-Based Tests (Hypothesis)
# ---------------------------------------------------------------------------

import re as _re
import importlib as _importlib
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


# Feature: dex-gui, Property 9: Alert log entry formatting
class TestProperty9AlertLogEntryFormatting:
    """Property 9: For any Alert with arbitrary title and body strings,
    the appended log entry SHALL match the format
    YYYY-MM-DD HH:MM:SS [title] body.

    **Validates: Requirements 6.1**
    """

    @given(
        title=st.text(
            min_size=0,
            max_size=100,
            alphabet=st.characters(
                blacklist_categories=("Cs",),
                blacklist_characters="\n\r\x00",
            ),
        ),
        body=st.text(
            min_size=0,
            max_size=100,
            alphabet=st.characters(
                blacklist_categories=("Cs",),
                blacklist_characters="\n\r\x00",
            ),
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_alert_entry_matches_expected_format(self, mock_ctk, title, body):
        """Each appended alert must match: YYYY-MM-DD HH:MM:SS [title] body\\n"""
        import dex_agent.gui.frames.alerts_log as mod

        _importlib.reload(mod)
        frame = mod.AlertsLogFrame(master=None)

        frame.append_alert(title, body)

        content = frame._textbox._content

        # The entry must end with a newline
        assert content.endswith("\n"), (
            f"Expected trailing newline, got: {content!r}"
        )

        # Strip trailing newline for pattern matching on the line
        line = content[:-1]

        # Extract timestamp portion (first 19 chars)
        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        assert len(line) >= 19, f"Line too short: {line!r}"
        timestamp_str = line[:19]
        assert _re.fullmatch(timestamp_pattern, timestamp_str), (
            f"Timestamp does not match YYYY-MM-DD HH:MM:SS: {timestamp_str!r}"
        )

        # After timestamp there should be a space then [title] then space then body
        remainder = line[19:]
        expected_remainder = f" [{title}] {body}"
        assert remainder == expected_remainder, (
            f"Expected remainder {expected_remainder!r}, got {remainder!r}"
        )


# ---------------------------------------------------------------------------
# Property-Based Tests (Hypothesis)
# ---------------------------------------------------------------------------

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


# Feature: dex-gui, Property 10: Alerts log capacity management
class TestAlertsLogCapacityProperty:
    """Property-based test: alerts log never exceeds 10,000 entries and oldest removed first.

    **Validates: Requirements 6.4, 6.6**
    """

    @given(initial_count=st.integers(min_value=9990, max_value=10100))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_log_never_exceeds_max_entries(self, initial_count, mock_ctk):
        """For any initial count near capacity, after appending entries the log
        never exceeds MAX_ENTRIES (10,000)."""
        frame = _make_frame(mock_ctk)

        # Clamp initial_count to MAX_ENTRIES to simulate realistic pre-population
        clamped = min(initial_count, frame.MAX_ENTRIES)
        frame._entry_count = clamped

        # Pre-populate textbox content with that many lines
        frame._textbox._content = "".join(
            f"2024-01-01 00:00:00 [Entry] line {i}\n" for i in range(clamped)
        )

        # Now append additional entries to push past capacity
        extra_entries = 15
        for i in range(extra_entries):
            frame.append_alert("New", f"extra {i}")

        # Property: entry_count must never exceed MAX_ENTRIES
        assert frame.entry_count <= frame.MAX_ENTRIES

    @given(initial_count=st.integers(min_value=9990, max_value=10100))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_oldest_removed_first_when_at_capacity(self, initial_count, mock_ctk):
        """When the log is at capacity, appending a new entry removes the oldest
        (first line) and preserves the newest entries."""
        frame = _make_frame(mock_ctk)

        # Set frame to exactly at capacity
        frame._entry_count = frame.MAX_ENTRIES

        # Pre-populate with numbered lines so we can identify oldest vs newest
        frame._textbox._content = "".join(
            f"2024-01-01 00:00:00 [Entry] line {i}\n" for i in range(frame.MAX_ENTRIES)
        )

        # Determine how many entries to add (between 1 and initial_count - 9989)
        entries_to_add = max(1, initial_count - 9989)

        # Add new entries
        for i in range(entries_to_add):
            frame.append_alert("New", f"added {i}")

        content = frame._textbox._content

        # Property 1: count must be exactly MAX_ENTRIES (never exceeds)
        assert frame.entry_count == frame.MAX_ENTRIES

        # Property 2: oldest entries should have been removed
        # The first `entries_to_add` original lines should be gone
        for i in range(min(entries_to_add, frame.MAX_ENTRIES)):
            assert f"[Entry] line {i}\n" not in content

        # Property 3: newest entries must be preserved (at the end)
        last_added = f"added {entries_to_add - 1}"
        assert last_added in content

    @given(initial_count=st.integers(min_value=9990, max_value=10100))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_entry_count_stays_at_max_when_already_at_capacity(self, initial_count, mock_ctk):
        """When the log is already at capacity, adding more entries keeps
        entry_count pinned at MAX_ENTRIES."""
        frame = _make_frame(mock_ctk)

        # Set to capacity
        frame._entry_count = frame.MAX_ENTRIES
        frame._textbox._content = "2024-01-01 00:00:00 [Old] placeholder\n" * frame.MAX_ENTRIES

        # Clamp additions to a reasonable number for the test
        additions = min(initial_count, 10100) - 9989

        for i in range(additions):
            frame.append_message(f"message {i}")

        # entry_count must remain exactly MAX_ENTRIES
        assert frame.entry_count == frame.MAX_ENTRIES
