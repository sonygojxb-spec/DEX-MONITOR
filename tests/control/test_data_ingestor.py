"""Tests for the Data_Ingestor (Tasks 18.1, 18.4, 18.5, 18.6).

Covers:

* **Property 10** - discovery adds only recent, matching pairs (Req 1.5, 1.6).
* **Property 11** - fetch failures retain last-good data and bound retries
  (Req 1.8, 1.9).
* Unit tests - pair-not-found rejection (Req 1.2) and remove-retains-data via
  the Orchestrator (Req 1.3, 1.4), plus the Req 1.1 security-eval trigger.

All provider access is through in-memory fakes and a controllable clock; there
are no real network/chain calls or sleeps.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.control import DataIngestor, MonitoringOrchestrator
from dex_agent.control.data_ingestor import MAX_CONSECUTIVE_FAILURES
from dex_agent.errors import NotFound, ProviderError
from dex_agent.models import (
    Configuration,
    Network,
    PairSnapshot,
    Token,
    WatchlistSource,
    make_trading_pair,
)
from dex_agent.providers.fakes import FakeMarketDataProvider
from dex_agent.providers.interfaces import Alert, DiscoveryFilters
from dex_agent.repositories import (
    InMemoryPairRepository,
    InMemoryWatchlistRepository,
)
from dex_agent.result import Err, Ok

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def fixed_clock(now: datetime = NOW):
    return lambda: now


def make_config() -> Configuration:
    return Configuration(
        discovery_scan_interval_s=60,
        measurement_period_s=300,
        bot_pct_threshold=Decimal(50),
        holder_conc_threshold=Decimal(50),
        rugpull_threshold=Decimal(50),
        dump_threshold=Decimal(2),
        entry_threshold=Decimal(50),
        slippage_tolerance=Decimal(1),
    )


def make_token(address: str) -> Token:
    return Token(
        address=address,
        network=Network.SOLANA,
        symbol="TKN",
        name="Token",
        total_supply=Decimal(1_000_000),
    )


def make_snapshot(
    pair_id: str,
    *,
    liquidity: Decimal = Decimal(1000),
    fetched_at: datetime = NOW,
) -> PairSnapshot:
    return PairSnapshot(
        pair_id=pair_id,
        price=Decimal("1.5"),
        liquidity=liquidity,
        market_cap=Decimal(50_000),
        fdv=Decimal(60_000),
        buy_count=10,
        sell_count=5,
        buy_volume=Decimal(2000),
        sell_volume=Decimal(1000),
        fetched_at=fetched_at,
    )


# ---------------------------------------------------------------------------
# Property 11: Fetch failures retain last-good data and bound retries
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(n_failures=st.integers(min_value=1, max_value=12))
def test_property_11_fetch_failures_retain_last_good_and_bound_retries(n_failures):
    # Feature: dex-trading-agent, Property 11: Fetch failures retain last-good data and bound retries
    # Validates: Requirements 1.8, 1.9
    market = FakeMarketDataProvider()
    stale_alerts: list[Alert] = []
    ingestor = DataIngestor(
        market,
        InMemoryWatchlistRepository(),
        InMemoryPairRepository(),
        stale_sink=stale_alerts.append,
        clock=fixed_clock(),
    )

    pair_id = "pair-A"
    good = make_snapshot(pair_id, liquidity=Decimal(4242))
    market.set_snapshot(good)

    # Seed a last-good snapshot via one successful refresh.
    seeded = ingestor.refresh(pair_id)
    assert isinstance(seeded, Ok)
    assert ingestor.failure_count(pair_id) == 0

    # Now every fetch fails for the rest of the sequence.
    market.fail_always(
        "fetch_pair_snapshot", ProviderError("provider down", provider="fake")
    )

    for k in range(1, n_failures + 1):
        result = ingestor.refresh(pair_id)
        # The served snapshot remains the last successfully retrieved snapshot.
        assert isinstance(result, Ok)
        served = result.value
        assert served.is_stale is True
        assert served.price == good.price
        assert served.liquidity == good.liquidity
        assert served.market_cap == good.market_cap
        # The consecutive failure count increments by one per failure, capped at 5.
        assert ingestor.failure_count(pair_id) == min(k, MAX_CONSECUTIVE_FAILURES)

    # A single stale-data notification is emitted iff >= 5 consecutive failures.
    expected_alerts = 1 if n_failures >= MAX_CONSECUTIVE_FAILURES else 0
    assert len(stale_alerts) == expected_alerts
    if expected_alerts:
        assert stale_alerts[0].pair_id == pair_id


def test_success_after_failures_resets_count_and_clears_stale():
    market = FakeMarketDataProvider()
    stale_alerts: list[Alert] = []
    ingestor = DataIngestor(
        market,
        InMemoryWatchlistRepository(),
        InMemoryPairRepository(),
        stale_sink=stale_alerts.append,
        clock=fixed_clock(),
    )
    pair_id = "pair-B"
    market.set_snapshot(make_snapshot(pair_id))
    ingestor.refresh(pair_id)

    market.fail_always("fetch_pair_snapshot", ProviderError("down"))
    for _ in range(5):
        ingestor.refresh(pair_id)
    assert ingestor.failure_count(pair_id) == 5
    assert len(stale_alerts) == 1

    # Recovery resets the failure count and re-arms the stale notification.
    market.clear_failures("fetch_pair_snapshot")
    result = ingestor.refresh(pair_id)
    assert isinstance(result, Ok)
    assert result.value.is_stale is False
    assert ingestor.failure_count(pair_id) == 0


def test_failure_without_last_good_returns_error():
    market = FakeMarketDataProvider()
    ingestor = DataIngestor(
        market,
        InMemoryWatchlistRepository(),
        InMemoryPairRepository(),
        clock=fixed_clock(),
    )
    market.fail_always("fetch_pair_snapshot", ProviderError("down"))
    result = ingestor.refresh("never-good")
    assert isinstance(result, Err)
    assert ingestor.failure_count("never-good") == 1


# ---------------------------------------------------------------------------
# Property 10: Discovery adds only recent, matching pairs
# ---------------------------------------------------------------------------

_candidate = st.fixed_dictionaries(
    {
        "idx": st.integers(min_value=0, max_value=40),
        "age_hours": st.integers(min_value=0, max_value=48),
        "quote_asset": st.sampled_from(["SOL", "USDC"]),
        "liquidity": st.integers(min_value=0, max_value=5000),
    }
)


@settings(max_examples=100)
@given(
    candidates=st.lists(_candidate, max_size=25, unique_by=lambda c: c["idx"]),
    min_liquidity=st.integers(min_value=0, max_value=5000),
    quote_filter=st.sampled_from([("SOL",), ("USDC",), ("SOL", "USDC")]),
)
def test_property_10_discovery_adds_only_recent_matching_pairs(
    candidates, min_liquidity, quote_filter
):
    # Feature: dex-trading-agent, Property 10: Discovery adds only recent, matching pairs
    # Validates: Requirements 1.5, 1.6
    market = FakeMarketDataProvider()
    pair_repo = InMemoryPairRepository()
    watchlist = InMemoryWatchlistRepository()
    ingestor = DataIngestor(
        market,
        watchlist,
        pair_repo,
        discovery_window=timedelta(hours=24),
        clock=fixed_clock(),
    )

    snapshots = []
    expected_added: set[str] = set()
    quote_assets = frozenset(quote_filter)
    min_liq = Decimal(min_liquidity)

    for c in candidates:
        pair_id = f"pair-{c['idx']}"
        created_at = NOW - timedelta(hours=c["age_hours"])
        liquidity = Decimal(c["liquidity"])
        pair = make_trading_pair(
            id=pair_id,
            token=make_token(f"tok-{c['idx']}"),
            quote_asset=c["quote_asset"],
            dex="raydium",
            created_at=created_at,
        ).value
        pair_repo.add(pair)
        # fetched_at = NOW so the provider returns every candidate; the ingestor
        # owns the 24h recency check against the resolved created_at.
        snapshots.append(make_snapshot(pair_id, liquidity=liquidity, fetched_at=NOW))

        recent = created_at >= NOW - timedelta(hours=24)
        matches = c["quote_asset"] in quote_assets and liquidity >= min_liq
        if recent and matches:
            expected_added.add(pair_id)

    market.set_discoveries(snapshots)
    filters = DiscoveryFilters(
        exchange="pumpfun",
        quote_assets=quote_assets,
        max_age=timedelta(hours=24),
        min_liquidity=min_liq,
    )

    result = ingestor.discovery_scan(filters)
    assert isinstance(result, Ok)
    outcome = result.value

    # The set added to the Watchlist equals exactly the recent + matching ones.
    assert set(outcome.added) == expected_added
    active_pairs = {e.pair_id for e in watchlist.list_active()}
    assert active_pairs == expected_added
    # Discovery-added entries carry AUTO_DISCOVERY provenance.
    for entry in watchlist.list_active():
        assert entry.source is WatchlistSource.AUTO_DISCOVERY


# ---------------------------------------------------------------------------
# Unit tests (Task 18.6): pair-not-found rejection, remove-retains-data
# ---------------------------------------------------------------------------


def test_add_token_pair_not_found_rejects_identifying_token():
    # Req 1.2: an unresolvable token is rejected with an error naming the token.
    market = FakeMarketDataProvider()  # no pairs scripted -> resolve fails
    ingestor = DataIngestor(
        market,
        InMemoryWatchlistRepository(),
        InMemoryPairRepository(),
        clock=fixed_clock(),
    )
    result = ingestor.add_token_to_watchlist("unknown-token", Network.SOLANA)
    assert isinstance(result, Err)
    assert isinstance(result.error, NotFound)
    assert result.error.identifier == "unknown-token"


def test_add_token_triggers_security_eval_and_begins_monitoring():
    # Req 1.1: resolve, trigger security evaluation, begin monitoring.
    market = FakeMarketDataProvider()
    market.set_pairs("tok-1", [make_snapshot("pair-1")])

    evaluated: list[str] = []

    class RecordingInspector:
        def evaluate(self, token):
            evaluated.append(token.address)
            return None

    watchlist = InMemoryWatchlistRepository()
    config = make_config()
    orch = MonitoringOrchestrator(config=config, watchlist_repo=watchlist)
    ingestor = DataIngestor(
        market,
        watchlist,
        InMemoryPairRepository(),
        security_inspector=RecordingInspector(),
        admit=orch.add_pair,
        clock=fixed_clock(),
    )

    result = ingestor.add_token_to_watchlist("tok-1", Network.SOLANA)
    assert isinstance(result, Ok)
    assert evaluated == ["tok-1"]
    assert orch.is_active("pair-1") is True
    assert watchlist.get("pair-1").value.source is WatchlistSource.MANUAL


def test_remove_pair_stops_monitoring_but_retains_data():
    # Req 1.3/1.4: removal stops the loop while repositories retain the data.
    market = FakeMarketDataProvider()
    market.set_pairs("tok-1", [make_snapshot("pair-1")])
    watchlist = InMemoryWatchlistRepository()
    config = make_config()
    orch = MonitoringOrchestrator(config=config, watchlist_repo=watchlist)
    ingestor = DataIngestor(
        market, watchlist, InMemoryPairRepository(), admit=orch.add_pair,
        clock=fixed_clock(),
    )
    ingestor.add_token_to_watchlist("tok-1", Network.SOLANA)
    assert orch.is_active("pair-1") is True

    orch.remove_pair("pair-1")

    # Monitoring stopped (Req 1.3).
    assert orch.is_active("pair-1") is False
    assert orch.active_count() == 0
    # Data retained: the watchlist entry still exists (deactivated, not deleted).
    entry = watchlist.get("pair-1")
    assert isinstance(entry, Ok)
    assert entry.value.active is False
    assert "pair-1" in {e.pair_id for e in watchlist.list_all()}


def test_add_token_rejected_when_concurrency_cap_reached():
    # Req 1.10/1.11: a manual add is rejected when the cap is reached.
    market = FakeMarketDataProvider()
    market.set_pairs("tok-x", [make_snapshot("pair-x")])
    watchlist = InMemoryWatchlistRepository()
    orch = MonitoringOrchestrator(
        config=make_config(), watchlist_repo=watchlist, cap=1
    )
    # Fill the single slot.
    orch.add_pair("occupied")
    ingestor = DataIngestor(
        market, watchlist, InMemoryPairRepository(), admit=orch.add_pair,
        clock=fixed_clock(),
    )
    result = ingestor.add_token_to_watchlist("tok-x", Network.SOLANA)
    assert isinstance(result, Err)
    # The fresh watchlist entry was deactivated (no partial monitoring state).
    assert watchlist.get("pair-x").value.active is False
    assert orch.is_active("pair-x") is False


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
