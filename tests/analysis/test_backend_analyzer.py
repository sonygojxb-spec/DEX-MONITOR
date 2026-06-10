"""Tests for the Backend_Analyzer (Task 8).

Covers the design's Correctness Properties for wallet/transaction analysis:

* Property 5 - distinct wallet count equals wallet-set cardinality
  (subtask 8.3, Req 3.1, 3.4);
* Property 6 - wallet classification partitions all transacting wallets
  (subtask 8.4, Req 3.2);
* Property 7 - bot transaction percentage is bounded and correct
  (subtask 8.5, Req 3.3, 3.4);
* Property 8 - holder concentration is bounded and flagged correctly
  (subtask 8.6, Req 3.6, 3.7);

plus unit tests for analysis-record persistence and the data-unavailable path
(subtask 8.7, Req 3.8, 3.9), the bot-threshold alert seam (Req 3.5), the
empty-window rule (Req 3.4), and window validation (Req 3.1).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.analysis import (
    DEFAULT_BOT_HEURISTICS,
    BackendAnalyzer,
    BotHeuristics,
)
from dex_agent.errors import ProviderError, TimedOut
from dex_agent.models import (
    HolderBalance,
    Network,
    Token,
    TradingPair,
    WalletClassification,
)
from dex_agent.providers.fakes import FakeChainDataProvider
from dex_agent.providers.interfaces import Alert, ChainTx
from dex_agent.repositories import InMemoryWalletAnalysisRepository

# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
WINDOW_MINUTES = 60
WINDOW_SECONDS = WINDOW_MINUTES * 60
WALLETS = [f"w{i}" for i in range(8)]


def make_pair() -> TradingPair:
    token = Token(
        address="MintAddr111",
        network=Network.SOLANA,
        symbol="TKN",
        name="Token",
        total_supply=Decimal(1_000_000),
    )
    return TradingPair(
        id="pair-1",
        token=token,
        quote_asset="SOL",
        dex="raydium",
        created_at=NOW - timedelta(days=1),
    )


def build_analyzer(
    txs: list[ChainTx],
    holders: list[HolderBalance] | None = None,
    *,
    window_minutes: int = WINDOW_MINUTES,
    bot_pct_threshold: Decimal = Decimal(50),
    holder_conc_threshold: Decimal = Decimal(50),
    heuristics: BotHeuristics = DEFAULT_BOT_HEURISTICS,
    alert_sink=None,
    repository: InMemoryWalletAnalysisRepository | None = None,
    chain: FakeChainDataProvider | None = None,
    now: datetime = NOW,
) -> tuple[BackendAnalyzer, TradingPair, FakeChainDataProvider]:
    pair = make_pair()
    chain = chain or FakeChainDataProvider()
    chain.set_transactions(pair.token.address, txs)
    chain.set_holders(pair.token.address, holders or [])
    analyzer = BackendAnalyzer(
        chain,
        repository,
        window_minutes=window_minutes,
        bot_pct_threshold=bot_pct_threshold,
        holder_conc_threshold=holder_conc_threshold,
        heuristics=heuristics,
        alert_sink=alert_sink,
        clock=lambda: now,
    )
    return analyzer, pair, chain


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


@st.composite
def chain_txs(draw: st.DrawFn) -> list[ChainTx]:
    """Generate a swap stream within the analysis window.

    Each swap has a wallet drawn from a small pool (so repeats and distinct
    counts vary), a buy/sell side, and a ``block_time`` inside
    ``[now - window, now]`` so the provider window filter retains it.
    """
    n = draw(st.integers(min_value=0, max_value=14))
    txs: list[ChainTx] = []
    for i in range(n):
        wallet = draw(st.sampled_from(WALLETS))
        tx_type = draw(st.sampled_from(["buy", "sell"]))
        offset = draw(st.integers(min_value=0, max_value=WINDOW_SECONDS - 1))
        amount = Decimal(draw(st.integers(min_value=0, max_value=1000)))
        txs.append(
            ChainTx(
                signature=f"sig-{i}",
                wallet_address=wallet,
                tx_type=tx_type,
                bought_amount=amount if tx_type == "buy" else None,
                sold_amount=amount if tx_type == "sell" else None,
                block_time=NOW - timedelta(seconds=offset),
            )
        )
    return txs


@st.composite
def holder_balances(draw: st.DrawFn) -> list[HolderBalance]:
    """Generate a holder distribution with non-negative balances."""
    n = draw(st.integers(min_value=0, max_value=20))
    return [
        HolderBalance(
            wallet=f"holder-{i}",
            balance=Decimal(draw(st.integers(min_value=0, max_value=1_000_000))),
        )
        for i in range(n)
    ]


PCT_THRESHOLDS = st.integers(min_value=0, max_value=100).map(Decimal)


# ---------------------------------------------------------------------------
# Property 5 (subtask 8.3): distinct wallet count == wallet-set cardinality
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(txs=chain_txs())
def test_property_5_distinct_count_equals_cardinality(txs: list[ChainTx]) -> None:
    # Feature: dex-trading-agent, Property 5: Distinct wallet count equals wallet-set cardinality
    # Validates: Requirements 3.1, 3.4
    analyzer, pair, _ = build_analyzer(txs)

    result = analyzer.analyze(pair)

    assert result.is_ok()
    analysis = result.value
    expected = len({tx.wallet_address for tx in txs})
    assert analysis.distinct_wallet_count == expected
    # Empty window -> distinct count is 0 (Req 3.4).
    if not txs:
        assert analysis.distinct_wallet_count == 0


# ---------------------------------------------------------------------------
# Property 6 (subtask 8.4): classification partitions all transacting wallets
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(txs=chain_txs())
def test_property_6_classification_partitions_wallets(txs: list[ChainTx]) -> None:
    # Feature: dex-trading-agent, Property 6: Wallet classification partitions all transacting wallets
    # Validates: Requirements 3.2
    analyzer, _, _ = build_analyzer(txs)

    classifications = analyzer.classify_wallets(txs)

    distinct = {tx.wallet_address for tx in txs}
    # Every transacting wallet receives exactly one classification (a key per
    # distinct wallet, no extras, each a member of the enum).
    assert set(classifications) == distinct
    assert all(
        c in (WalletClassification.BOT, WalletClassification.NON_BOT)
        for c in classifications.values()
    )
    bots = {w for w, c in classifications.items() if c is WalletClassification.BOT}
    non_bots = {
        w for w, c in classifications.items() if c is WalletClassification.NON_BOT
    }
    # The two classes partition the wallet set: disjoint and covering.
    assert bots.isdisjoint(non_bots)
    assert bots | non_bots == distinct


# ---------------------------------------------------------------------------
# Property 7 (subtask 8.5): bot transaction percentage is bounded and correct
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(txs=chain_txs())
def test_property_7_bot_percentage_bounded_and_correct(txs: list[ChainTx]) -> None:
    # Feature: dex-trading-agent, Property 7: Bot transaction percentage is bounded and correct
    # Validates: Requirements 3.3, 3.4
    analyzer, pair, _ = build_analyzer(txs)

    result = analyzer.analyze(pair)

    assert result.is_ok()
    bot_pct = result.value.bot_tx_percentage
    # Bounded in [0, 100] (Req 3.3).
    assert Decimal(0) <= bot_pct <= Decimal(100)

    total = len(txs)
    if total == 0:
        # Empty window -> 0 (Req 3.4).
        assert bot_pct == Decimal(0)
    else:
        classifications = analyzer.classify_wallets(txs)
        bot_txs = sum(
            1
            for tx in txs
            if classifications[tx.wallet_address] is WalletClassification.BOT
        )
        assert bot_pct == Decimal(100) * Decimal(bot_txs) / Decimal(total)


# ---------------------------------------------------------------------------
# Property 8 (subtask 8.6): holder concentration bounded and flagged correctly
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(holders=holder_balances(), threshold=PCT_THRESHOLDS)
def test_property_8_concentration_bounded_and_flagged(
    holders: list[HolderBalance], threshold: Decimal
) -> None:
    # Feature: dex-trading-agent, Property 8: Holder concentration is bounded and flagged correctly
    # Validates: Requirements 3.6, 3.7
    analyzer, pair, _ = build_analyzer(
        [], holders=holders, holder_conc_threshold=threshold
    )

    result = analyzer.analyze(pair)

    assert result.is_ok()
    analysis = result.value
    concentration = analysis.holder_concentration_pct
    # Bounded in [0, 100] (Req 3.6).
    assert Decimal(0) <= concentration <= Decimal(100)
    # Flag iff concentration strictly exceeds the threshold (Req 3.7).
    assert analysis.concentration_risk_flag == (concentration > threshold)


# ---------------------------------------------------------------------------
# Subtask 8.7: persistence (Req 3.8) and data-unavailable path (Req 3.9)
# ---------------------------------------------------------------------------


def test_analysis_is_persisted_with_pair_id_and_timestamp() -> None:
    """Req 3.8: the analysis is persisted with the pair id and a timestamp."""
    repo = InMemoryWalletAnalysisRepository()
    txs = [
        ChainTx(
            signature="s1",
            wallet_address="wA",
            tx_type="buy",
            bought_amount=Decimal(10),
            sold_amount=None,
            block_time=NOW - timedelta(seconds=30),
        )
    ]
    analyzer, pair, _ = build_analyzer(txs, repository=repo)

    result = analyzer.analyze(pair)

    assert result.is_ok()
    latest = repo.latest(pair.id)
    assert latest.is_ok()
    stored = latest.value
    assert stored == result.value
    assert stored.pair_id == pair.id
    assert stored.analyzed_at == NOW
    assert stored.data_unavailable is False


def test_empty_window_records_zero_percentage_and_count() -> None:
    """Req 3.4: an empty window yields bot_pct = 0 and distinct_count = 0."""
    analyzer, pair, _ = build_analyzer([])

    result = analyzer.analyze(pair)

    assert result.is_ok()
    assert result.value.bot_tx_percentage == Decimal(0)
    assert result.value.distinct_wallet_count == 0


def test_data_unavailable_on_transactions_records_marker_and_retains_prior() -> None:
    """Req 3.9: provider failure records an error result and retains prior results."""
    repo = InMemoryWalletAnalysisRepository()
    pair = make_pair()
    chain = FakeChainDataProvider()
    chain.set_holders(pair.token.address, [])

    # First, a successful analysis at t0 (the "prior" result to retain).
    chain.set_transactions(
        pair.token.address,
        [
            ChainTx(
                signature="s1",
                wallet_address="wA",
                tx_type="buy",
                bought_amount=Decimal(1),
                sold_amount=None,
                block_time=NOW - timedelta(seconds=10),
            )
        ],
    )
    good = BackendAnalyzer(chain, repo, clock=lambda: NOW - timedelta(seconds=120))
    prior = good.analyze(pair)
    assert prior.is_ok()

    # Now the swap source is unavailable.
    chain.fail_always("fetch_transactions", ProviderError("down", provider="fake"))
    analyzer = BackendAnalyzer(chain, repo, clock=lambda: NOW)
    result = analyzer.analyze(pair)

    # Err is returned to the caller (Req 3.9).
    assert result.is_err()
    assert isinstance(result.error, ProviderError)
    # An error result (data_unavailable marker) was recorded with no new
    # classification or percentage.
    latest = repo.latest(pair.id)
    assert latest.is_ok()
    assert latest.value.data_unavailable is True
    assert latest.value.distinct_wallet_count == 0
    assert latest.value.bot_tx_percentage == Decimal(0)
    # The prior result is retained in history (append-only).
    history = repo.history(pair.id)
    assert prior.value in history
    assert any(a.data_unavailable is False for a in history)


def test_data_unavailable_on_holders_records_marker() -> None:
    """Req 3.9: a holder-distribution failure also takes the unavailable path."""
    repo = InMemoryWalletAnalysisRepository()
    pair = make_pair()
    chain = FakeChainDataProvider()
    chain.set_transactions(pair.token.address, [])
    chain.fail_always(
        "fetch_holder_distribution", TimedOut("slow", timeout_s=30.0)
    )
    analyzer = BackendAnalyzer(chain, repo, clock=lambda: NOW)

    result = analyzer.analyze(pair)

    assert result.is_err()
    assert isinstance(result.error, TimedOut)
    assert repo.latest(pair.id).value.data_unavailable is True


# ---------------------------------------------------------------------------
# Bot-threshold alert seam (Req 3.5)
# ---------------------------------------------------------------------------


def test_bot_alert_emitted_when_threshold_exceeded() -> None:
    """Req 3.5: a bot_pct above the threshold emits an alert through the sink."""
    alerts: list[Alert] = []
    # Six swaps from one wallet -> high-frequency BOT -> bot_pct = 100.
    txs = [
        ChainTx(
            signature=f"s{i}",
            wallet_address="botwallet",
            tx_type="buy",
            bought_amount=Decimal(1),
            sold_amount=None,
            block_time=NOW - timedelta(seconds=10 * (i + 1)),
        )
        for i in range(6)
    ]
    analyzer, pair, _ = build_analyzer(
        txs, bot_pct_threshold=Decimal(50), alert_sink=alerts.append
    )

    result = analyzer.analyze(pair)

    assert result.is_ok()
    assert result.value.bot_tx_percentage == Decimal(100)
    assert len(alerts) == 1
    assert alerts[0].pair_id == pair.id
    assert "100" in alerts[0].body


def test_no_bot_alert_when_below_threshold() -> None:
    """No alert is emitted when bot_pct does not exceed the threshold."""
    alerts: list[Alert] = []
    # A single, slow, one-sided swap -> NON_BOT -> bot_pct = 0.
    txs = [
        ChainTx(
            signature="s1",
            wallet_address="human",
            tx_type="buy",
            bought_amount=Decimal(1),
            sold_amount=None,
            block_time=NOW - timedelta(seconds=30),
        )
    ]
    analyzer, pair, _ = build_analyzer(
        txs, bot_pct_threshold=Decimal(50), alert_sink=alerts.append
    )

    result = analyzer.analyze(pair)

    assert result.is_ok()
    assert result.value.bot_tx_percentage == Decimal(0)
    assert alerts == []


# ---------------------------------------------------------------------------
# Window validation (Req 3.1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_window", [0, -5, 1441, 5000])
def test_window_out_of_range_is_rejected(bad_window: int) -> None:
    """Req 3.1: the analysis window must be within [1, 1440] minutes."""
    chain = FakeChainDataProvider()
    with pytest.raises(ValueError):
        BackendAnalyzer(chain, window_minutes=bad_window)


@pytest.mark.parametrize("good_window", [1, 60, 1440])
def test_window_within_range_is_accepted(good_window: int) -> None:
    chain = FakeChainDataProvider()
    analyzer = BackendAnalyzer(chain, window_minutes=good_window)
    assert analyzer is not None
