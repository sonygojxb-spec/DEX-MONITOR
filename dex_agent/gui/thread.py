"""Data models and background thread for the DEX Monitor GUI.

This module defines the immutable data-transfer objects used to communicate
state from the agent background thread to the Tkinter main thread, and the
:class:`AgentThread` class that runs the agent's asyncio tick loop in a
dedicated daemon thread.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from dex_agent.models import SignalType

if TYPE_CHECKING:
    from dex_agent.agent import Agent
    from dex_agent.gui.channel import GUIChannel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WatchlistRow:
    """One row of watchlist table data (immutable snapshot).

    Each field is pre-formatted as a display string. Fields that have no data
    available are represented as the literal string ``"-"``.
    """

    pair_id: str
    token_name: str
    severity: str
    bot_pct: str
    liquidity: str
    signal_type: str
    signal_score: str


@dataclass(frozen=True)
class AgentState:
    """Snapshot of agent state pushed to the GUI each tick (immutable).

    Produced by the AgentThread after each tick cycle and placed on the
    shared ``queue.Queue`` for the main thread to consume via polling.
    """

    active_pairs: int
    uptime_seconds: float
    last_tick_time: str | None
    alerts_count: int
    watchlist_rows: list[WatchlistRow]
    is_running: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_time(dt: datetime) -> str:
    """Format a datetime as HH:MM:SS."""
    return dt.strftime("%H:%M:%S")


async def _maybe_await(value):
    """Await the value if it's a coroutine; otherwise return it as-is."""
    if inspect.isawaitable(value):
        return await value
    return value


# ---------------------------------------------------------------------------
# AgentThread
# ---------------------------------------------------------------------------


