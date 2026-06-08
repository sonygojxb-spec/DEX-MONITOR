"""Per-provider rate limiting fronting each adapter.

Design reference: "Concurrency" (back-pressure via per-provider rate limiting)
and "Rate Limits & Real-Time Strategy". Monitoring 200 pairs at the 5s minimum
refresh would exceed provider limits, so each adapter's transport is fronted by
a reusable token-bucket limiter:

* **Moralis (PRIMARY)** is budgeted by **compute units (CU)** per endpoint
  (metadata 10 / batch metadata 100, analytics 80, token score 100,
  holders/top-holders 50, swaps 50, pairs 50, price 50). Token lookups are
  batched via the batch-metadata endpoint (POST, <=100 addresses).
* The limiter exposes a **remaining-budget signal** (:meth:`TokenBucket.available`
  / :meth:`ProviderRateLimiter.remaining`) that the Orchestrator consumes to
  derive the effective poll interval (Task 18.7).
* **DexScreener** (~300 req/min token/pair, ~60 req/min profiles/boosts) and
  **GoPlus** limits apply only when those optional fallbacks are active.

The limiter is a pure, monotonic-clock-driven token bucket so it is
deterministically testable. :class:`RateLimitedHttpClient` wraps any
:class:`~dex_agent.providers.clients.HttpClient` and charges the bucket per
request using a pluggable cost function; when the budget cannot cover a request
it raises :class:`~dex_agent.providers.clients.RateLimitExceeded`, which the
adapter maps to a :class:`~dex_agent.errors.ProviderError`.
"""

from __future__ import annotations

import time as _time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from dex_agent.providers.clients import (
    HttpClient,
    HttpResponse,
    RateLimitExceeded,
)

# ---------------------------------------------------------------------------
# Cost tables (design "Moralis Endpoint Reference (Solana)" CU column)
# ---------------------------------------------------------------------------

# Logical endpoint key -> compute-unit cost.
MORALIS_CU_COSTS: Mapping[str, int] = {
    "metadata": 10,
    "metadata_batch": 100,
    "analytics": 80,
    "token_score": 100,
    "holders": 50,
    "top_holders": 50,
    "swaps": 50,
    "pairs": 50,
    "price": 50,
    "price_batch": 50,
    "new_tokens": 50,
    "search": 50,
}

# Default CU charged for an unrecognized Moralis endpoint (conservative).
MORALIS_DEFAULT_CU = 50

# DexScreener request-count limits (requests/min) by endpoint group; applied
# only when the optional DexScreener fallback is active.
DEXSCREENER_RPM: Mapping[str, int] = {
    "tokens": 300,
    "pairs": 300,
    "profiles": 60,
    "boosts": 60,
}


def moralis_cu_for(method: str, url: str) -> int:
    """Resolve the CU cost for a Moralis request from its method + URL.

    The mapping inspects the URL path so the same limiter can be shared across
    both Moralis hosts (``solana-gateway`` and ``deep-index``). The batch
    metadata endpoint (POST ``/token/{net}/metadata``) costs 100 CU; the single
    metadata GET costs 10.
    """
    u = url.lower()
    is_post = method.upper() == "POST"
    if "/metadata" in u:
        if is_post or "/prices" in u:
            # POST batch metadata / batch prices
            return MORALIS_CU_COSTS["metadata_batch"] if "/metadata" in u else MORALIS_CU_COSTS["price_batch"]
        return MORALIS_CU_COSTS["metadata"]
    if "/prices" in u:
        return MORALIS_CU_COSTS["price_batch"]
    if "/analytics" in u:
        return MORALIS_CU_COSTS["analytics"]
    if "/score" in u:
        return MORALIS_CU_COSTS["token_score"]
    if "/top-holders" in u:
        return MORALIS_CU_COSTS["top_holders"]
    if "/holders" in u:
        return MORALIS_CU_COSTS["holders"]
    if "/swaps" in u:
        return MORALIS_CU_COSTS["swaps"]
    if "/pairs" in u:
        return MORALIS_CU_COSTS["pairs"]
    if "/price" in u:
        return MORALIS_CU_COSTS["price"]
    if "/new" in u:
        return MORALIS_CU_COSTS["new_tokens"]
    if "/search" in u:
        return MORALIS_CU_COSTS["search"]
    return MORALIS_DEFAULT_CU


# ---------------------------------------------------------------------------
# Token bucket
# ---------------------------------------------------------------------------

Clock = Callable[[], float]


