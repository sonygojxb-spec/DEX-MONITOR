"""Unit tests for the per-provider rate limiter (Task 4.3).

Covers the token bucket, CU cost resolution, and the RateLimitedHttpClient
wrapper (including budget exhaustion -> RateLimitExceeded and the
remaining-budget signal). A controllable clock keeps tests deterministic.
"""

from __future__ import annotations

import pytest

from dex_agent.providers import (
    FakeHttpClient,
    MORALIS_CU_COSTS,
    ProviderRateLimiter,
    RateLimitExceeded,
    RateLimitedHttpClient,
    TokenBucket,
    moralis_cu_for,
)


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_token_bucket_consume_and_refill():
    clock = FakeClock()
    bucket = TokenBucket(capacity=100, refill_per_second=10, clock=clock)
    assert bucket.try_consume(100) is True
    assert bucket.try_consume(1) is False  # empty
    clock.advance(5)  # +50 tokens
    assert bucket.available == pytest.approx(50)
    assert bucket.try_consume(50) is True


def test_token_bucket_never_negative_and_caps_at_capacity():
    clock = FakeClock()
    bucket = TokenBucket(capacity=100, refill_per_second=10, clock=clock)
    bucket.try_consume(40)
    clock.advance(1000)  # would overfill, but caps at capacity
    assert bucket.available == pytest.approx(100)


def test_token_bucket_time_until():
    clock = FakeClock()
    bucket = TokenBucket(capacity=100, refill_per_second=10, clock=clock)
    bucket.try_consume(100)
    assert bucket.time_until(30) == pytest.approx(3.0)


def test_moralis_cu_for_endpoint_mapping():
    assert moralis_cu_for("GET", "https://solana-gateway.moralis.io/token/mainnet/X/metadata") == MORALIS_CU_COSTS["metadata"]
    assert moralis_cu_for("POST", "https://solana-gateway.moralis.io/token/mainnet/metadata") == MORALIS_CU_COSTS["metadata_batch"]
    assert moralis_cu_for("GET", "https://deep-index.moralis.io/api/v2.2/tokens/X/analytics") == MORALIS_CU_COSTS["analytics"]
    assert moralis_cu_for("GET", "https://deep-index.moralis.io/api/v2.2/tokens/X/score") == MORALIS_CU_COSTS["token_score"]
    assert moralis_cu_for("GET", "https://solana-gateway.moralis.io/token/mainnet/X/top-holders") == MORALIS_CU_COSTS["top_holders"]
    assert moralis_cu_for("GET", "https://solana-gateway.moralis.io/token/mainnet/holders/X") == MORALIS_CU_COSTS["holders"]
    assert moralis_cu_for("GET", "https://solana-gateway.moralis.io/token/mainnet/X/swaps") == MORALIS_CU_COSTS["swaps"]
    assert moralis_cu_for("GET", "https://solana-gateway.moralis.io/token/mainnet/X/pairs") == MORALIS_CU_COSTS["pairs"]
    assert moralis_cu_for("GET", "https://solana-gateway.moralis.io/token/mainnet/X/price") == MORALIS_CU_COSTS["price"]


def test_provider_rate_limiter_moralis_budget_and_remaining():
    clock = FakeClock()
    limiter = ProviderRateLimiter.moralis(cu_per_window=100, window_seconds=1, clock=clock)
    assert limiter.charge(80) is True
    assert limiter.remaining() == pytest.approx(20)
    assert limiter.charge(80) is False  # exceeds remaining
    assert limiter.remaining() == pytest.approx(20)


def test_rate_limited_http_client_charges_cu_and_blocks_when_exhausted():
    clock = FakeClock()
    inner = FakeHttpClient().stub("/metadata", {"ok": True})
    limiter = ProviderRateLimiter.moralis(cu_per_window=100, window_seconds=1, clock=clock)
    client = RateLimitedHttpClient(inner, limiter, cost_fn=moralis_cu_for)

    # batch metadata costs 100 CU -> consumes the whole budget
    resp = client.request("POST", "https://solana-gateway.moralis.io/token/mainnet/metadata", json={"addresses": ["a"]})
    assert resp.json == {"ok": True}
    assert client.remaining_budget() == pytest.approx(0)

    # next request cannot be funded -> RateLimitExceeded, inner NOT called again
    before = len(inner.calls)
    with pytest.raises(RateLimitExceeded):
        client.request("GET", "https://solana-gateway.moralis.io/token/mainnet/X/metadata")
    assert len(inner.calls) == before


def test_rate_limited_http_client_recovers_after_refill():
    clock = FakeClock()
    inner = FakeHttpClient().stub("/price", {"usdPrice": "1"})
    limiter = ProviderRateLimiter.moralis(cu_per_window=100, window_seconds=1, clock=clock)
    client = RateLimitedHttpClient(inner, limiter, cost_fn=moralis_cu_for)
    # spend 50 (price), then exhaust
    client.request("GET", "https://x/token/mainnet/X/price")
    client.request("GET", "https://x/token/mainnet/X/price")
    with pytest.raises(RateLimitExceeded):
        client.request("GET", "https://x/token/mainnet/X/price")
    clock.advance(1)  # full refill
    resp = client.request("GET", "https://x/token/mainnet/X/price")
    assert resp.json == {"usdPrice": "1"}


def test_per_minute_limiter_for_dexscreener_fallback():
    clock = FakeClock()
    limiter = ProviderRateLimiter.per_minute("dexscreener", 300, clock=clock)
    assert limiter.name == "dexscreener"
    assert all(limiter.charge(1) for _ in range(300))
    assert limiter.charge(1) is False
