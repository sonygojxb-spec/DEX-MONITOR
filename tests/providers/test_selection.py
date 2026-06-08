"""Unit tests for the provider-selection / fallback wrappers (Task 4.4).

Verifies that fallbacks are DISABLED by default, that a typed ProviderError /
TimedOut from the primary triggers the configured fallback, that a successful
primary is never overridden, and that NotFound does not trigger fallback unless
explicitly opted in.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from dex_agent.errors import NotFound, ProviderError, TimedOut
from dex_agent.models import Network, PairSnapshot
from dex_agent.providers import (
    FakeContractInspectorProvider,
    FakeMarketDataProvider,
    FallbackContractInspectorProvider,
    FallbackMarketDataProvider,
    SecurityInputs,
)


def _snapshot(pair_id: str, price: str) -> PairSnapshot:
    return PairSnapshot(
        pair_id=pair_id,
        price=Decimal(price),
        liquidity=Decimal("1"),
        market_cap=Decimal("1"),
        fdv=Decimal("1"),
        buy_count=0,
        sell_count=0,
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def test_fallback_disabled_by_default_returns_primary_error():
    primary = FakeMarketDataProvider()
    primary.fail_always("fetch_pair_snapshot", ProviderError("down", provider="moralis"))
    wrapper = FallbackMarketDataProvider(primary)  # no fallback configured
    assert wrapper.fallback_enabled is False
    result = wrapper.fetch_pair_snapshot("p")
    assert result.is_err() and isinstance(result.error, ProviderError)


def test_provider_error_triggers_fallback():
    primary = FakeMarketDataProvider()
    primary.fail_always("fetch_pair_snapshot", ProviderError("moralis down", provider="moralis"))
    fallback = FakeMarketDataProvider()
    fallback.set_snapshot(_snapshot("p", "9"))
    wrapper = FallbackMarketDataProvider(primary, fallback)
    result = wrapper.fetch_pair_snapshot("p")
    assert result.is_ok() and result.value.price == Decimal("9")


def test_timeout_triggers_fallback():
    primary = FakeMarketDataProvider()
    primary.fail_always("resolve_pairs", TimedOut("slow", timeout_s=5))
    fallback = FakeMarketDataProvider()
    fallback.set_pairs("tok", [_snapshot("p", "1")])
    wrapper = FallbackMarketDataProvider(primary, fallback)
    result = wrapper.resolve_pairs("tok", Network.SOLANA)
    assert result.is_ok() and result.value[0].pair_id == "p"


def test_successful_primary_is_not_overridden():
    primary = FakeMarketDataProvider()
    primary.set_snapshot(_snapshot("p", "1"))
    fallback = FakeMarketDataProvider()
    fallback.set_snapshot(_snapshot("p", "2"))
    wrapper = FallbackMarketDataProvider(primary, fallback)
    result = wrapper.fetch_pair_snapshot("p")
    assert result.value.price == Decimal("1")  # primary wins
    assert fallback.calls == []  # fallback never consulted


def test_not_found_does_not_trigger_fallback_by_default():
    primary = FakeMarketDataProvider()  # resolve_pairs -> NotFound (no pairs)
    fallback = FakeMarketDataProvider()
    fallback.set_pairs("tok", [_snapshot("p", "1")])
    wrapper = FallbackMarketDataProvider(primary, fallback)
    result = wrapper.resolve_pairs("tok", Network.SOLANA)
    assert result.is_err() and isinstance(result.error, NotFound)
    assert fallback.calls == []


def test_not_found_triggers_fallback_when_opted_in():
    primary = FakeMarketDataProvider()
    fallback = FakeMarketDataProvider()
    fallback.set_pairs("tok", [_snapshot("p", "1")])
    wrapper = FallbackMarketDataProvider(primary, fallback, fallback_on_not_found=True)
    result = wrapper.resolve_pairs("tok", Network.SOLANA)
    assert result.is_ok() and result.value[0].pair_id == "p"


def test_contract_inspector_fallback_to_goplus_like():
    primary = FakeContractInspectorProvider()
    primary.fail_always("inspect_token", ProviderError("score unavailable", provider="moralis"))
    fallback = FakeContractInspectorProvider()
    fallback.set_inputs(SecurityInputs(token_address="t", freeze_authority="F", signal_source="GoPlus"))
    wrapper = FallbackContractInspectorProvider(primary, fallback)
    result = wrapper.inspect_token("t", Network.SOLANA)
    assert result.is_ok() and result.value.signal_source == "GoPlus"