class AgentThread:
    """Manages the background daemon thread running the agent tick loop.

    The thread runs ``asyncio.run()`` containing the agent's boot sequence
    followed by the per-pair tick loop (replicating the CLI behavior). State
    snapshots are pushed to a :class:`queue.Queue` after each tick cycle for
    the main thread to consume.

    The ``submit()`` method allows scheduling callable work (e.g. add_token,
    remove_pair) on the agent thread to avoid cross-thread mutation of agent
    internals.
    """

    _STOP_TIMEOUT_S: float = 60.0

    def __init__(
        self,
        agent: "Agent",
        state_queue: queue.Queue,
        gui_channel: "GUIChannel",
    ) -> None:
        self._agent = agent
        self._state_queue: queue.Queue = state_queue
        self._gui_channel: "GUIChannel" = gui_channel

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at: float | None = None
        self._transitioning: bool = False
        self._running: bool = False

        # Work queue for submit() — callables scheduled from the main thread.
        self._work_queue: queue.Queue[Callable] = queue.Queue()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the agent background thread.

        Sets the transitioning flag during boot, then clears it once the
        tick loop begins (or on error).
        """
        if self._running or self._transitioning:
            return

        self._stop_event.clear()
        self._transitioning = True
        self._thread = threading.Thread(
            target=self._run_in_thread,
            name="AgentThread",
            daemon=True,
        )
        self._thread.start()

    def request_stop(self) -> None:
        """Signal the agent thread to stop after the current tick cycle.

        Waits up to 60 seconds for graceful termination. If the thread does
        not stop within that window, it is abandoned (daemon thread will be
        killed on process exit) and the state transitions to stopped.
        """
        if not self._running and not self._transitioning:
            return

        self._transitioning = True
        self._stop_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=self._STOP_TIMEOUT_S)
            if self._thread.is_alive():
                # Force-termination fallback: daemon thread will die with process.
                logger.warning(
                    "AgentThread did not terminate within %.0fs; abandoning.",
                    self._STOP_TIMEOUT_S,
                )

        self._running = False
        self._transitioning = False
        self._push_state(is_running=False)

    def is_running(self) -> bool:
        """True while the tick loop is actively running."""
        return self._running

    def is_transitioning(self) -> bool:
        """True while the thread is booting or stopping."""
        return self._transitioning

    def submit(self, fn: Callable) -> None:
        """Schedule a callable to run on the agent thread.

        The callable will be executed at the start of the next tick cycle.
        This is used for operations like add_token/remove_pair that must
        run on the same thread as the agent to avoid data races.
        """
        self._work_queue.put(fn)

    # ------------------------------------------------------------------
    # Internal: thread entry point
    # ------------------------------------------------------------------

    def _run_in_thread(self) -> None:
        """Thread target: runs asyncio.run() with the agent loop."""
        try:
            asyncio.run(self._agent_loop())
        except Exception as exc:
            logger.exception("AgentThread crashed with unhandled exception")
            self._running = False
            self._transitioning = False
            self._push_state(is_running=False, error=str(exc))

    async def _agent_loop(self) -> None:
        """The async agent loop: boot → tick until stop signal."""
        try:
            # Boot phase
            await _maybe_await(self._agent.boot())
        except Exception as exc:
            # Boot failure: propagate error via state queue
            self._running = False
            self._transitioning = False
            self._push_state(is_running=False, error=f"Boot failed: {exc}")
            return

        # Boot succeeded — enter running state
        self._started_at = time.monotonic()
        self._running = True
        self._transitioning = False

        orchestrator = self._agent.orchestrator
        config = self._agent.config
        refresh_interval = config.refresh_interval_s

        try:
            while not self._stop_event.is_set():
                # Drain submitted work items
                self._drain_work_queue()

                # Tick every active pair
                try:
                    active = list(orchestrator.active_pairs())
                except Exception as exc:
                    logger.error("Could not list active pairs: %r", exc)
                    active = []

                for pair_id in active:
                    if self._stop_event.is_set():
                        break
                    try:
                        await _maybe_await(orchestrator.tick(pair_id))
                    except Exception as exc:
                        logger.error("Tick error for %s: %r", pair_id, exc)

                # Push state snapshot after each tick cycle
                self._push_state(is_running=True)

                # Sleep (check stop event periodically for responsiveness)
                self._interruptible_sleep(refresh_interval)

        except Exception as exc:
            # Unhandled exception in tick loop
            logger.exception("Unhandled exception in agent tick loop")
            self._running = False
            self._transitioning = False
            self._push_state(is_running=False, error=str(exc))
            return

        # Clean stop
        self._running = False
        self._transitioning = False

    # ------------------------------------------------------------------
    # Internal: state collection and pushing
    # ------------------------------------------------------------------

    def _push_state(
        self, *, is_running: bool, error: str | None = None
    ) -> None:
        """Collect current state from repositories and push to the queue."""
        try:
            uptime = 0.0
            if self._started_at is not None:
                uptime = time.monotonic() - self._started_at

            last_tick_time = _format_time(
                datetime.now(timezone.utc)
            ) if is_running else None

            watchlist_rows = self._collect_watchlist_rows()

            active_pairs = 0
            try:
                active_pairs = self._agent.orchestrator.active_count()
            except Exception:
                pass

            alerts_count = self._gui_channel.alerts_count

            state = AgentState(
                active_pairs=active_pairs,
                uptime_seconds=uptime,
                last_tick_time=last_tick_time,
                alerts_count=alerts_count,
                watchlist_rows=watchlist_rows,
                is_running=is_running,
                error=error,
            )
            self._state_queue.put_nowait(state)
        except Exception:
            # Never let state collection crash the thread
            logger.exception("Failed to push state to queue")

    def _collect_watchlist_rows(self) -> list[WatchlistRow]:
        """Build WatchlistRow snapshots from the current repository state."""
        rows: list[WatchlistRow] = []
        repos = self._agent.repositories

        try:
            entries = repos.watchlist.list_active()
        except Exception:
            return rows

        for entry in entries:
            pair_id = entry.pair_id

            # Token name via PairRepository
            token_name = "-"
            try:
                pair_result = repos.pairs.get(pair_id)
                if pair_result.is_ok():
                    name = pair_result.value.token.name
                    token_name = name if name else pair_result.value.token.symbol or pair_id[:12]
            except Exception:
                pass

            # Severity from SecurityEvalRepository
            severity = "-"
            try:
                # SecurityEvalRepository.latest takes token_address
                # Get token_address from the pair
                pair_result = repos.pairs.get(pair_id)
                if pair_result.is_ok():
                    token_address = pair_result.value.token.address
                    eval_result = repos.security_eval.latest(token_address)
                    if eval_result.is_ok():
                        severity = eval_result.value.rating.name
            except Exception:
                pass

            # Bot percentage from WalletAnalysisRepository
            bot_pct = "-"
            try:
                wa_result = repos.wallet_analysis.latest(pair_id)
                if wa_result.is_ok():
                    bot_pct = f"{wa_result.value.bot_tx_percentage:.1f}%"
            except Exception:
                pass

            # Liquidity from the latest PairSnapshot (available via the
            # ingestor's last_good cache or the metrics repository).
            liquidity = "-"
            try:
                ingestor = self._agent.data_ingestor
                last = ingestor.last_good(pair_id)
                if last is not None:
                    liquidity = f"${last.liquidity:,.0f}"
            except Exception:
                pass

            # Signal from SignalRepository (latest of either type)
            signal_type = "-"
            signal_score = "-"
            try:
                # Try ENTRY first, then EXIT; show whichever is more recent
                entry_result = repos.signals.latest(pair_id, SignalType.ENTRY)
                exit_result = repos.signals.latest(pair_id, SignalType.EXIT)

                latest_signal = None
                if entry_result.is_ok() and exit_result.is_ok():
                    # Pick the more recent one
                    if entry_result.value.generated_at >= exit_result.value.generated_at:
                        latest_signal = entry_result.value
                    else:
                        latest_signal = exit_result.value
                elif entry_result.is_ok():
                    latest_signal = entry_result.value
                elif exit_result.is_ok():
                    latest_signal = exit_result.value

                if latest_signal is not None:
                    signal_type = latest_signal.type.name
                    signal_score = f"{latest_signal.score:.2f}"
            except Exception:
                pass

            rows.append(
                WatchlistRow(
                    pair_id=pair_id,
                    token_name=token_name,
                    severity=severity,
                    bot_pct=bot_pct,
                    liquidity=liquidity,
                    signal_type=signal_type,
                    signal_score=signal_score,
                )
            )

        return rows

    # ------------------------------------------------------------------
    # Internal: work queue & sleep
    # ------------------------------------------------------------------

    def _drain_work_queue(self) -> None:
        """Execute all pending submitted callables."""
        while True:
            try:
                fn = self._work_queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception as exc:
                logger.error("Submitted work item raised: %r", exc)

    def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep for *seconds*, waking early if the stop event is set."""
        # Check every 0.5s so stop requests are handled promptly
        interval = 0.5
        remaining = seconds
        while remaining > 0 and not self._stop_event.is_set():
            time.sleep(min(interval, remaining))
            remaining -= interval
