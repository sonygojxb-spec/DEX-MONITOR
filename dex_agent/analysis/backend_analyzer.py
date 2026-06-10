"""Backend_Analyzer: wallet/transaction behavior analysis.

Design reference: "Backend_Analyzer". Maps to Requirements 3.1-3.9.

The analyzer, over a user-configured time window (``1..1440`` minutes, Req 3.1):

* counts the **distinct** wallets that transacted in the Trading_Pair (Req 3.1);
* classifies each transacting wallet as exactly one of
  :attr:`~dex_agent.models.WalletClassification.BOT` or
  :attr:`~dex_agent.models.WalletClassification.NON_BOT` (a total partition,
  Req 3.2) using behavioral heuristics over the swap stream;
* computes ``bot_pct = 100 * bot_txs / total_txs`` in ``[0, 100]`` (Req 3.3),
  recording ``bot_pct = 0`` and ``distinct_count = 0`` for an empty window
  (Req 3.4);
* computes the top-10 holder concentration in ``[0, 100]`` (Req 3.6) and raises a
  concentration-risk flag when the configured threshold is exceeded (Req 3.7);
* persists the :class:`~dex_agent.models.WalletAnalysis` with ``pair_id`` + a
  timestamp (Req 3.8);
* emits a bot-threshold alert through the injected alert sink when ``bot_pct``
  exceeds the configured threshold (Req 3.5; the real Notifier is wired in
  Task 17 - here we depend on a clean sink seam only); and
* on provider unavailability records an error result (a ``data_unavailable``
  analysis), retains prior results, produces no new classification/percentage,
  and returns an ``Err`` (Req 3.9).

It depends only on the :class:`~dex_agent.providers.interfaces.ChainDataProvider`
interface (so the swap/holder source is injectable / fakeable) plus the Task 1
``Result``/error types, the Task 2 models, and the Task 3
:class:`~dex_agent.repositories.interfaces.WalletAnalysisRepository`.

Bot/sniper heuristics
---------------------

There is no dedicated sniper API; bot detection derives from the Moralis Token
Swaps fields (``walletAddress`` / ``transactionType`` / ``bought`` / ``sold`` /
``blockTimestamp``, surfaced as :class:`~dex_agent.providers.interfaces.ChainTx`)
plus Streams pre/postTokenBalance deltas. A wallet is classified ``BOT`` when it
exhibits **any** of these automated-trading signals over its swaps in the window
(each threshold is injectable via :class:`BotHeuristics`):

* **high frequency** - the wallet made at least ``min_tx_count`` swaps in the
  window (sustained automated activity);
* **rapid-fire cadence** - two consecutive swaps occurred less than
  ``min_inter_tx_seconds`` apart (humanly implausible spacing);
* **rapid buy/sell flip** - a buy and a sell occurred within
  ``max_flip_seconds`` of one another (sniping / sandwich behavior).

A wallet matching none of these is ``NON_BOT``. The function is total, so every
transacting wallet receives exactly one classification (Req 3.2 / Property 6).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable, Mapping, Sequence

from dex_agent.models import (
    Configuration,
    HolderBalance,
    Severity,
    TradingPair,
    WalletAnalysis,
    WalletClassification,
    utc_now_seconds,
)
from dex_agent.providers.interfaces import Alert, ChainDataProvider, ChainTx, TxWindow
from dex_agent.repositories.interfaces import WalletAnalysisRepository
from dex_agent.result import Err, Ok, Result

# Configurable window bounds for Req 3.1 (1 minute .. 24 hours, inclusive).
WINDOW_MINUTES_MIN = 1
WINDOW_MINUTES_MAX = 1440

# A callable sink that delivers an :class:`Alert`. Task 17 wires the real
# Notifier behind this seam; tests inject a recording sink.
AlertSink = Callable[[Alert], None]


@dataclass(frozen=True)
class BotHeuristics:
    """Tunable thresholds for the bot-classification heuristics (Req 3.2).

    Attributes:
        min_tx_count: A wallet with at least this many swaps in the window is a
            ``BOT`` (sustained automated activity).
        min_inter_tx_seconds: Two consecutive swaps spaced strictly less than
            this many seconds apart classify the wallet as ``BOT``.
        max_flip_seconds: A buy and a sell within this many seconds of one
            another classify the wallet as ``BOT`` (rapid flip / sniping).
    """

    min_tx_count: int = 5
    min_inter_tx_seconds: float = 2.0
    max_flip_seconds: float = 5.0


DEFAULT_BOT_HEURISTICS = BotHeuristics()


class BackendAnalyzer:
    """Analyzes wallet/transaction behavior for a Trading_Pair (Req 3.1-3.9).

    Args:
        chain: The :class:`ChainDataProvider` supplying the swap stream and
            holder distribution.
        repository: Optional :class:`WalletAnalysisRepository` to persist each
            analysis (Req 3.8). When ``None`` results are not persisted.
        window_minutes: Default analysis window in minutes (``1..1440``,
            Req 3.1); may be overridden per call.
        bot_pct_threshold: Bot-transaction-percentage threshold in ``[0, 100]``;
            ``bot_pct`` strictly above it raises a bot alert (Req 3.5).
        holder_conc_threshold: Holder-concentration threshold in ``[0, 100]``;
            concentration strictly above it raises the risk flag (Req 3.7).
        heuristics: Tunable :class:`BotHeuristics` thresholds.
        alert_sink: Optional sink that receives the bot-threshold :class:`Alert`
            (Req 3.5). Task 17 wires the real Notifier here.
        clock: Callable returning the current second-precision UTC timestamp
            used to bound the window and stamp the analysis; injectable for tests.

    Raises:
        ValueError: If ``window_minutes`` is outside ``[1, 1440]`` (Req 3.1).
    """

    def __init__(
        self,
        chain: ChainDataProvider,
        repository: WalletAnalysisRepository | None = None,
        *,
        window_minutes: int = 60,
        bot_pct_threshold: Decimal = Decimal(50),
        holder_conc_threshold: Decimal = Decimal(50),
        heuristics: BotHeuristics = DEFAULT_BOT_HEURISTICS,
        alert_sink: AlertSink | None = None,
        clock: Callable[[], datetime] = utc_now_seconds,
    ) -> None:
        self._chain = chain
        self._repository = repository
        self._window_minutes = _validate_window(window_minutes)
        self._bot_pct_threshold = bot_pct_threshold
        self._holder_conc_threshold = holder_conc_threshold
        self._heuristics = heuristics
        self._alert_sink = alert_sink
        self._clock = clock

    @classmethod
    def from_configuration(
        cls,
        chain: ChainDataProvider,
        config: Configuration,
        *,
        window_minutes: int = 60,
        repository: WalletAnalysisRepository | None = None,
        heuristics: BotHeuristics = DEFAULT_BOT_HEURISTICS,
        alert_sink: AlertSink | None = None,
        clock: Callable[[], datetime] = utc_now_seconds,
    ) -> "BackendAnalyzer":
        """Build an analyzer with the bot/concentration thresholds from ``config``.

        The bot window is supplied separately because it is not a Configuration
        field; ``bot_pct_threshold`` and ``holder_conc_threshold`` are taken from
        the validated :class:`~dex_agent.models.Configuration` (Task 5).
        """
        return cls(
            chain,
            repository,
            window_minutes=window_minutes,
            bot_pct_threshold=config.bot_pct_threshold,
            holder_conc_threshold=config.holder_conc_threshold,
            heuristics=heuristics,
            alert_sink=alert_sink,
            clock=clock,
        )

    # ------------------------------------------------------------------
    # Classification heuristics (Req 3.2)
    # ------------------------------------------------------------------
    def classify_wallet(
        self, wallet_txs: Sequence[ChainTx]
    ) -> WalletClassification:
        """Classify a single wallet from its swaps in the window (Req 3.2).

        Returns exactly one of ``BOT`` / ``NON_BOT`` for any non-empty sequence,
        so the per-wallet classification is total (Property 6).
        """
        txs = sorted(wallet_txs, key=lambda t: t.block_time)
        h = self._heuristics

        # (1) high frequency.
        if len(txs) >= h.min_tx_count:
            return WalletClassification.BOT

        # (2) rapid-fire cadence (consecutive swaps too close together) and
        # (3) rapid buy/sell flip (opposite-side swaps within max_flip_seconds).
        last_seen_by_type: dict[str, datetime] = {}
        prev_time: datetime | None = None
        for tx in txs:
            if prev_time is not None:
                gap = (tx.block_time - prev_time).total_seconds()
                if gap < h.min_inter_tx_seconds:
                    return WalletClassification.BOT
            opposite = "sell" if tx.tx_type == "buy" else "buy"
            opp_time = last_seen_by_type.get(opposite)
            if opp_time is not None:
                flip_gap = (tx.block_time - opp_time).total_seconds()
                if flip_gap <= h.max_flip_seconds:
                    return WalletClassification.BOT
            last_seen_by_type[tx.tx_type] = tx.block_time
            prev_time = tx.block_time

        return WalletClassification.NON_BOT

    def classify_wallets(
        self, txs: Sequence[ChainTx]
    ) -> dict[str, WalletClassification]:
        """Classify every transacting wallet, returning one entry per wallet.

        The keys are exactly the distinct wallet addresses in ``txs`` and each
        value is exactly one :class:`WalletClassification` - the partition of
        Req 3.2 (Property 6).
        """
        by_wallet = _group_by_wallet(txs)
        return {
            wallet: self.classify_wallet(wallet_txs)
            for wallet, wallet_txs in by_wallet.items()
        }

    # ------------------------------------------------------------------
    # Pure metric helpers (Req 3.1, 3.3, 3.4, 3.6)
    # ------------------------------------------------------------------
    @staticmethod
    def distinct_wallets(txs: Sequence[ChainTx]) -> set[str]:
        """Return the set of distinct transacting wallet addresses (Req 3.1)."""
        return {tx.wallet_address for tx in txs}

    def bot_percentage(self, txs: Sequence[ChainTx]) -> Decimal:
        """Percentage of transactions attributable to bot wallets (Req 3.3/3.4).

        ``0`` for an empty window (Req 3.4); otherwise
        ``100 * bot_txs / total_txs`` in ``[0, 100]``.
        """
        total = len(txs)
        if total == 0:
            return Decimal(0)
        classifications = self.classify_wallets(txs)
        bot_txs = sum(
            1
            for tx in txs
            if classifications[tx.wallet_address] is WalletClassification.BOT
        )
        return Decimal(100) * Decimal(bot_txs) / Decimal(total)

    @staticmethod
    def holder_concentration(holders: Sequence[HolderBalance]) -> Decimal:
        """Top-10 holder concentration as a percentage in ``[0, 100]`` (Req 3.6).

        The denominator is the aggregated balance reported by the holder
        distribution (the observed circulating supply), so the result is bounded
        in ``[0, 100]`` by construction. Returns ``0`` when there is no positive
        supply.
        """
        balances = [h.balance for h in holders if h.balance > 0]
        total = sum(balances, Decimal(0))
        if total <= 0:
            return Decimal(0)
        top10 = sum(sorted(balances, reverse=True)[:10], Decimal(0))
        return Decimal(100) * top10 / total

    # ------------------------------------------------------------------
    # Analysis entry point (Req 3.1-3.9)
    # ------------------------------------------------------------------
    def analyze(
        self, pair: TradingPair, window_minutes: int | None = None
    ) -> Result[WalletAnalysis]:
        """Analyze ``pair`` over the configured window (Req 3.1-3.9).

        Returns ``Ok(WalletAnalysis)`` on success. On provider unavailability
        (the swap stream or holder distribution returns an error) it records an
        error result (a ``data_unavailable`` analysis), keeps prior results, and
        returns ``Err`` with the underlying provider error (Req 3.9).
        """
        window = self._window_minutes if window_minutes is None else _validate_window(
            window_minutes
        )
        now = self._clock()
        tx_window = TxWindow(start=now - timedelta(minutes=window), end=now)

        txs_result = self._chain.fetch_transactions(pair.token.address, tx_window)
        if txs_result.is_err():
            return self._record_unavailable(pair, window, now, txs_result.error)

        holders_result = self._chain.fetch_holder_distribution(pair.token.address)
        if holders_result.is_err():
            return self._record_unavailable(pair, window, now, holders_result.error)

        txs = txs_result.value
        holders = holders_result.value

        distinct_count = len(self.distinct_wallets(txs))  # Req 3.1 (0 when empty -> Req 3.4)
        bot_pct = self.bot_percentage(txs)  # Req 3.3/3.4 (in [0, 100])
        concentration = self.holder_concentration(holders)  # Req 3.6 (in [0, 100])
        conc_flag = concentration > self._holder_conc_threshold  # Req 3.7

        analysis = WalletAnalysis(
            pair_id=pair.id,
            window_minutes=window,
            distinct_wallet_count=distinct_count,
            bot_tx_percentage=bot_pct,
            holder_concentration_pct=concentration,
            concentration_risk_flag=conc_flag,
            data_unavailable=False,
            analyzed_at=now,
        )
        self._persist(analysis)

        if bot_pct > self._bot_pct_threshold:  # Req 3.5
            self._emit_bot_alert(pair, bot_pct)

        return Ok(analysis)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _record_unavailable(
        self,
        pair: TradingPair,
        window: int,
        now: datetime,
        error: object,
    ) -> Result[WalletAnalysis]:
        """Record a data-unavailable error result and return ``Err`` (Req 3.9).

        Prior analysis results are retained (the repository is append-only); the
        recorded marker carries ``data_unavailable = True`` with no new
        classification or percentage.
        """
        marker = WalletAnalysis(
            pair_id=pair.id,
            window_minutes=window,
            distinct_wallet_count=0,
            bot_tx_percentage=Decimal(0),
            holder_concentration_pct=Decimal(0),
            concentration_risk_flag=False,
            data_unavailable=True,
            analyzed_at=now,
        )
        self._persist(marker)
        return Err(error)

    def _persist(self, analysis: WalletAnalysis) -> WalletAnalysis:
        """Persist ``analysis`` when a repository is configured (Req 3.8)."""
        if self._repository is not None:
            self._repository.append(analysis)
        return analysis

    def _emit_bot_alert(self, pair: TradingPair, bot_pct: Decimal) -> None:
        """Deliver the bot-threshold alert through the sink seam (Req 3.5)."""
        if self._alert_sink is None:
            return
        alert = Alert(
            title="Bot activity threshold exceeded",
            body=(
                f"Bot transaction percentage {bot_pct} exceeds the configured "
                f"threshold {self._bot_pct_threshold} for pair {pair.id}."
            ),
            severity=Severity.HIGH,
            pair_id=pair.id,
        )
        self._alert_sink(alert)


def _validate_window(window_minutes: int) -> int:
    """Validate the window is within ``[1, 1440]`` minutes (Req 3.1)."""
    if not WINDOW_MINUTES_MIN <= window_minutes <= WINDOW_MINUTES_MAX:
        raise ValueError(
            "window_minutes must be between "
            f"{WINDOW_MINUTES_MIN} and {WINDOW_MINUTES_MAX} inclusive, "
            f"got {window_minutes}"
        )
    return window_minutes


def _group_by_wallet(txs: Sequence[ChainTx]) -> Mapping[str, list[ChainTx]]:
    """Group swaps by wallet address, preserving input order within a wallet."""
    by_wallet: dict[str, list[ChainTx]] = defaultdict(list)
    for tx in txs:
        by_wallet[tx.wallet_address].append(tx)
    return by_wallet


__all__ = [
    "BackendAnalyzer",
    "BotHeuristics",
    "DEFAULT_BOT_HEURISTICS",
    "AlertSink",
    "WINDOW_MINUTES_MIN",
    "WINDOW_MINUTES_MAX",
]