class TokenBucket:
    """A monotonic-clock token bucket.

    ``capacity`` tokens accrue at ``refill_per_second`` up to the cap. A request
    consumes ``cost`` tokens via :meth:`try_consume`; it succeeds (returning
    ``True``) only when enough tokens are available, never going negative. The
    ``clock`` is injectable so tests advance time deterministically without
    sleeping.

    For a Moralis CU budget, set ``capacity`` to the per-window CU allowance and
    ``refill_per_second`` to ``allowance / window_seconds``.
    """

    def __init__(
        self,
        capacity: float,
        refill_per_second: float,
        *,
        clock: Clock = _time.monotonic,
        initial: float | None = None,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")
        self.capacity = float(capacity)
        self.refill_per_second = float(refill_per_second)
        self._clock = clock
        self._tokens = float(initial if initial is not None else capacity)
        self._last = clock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_second)
            self._last = now

    @property
    def available(self) -> float:
        """Current available tokens (the remaining-budget signal)."""
        self._refill()
        return self._tokens

    def try_consume(self, cost: float = 1.0) -> bool:
        """Consume ``cost`` tokens if available; return whether it succeeded."""
        if cost < 0:
            raise ValueError("cost must be non-negative")
        self._refill()
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def time_until(self, cost: float) -> float:
        """Seconds until ``cost`` tokens would be available (0 if already)."""
        self._refill()
        if self._tokens >= cost:
            return 0.0
        if self.refill_per_second == 0:
            return float("inf")
        return (cost - self._tokens) / self.refill_per_second


# ---------------------------------------------------------------------------
# Provider rate limiter
# ---------------------------------------------------------------------------


class ProviderRateLimiter:
    """A named token-bucket limiter fronting one provider.

    Wraps a :class:`TokenBucket` and exposes :meth:`charge` (consume a cost) and
    :meth:`remaining` (the remaining-budget signal). Construct CU-budgeted
    Moralis limiters with :meth:`moralis`, request-count DexScreener limiters
    with :meth:`per_minute`.
    """

    def __init__(self, name: str, bucket: TokenBucket) -> None:
        self.name = name
        self.bucket = bucket

    @classmethod
    def moralis(
        cls,
        cu_per_window: float,
        window_seconds: float = 1.0,
        *,
        clock: Clock = _time.monotonic,
    ) -> "ProviderRateLimiter":
        """A Moralis CU-budgeted limiter (``cu_per_window`` CU per window)."""
        bucket = TokenBucket(
            capacity=cu_per_window,
            refill_per_second=cu_per_window / window_seconds,
            clock=clock,
        )
        return cls("moralis", bucket)

    @classmethod
    def per_minute(
        cls,
        name: str,
        requests_per_minute: float,
        *,
        clock: Clock = _time.monotonic,
    ) -> "ProviderRateLimiter":
        """A request-count limiter (e.g. DexScreener / GoPlus fallbacks)."""
        bucket = TokenBucket(
            capacity=requests_per_minute,
            refill_per_second=requests_per_minute / 60.0,
            clock=clock,
        )
        return cls(name, bucket)

    def charge(self, cost: float = 1.0) -> bool:
        """Charge ``cost`` to the budget; return whether it was allowed."""
        return self.bucket.try_consume(cost)

    def remaining(self) -> float:
        """The remaining budget (Orchestrator poll-interval input, Task 18.7)."""
        return self.bucket.available


# A cost function maps a (method, url) request to its budget cost.
CostFn = Callable[[str, str], float]


def _unit_cost(method: str, url: str) -> float:
    return 1.0


class RateLimitedHttpClient:
    """An :class:`HttpClient` decorator that charges a limiter per request.

    Wraps an inner client and a :class:`ProviderRateLimiter`. Before each
    request it computes the cost via ``cost_fn`` and charges the limiter; if the
    budget cannot cover the request it raises
    :class:`~dex_agent.providers.clients.RateLimitExceeded` (which the adapter
    maps to a ``ProviderError``) and the underlying request is **not** issued.
    Use :func:`moralis_cu_for` as ``cost_fn`` to budget Moralis by CU.
    """

    def __init__(
        self,
        inner: HttpClient,
        limiter: ProviderRateLimiter,
        *,
        cost_fn: CostFn = _unit_cost,
    ) -> None:
        self._inner = inner
        self._limiter = limiter
        self._cost_fn = cost_fn

    def remaining_budget(self) -> float:
        """Expose the limiter's remaining-budget signal."""
        return self._limiter.remaining()

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        cost = self._cost_fn(method, url)
        if not self._limiter.charge(cost):
            raise RateLimitExceeded(
                f"{self._limiter.name}: rate-limit budget exhausted "
                f"(need {cost}, remaining {self._limiter.remaining():.1f})"
            )
        return self._inner.request(
            method, url, headers=headers, params=params, json=json, timeout=timeout
        )


__all__ = [
    "MORALIS_CU_COSTS",
    "MORALIS_DEFAULT_CU",
    "DEXSCREENER_RPM",
    "moralis_cu_for",
    "TokenBucket",
    "ProviderRateLimiter",
    "RateLimitedHttpClient",
    "CostFn",
]
