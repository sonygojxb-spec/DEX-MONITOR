"""DexScreener adapter - OPTIONAL market-data fallback.

Design reference: "Per-Integration Details" -> DexScreener. A public REST source
for price, liquidity, market cap, FDV, and bucketed buy/sell counts/volumes,
used **only** as a fallback behind :class:`MarketDataProvider` when Moralis
market data is unavailable, or for cross-checking. There is no websocket, so
data is polled; rate limits (~300 req/min token/pair) apply only while this
fallback is active. **Disabled unless wired in configuration** - construct it
only when a fallback is configured.

Like every adapter it takes an injected
:class:`~dex_agent.providers.clients.HttpClient`, so no real network call occurs
in tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from dex_agent.errors import NotFound
from dex_agent.models import Network, PairSnapshot
from dex_agent.providers.adapters._common import (
    as_list,
    first_present,
    run_request,
    to_decimal,
    to_int,
    parse_timestamp,
)
from dex_agent.providers.clients import HttpClient
from dex_agent.providers.interfaces import (
    DiscoveryFilters,
    MarketDataProvider,
)
from dex_agent.result import Err, Ok, Result

BASE_URL = "https://api.dexscreener.com"
PROVIDER = "DexScreener"


class DexScreenerAdapter(MarketDataProvider):
    """Optional fallback :class:`MarketDataProvider` (disabled by default)."""

    def __init__(
        self,
        http: HttpClient,
        *,
        base_url: str = BASE_URL,
        chain: str = "solana",
        volume_bucket: str = "h24",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._http = http
        self._base = base_url.rstrip("/")
        self._chain = chain
        self._bucket = volume_bucket
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _get(self, path: str) -> Result[Any]:
        url = f"{self._base}{path}"
        return run_request(
            lambda: self._http.request("GET", url, headers={"accept": "application/json"}),
            provider=PROVIDER,
        )

    def _bucketed(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return first_present(value, self._bucket, "h24", "h6", "h1", "m5")
        return value

    def _to_snapshot(self, row: Mapping[str, Any], now: datetime) -> PairSnapshot:
        txns = row.get("txns") if isinstance(row.get("txns"), Mapping) else {}
        bucket_txns = self._bucketed(txns) if txns else {}
        bucket_txns = bucket_txns if isinstance(bucket_txns, Mapping) else {}
        volume = row.get("volume") if isinstance(row.get("volume"), Mapping) else {}
        liquidity = row.get("liquidity") if isinstance(row.get("liquidity"), Mapping) else {}
        return PairSnapshot(
            pair_id=str(first_present(row, "pairAddress", "pairId") or ""),
            price=to_decimal(first_present(row, "priceUsd"), to_decimal("0")) or to_decimal("0"),
            liquidity=to_decimal(first_present(liquidity, "usd"), to_decimal("0")) or to_decimal("0"),
            market_cap=to_decimal(first_present(row, "marketCap"), to_decimal("0")) or to_decimal("0"),
            fdv=to_decimal(first_present(row, "fdv"), to_decimal("0")) or to_decimal("0"),
            buy_count=to_int(bucket_txns.get("buys")),
            sell_count=to_int(bucket_txns.get("sells")),
            buy_volume=to_decimal(self._bucketed(volume), to_decimal("0")) or to_decimal("0"),
            sell_volume=to_decimal("0"),
            fetched_at=now,
        )

    def resolve_pairs(
        self, token_address: str, network: Network
    ) -> Result[list[PairSnapshot]]:
        result = self._get(f"/tokens/v1/{self._chain}/{token_address}")
        if result.is_err():
            return result
        rows = as_list(result.value, "pairs")
        if not rows:
            return Err(NotFound("no pairs for token", identifier=token_address))
        now = self._clock()
        return Ok([self._to_snapshot(r, now) for r in rows if isinstance(r, Mapping)])

    def fetch_pair_snapshot(self, pair_id: str, *, token_address: str | None = None) -> Result[PairSnapshot]:
        result = self._get(f"/latest/dex/pairs/{self._chain}/{pair_id}")
        if result.is_err():
            return result
        rows = as_list(result.value, "pairs", "pair")
        now = self._clock()
        for row in rows:
            if isinstance(row, Mapping):
                return Ok(self._to_snapshot(row, now))
        # Some responses wrap a single pair under "pair".
        pair = result.value.get("pair") if isinstance(result.value, Mapping) else None
        if isinstance(pair, Mapping):
            return Ok(self._to_snapshot(pair, now))
        return Err(NotFound("pair not found", identifier=pair_id))

    def discover_recent_pairs(
        self, filters: DiscoveryFilters, since: datetime
    ) -> Result[list[PairSnapshot]]:
        result = self._get("/token-profiles/latest/v1")
        if result.is_err():
            return result
        rows = as_list(result.value, "profiles", "data")
        now = self._clock()
        out: list[PairSnapshot] = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            created = parse_timestamp(first_present(row, "createdAt", "pairCreatedAt"), now)
            if created < since:
                continue
            out.append(self._to_snapshot(row, now))
        return Ok(out)


__all__ = ["DexScreenerAdapter", "BASE_URL"]
