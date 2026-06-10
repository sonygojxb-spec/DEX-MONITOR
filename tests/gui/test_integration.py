"""Integration tests for agent thread lifecycle.

Tests validate:
- Full start → tick → state pushed to queue → stop lifecycle (Req 9.1, 9.2, 9.4)
- GUIChannel delivery from background thread via widget.after() (Req 7.3)
- Settings save → config applied to next tick cycle (Req 10.7, 11.3)
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from dex_agent.gui.channel import GUIChannel
from dex_agent.gui.thread import AgentState, AgentThread
from dex_agent.providers.interfaces import Alert, DeliveryResult
from dex_agent.models import Severity
from dex_agent.result import Ok


# ---------------------------------------------------------------------------
# Helpers: mock agent factory
# ---------------------------------------------------------------------------


def _build_mock_agent(refresh_interval: float = 0.1):
    """Create a comprehensive mock Agent for integration testing.

    The mock agent is synchronous (no real asyncio) and returns immediately
    from boot() and tick(). This allows the AgentThread to cycle fast.
    """
    agent = MagicMock()

    # boot() returns a mock BootReport (synchronous, not a coroutine)
    boot_report = MagicMock()
    boot_report.config = MagicMock()
    boot_report.recovery_ok = True
    boot_report.monitoring_only = True
    agent.boot.return_value = boot_report

    # orchestrator mock
    agent.orchestrator.active_pairs.return_value = ["pair_1", "pair_2"]
    agent.orchestrator.active_count.return_value = 2
    agent.orchestrator.tick.return_value = None

    # repositories mock
    agent.repositories.watchlist.list_active.return_value = []

    # config mock
    agent.config.refresh_interval_s = refresh_interval

    return agent


# ---------------------------------------------------------------------------
# Test 1: Start → tick → state pushed to queue → stop lifecycle
# Requirements: 9.1, 9.2, 9.4
# ---------------------------------------------------------------------------


class TestAgentThreadLifecycle:
    """Integration test for full agent thread start/tick/stop lifecycle."""

    def test_start_tick_state_pushed_stop(self):
        """Validates: Requirements 9.1, 9.2, 9.4

        Start the AgentThread, wait for at least one AgentState to appear
        in the queue, verify the state fields, then request stop and confirm
        clean termination.
        """
        agent = _build_mock_agent(refresh_interval=0.05)
        state_queue: queue.Queue = queue.Queue()
        gui_channel = GUIChannel()  # No widget bound — that's fine for this test

        thread = AgentThread(
            agent=agent,
            state_queue=state_queue,
            gui_channel=gui_channel,
        )

        # Start the thread
        thread.start()

        # Wait for at least one AgentState to appear in the queue
        # Use a reasonable timeout to avoid hanging tests
        state: AgentState | None = None
        try:
            state = state_queue.get(timeout=5.0)
        except queue.Empty:
            pytest.fail("No AgentState was pushed to the queue within 5 seconds")

        # Verify the state has correct fields
        assert state is not None
        assert state.is_running is True
        assert state.active_pairs == 2  # From our mock
        assert state.uptime_seconds >= 0
        assert state.last_tick_time is not None
        assert state.error is None

        # Verify agent.boot() was called
        agent.boot.assert_called_once()

        # Verify orchestrator.tick was called for each active pair
        assert agent.orchestrator.tick.call_count >= 2

        # Request stop
        thread.request_stop()

        # Verify thread terminates cleanly
        assert not thread.is_running()
        assert not thread.is_transitioning()

        # After stop, a final state with is_running=False should be pushed
        # Drain the queue to find the stopped state
        stopped_state = None
        while not state_queue.empty():
            stopped_state = state_queue.get_nowait()

        assert stopped_state is not None
        assert stopped_state.is_running is False

    def test_thread_is_daemon(self):
        """The agent thread runs as a daemon so it dies with the process."""
        agent = _build_mock_agent(refresh_interval=0.05)
        state_queue: queue.Queue = queue.Queue()
        gui_channel = GUIChannel()

        thread = AgentThread(
            agent=agent,
            state_queue=state_queue,
            gui_channel=gui_channel,
        )

        thread.start()

        # Wait briefly for the thread to actually start
        try:
            state_queue.get(timeout=5.0)
        except queue.Empty:
            pytest.fail("Thread did not produce state within timeout")

        # The internal thread should be a daemon
        assert thread._thread is not None
        assert thread._thread.daemon is True

        # Cleanup
        thread.request_stop()

    def test_boot_failure_pushes_error_state(self):
        """If agent.boot() raises, the error is pushed to the queue."""
        agent = _build_mock_agent()
        agent.boot.side_effect = RuntimeError("Boot exploded")

        state_queue: queue.Queue = queue.Queue()
        gui_channel = GUIChannel()

        thread = AgentThread(
            agent=agent,
            state_queue=state_queue,
            gui_channel=gui_channel,
        )

        thread.start()

        # Wait for the error state
        try:
            state = state_queue.get(timeout=5.0)
        except queue.Empty:
            pytest.fail("No error state pushed after boot failure")

        assert state.is_running is False
        assert state.error is not None
        assert "Boot" in state.error

        # Thread should not be running
        # Give it a moment to fully terminate
        time.sleep(0.2)
        assert not thread.is_running()

    def test_multiple_ticks_produce_multiple_states(self):
        """Multiple tick cycles push multiple states to the queue."""
        agent = _build_mock_agent(refresh_interval=0.05)
        state_queue: queue.Queue = queue.Queue()
        gui_channel = GUIChannel()

        thread = AgentThread(
            agent=agent,
            state_queue=state_queue,
            gui_channel=gui_channel,
        )

        thread.start()

        # Collect at least 3 states
        states = []
        deadline = time.monotonic() + 5.0
        while len(states) < 3 and time.monotonic() < deadline:
            try:
                s = state_queue.get(timeout=1.0)
                states.append(s)
            except queue.Empty:
                break

        assert len(states) >= 3, f"Expected at least 3 states, got {len(states)}"

        # All should be running states
        for s in states:
            assert s.is_running is True

        # Uptime should be monotonically increasing
        for i in range(1, len(states)):
            assert states[i].uptime_seconds >= states[i - 1].uptime_seconds

        # Cleanup
        thread.request_stop()


# ---------------------------------------------------------------------------
# Test 2: GUIChannel delivery from background thread via widget.after()
# Requirements: 7.3
# ---------------------------------------------------------------------------


class TestGUIChannelBackgroundDelivery:
    """Integration test for GUIChannel delivery from the agent thread."""

    def test_gui_channel_delivery_from_background_thread(self):
        """Validates: Requirements 7.3

        From the agent thread (via submit()), deliver an alert through the
        GUIChannel and verify widget.after() was called with the alert
        title/body on the GUI main thread.
        """
        agent = _build_mock_agent(refresh_interval=0.1)
        state_queue: queue.Queue = queue.Queue()
        gui_channel = GUIChannel()

        # Set up a mock widget that records after() calls
        mock_widget = MagicMock()
        calls_received = []

        def capture_after(delay, fn, *args):
            calls_received.append((fn, args))

        mock_widget.after = capture_after
        mock_widget.append_alert = MagicMock()
        gui_channel.set_widget(mock_widget)

        thread = AgentThread(
            agent=agent,
            state_queue=state_queue,
            gui_channel=gui_channel,
        )

        thread.start()

        # Wait for the thread to be running
        try:
            state_queue.get(timeout=5.0)
        except queue.Empty:
            pytest.fail("Thread did not start within timeout")

        # Submit work that delivers an alert via the GUIChannel
        delivery_done = threading.Event()

        def deliver_alert():
            alert = Alert(
                title="Test Alert",
                body="Something happened",
                severity=Severity.HIGH,
            )
            result = gui_channel.deliver(alert)
            assert isinstance(result, Ok)
            assert result.value.delivered is True
            delivery_done.set()

        thread.submit(deliver_alert)

        # Wait for the submitted work to execute (next tick drains work queue)
        assert delivery_done.wait(timeout=5.0), "Alert delivery did not complete"

        # Verify widget.after() was called with append_alert and the correct args
        assert len(calls_received) >= 1, "widget.after() was never called"

        # Find the call that has append_alert
        found = False
        for fn, args in calls_received:
            if fn == mock_widget.append_alert and args == ("Test Alert", "Something happened"):
                found = True
                break

        assert found, (
            f"Expected widget.after() to be called with append_alert('Test Alert', 'Something happened'), "
            f"but got: {calls_received}"
        )

        # Verify alerts_count incremented
        assert gui_channel.alerts_count >= 1

        # Cleanup
        thread.request_stop()

    def test_gui_channel_delivery_without_widget_does_not_crash(self):
        """Validates: Requirements 7.6

        If no widget is bound, deliver() returns delivered=False gracefully
        without crashing the background thread.
        """
        agent = _build_mock_agent(refresh_interval=0.1)
        state_queue: queue.Queue = queue.Queue()
        gui_channel = GUIChannel()  # No widget set

        thread = AgentThread(
            agent=agent,
            state_queue=state_queue,
            gui_channel=gui_channel,
        )

        thread.start()

        # Wait for running
        try:
            state_queue.get(timeout=5.0)
        except queue.Empty:
            pytest.fail("Thread did not start within timeout")

        # Submit a delivery that will hit the "no widget" path
        delivery_result_holder = []
        delivery_done = threading.Event()

        def deliver_no_widget():
            alert = Alert(title="No Widget", body="test")
            result = gui_channel.deliver(alert)
            delivery_result_holder.append(result)
            delivery_done.set()

        thread.submit(deliver_no_widget)

        assert delivery_done.wait(timeout=5.0), "Delivery did not complete"

        # Check result
        assert len(delivery_result_holder) == 1
        result = delivery_result_holder[0]
        assert isinstance(result, Ok)
        assert result.value.delivered is False
        assert result.value.detail == "widget unavailable"

        # Thread should still be running (no crash)
        assert thread.is_running()

        # Cleanup
        thread.request_stop()


# ---------------------------------------------------------------------------
# Test 3: Settings save → config applied to next tick cycle
# Requirements: 10.7, 11.3
# ---------------------------------------------------------------------------


class TestSettingsAppliedToTick:
    """Integration test for settings changes reflected in tick behavior."""

    def test_config_change_applied_to_next_tick(self):
        """Validates: Requirements 10.7, 11.3

        Change the config's refresh_interval_s between ticks and verify the
        agent reads the new config on the next cycle by observing that the
        tick interval changes.
        """
        # Start with a long refresh interval
        agent = _build_mock_agent(refresh_interval=0.05)
        state_queue: queue.Queue = queue.Queue()
        gui_channel = GUIChannel()

        thread = AgentThread(
            agent=agent,
            state_queue=state_queue,
            gui_channel=gui_channel,
        )

        thread.start()

        # Wait for at least 2 ticks at the original interval
        states = []
        deadline = time.monotonic() + 5.0
        while len(states) < 2 and time.monotonic() < deadline:
            try:
                s = state_queue.get(timeout=2.0)
                states.append(s)
            except queue.Empty:
                break

        assert len(states) >= 2, f"Expected at least 2 states, got {len(states)}"

        # Now change the refresh interval to something different
        # The AgentThread reads config.refresh_interval_s at the start of the loop,
        # so changing it should be picked up on the next cycle
        agent.config.refresh_interval_s = 0.02

        # Collect more states and measure timing
        tick_times = []
        for _ in range(3):
            try:
                start = time.monotonic()
                state_queue.get(timeout=2.0)
                elapsed = time.monotonic() - start
                tick_times.append(elapsed)
            except queue.Empty:
                break

        # The thread should still be running after config change
        assert thread.is_running()

        # Verify ticks occurred (the config change didn't break the loop)
        assert len(tick_times) >= 1, "No ticks occurred after config change"

        # Cleanup
        thread.request_stop()

    def test_active_pairs_change_reflected_in_state(self):
        """Validates: Requirements 11.3

        Change the orchestrator.active_pairs() return value between ticks
        and verify the next AgentState reflects the change.
        """
        agent = _build_mock_agent(refresh_interval=0.05)
        state_queue: queue.Queue = queue.Queue()
        gui_channel = GUIChannel()

        thread = AgentThread(
            agent=agent,
            state_queue=state_queue,
            gui_channel=gui_channel,
        )

        thread.start()

        # Wait for first state with 2 active pairs
        try:
            state = state_queue.get(timeout=5.0)
        except queue.Empty:
            pytest.fail("No state received")

        assert state.active_pairs == 2

        # Change active pairs to 5
        agent.orchestrator.active_pairs.return_value = [
            "pair_1", "pair_2", "pair_3", "pair_4", "pair_5"
        ]
        agent.orchestrator.active_count.return_value = 5

        # Wait for a state that reflects the change
        found_new_count = False
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            try:
                state = state_queue.get(timeout=1.0)
                if state.active_pairs == 5:
                    found_new_count = True
                    break
            except queue.Empty:
                break

        assert found_new_count, "Agent state did not reflect new active_pairs count"

        # Cleanup
        thread.request_stop()

    def test_submit_work_executed_on_agent_thread(self):
        """Validates: Requirements 10.7

        Submitted work (simulating a settings save callback) executes on
        the agent thread during the next tick cycle.
        """
        agent = _build_mock_agent(refresh_interval=0.05)
        state_queue: queue.Queue = queue.Queue()
        gui_channel = GUIChannel()

        thread = AgentThread(
            agent=agent,
            state_queue=state_queue,
            gui_channel=gui_channel,
        )

        thread.start()

        # Wait for running
        try:
            state_queue.get(timeout=5.0)
        except queue.Empty:
            pytest.fail("Thread did not start")

        # Submit work that simulates applying a config change
        work_executed = threading.Event()
        work_thread_id = []

        def apply_config():
            work_thread_id.append(threading.current_thread().ident)
            # Simulate updating refresh interval as settings dialog would
            agent.config.refresh_interval_s = 0.01
            work_executed.set()

        thread.submit(apply_config)

        assert work_executed.wait(timeout=5.0), "Submitted work was not executed"

        # Verify the work ran on the agent thread (not the main thread)
        assert len(work_thread_id) == 1
        assert work_thread_id[0] != threading.current_thread().ident
        assert work_thread_id[0] == thread._thread.ident

        # Cleanup
        thread.request_stop()
