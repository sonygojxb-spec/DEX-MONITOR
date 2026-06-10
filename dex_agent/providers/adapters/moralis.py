"""Moralis Solana Data API adapter (PRIMARY).

Design reference: "Per-Integration Details" -> Moralis, and "Moralis Endpoint
Reference (Solana)". Implements :class:`MarketDataProvider`,
:class:`ChainDataProvider`, and :class:`ContractInspectorProvider` over **two
hosts**:

* ``https://solana-gateway.moralis.io`` - Solana-native endpoints (metadata,
  batch metadata, pairs, swaps, holders, top-holders, new tokens, price).
* ``https://deep-index.moralis.io/api/v2.2`` - Token Analytics + Token Score
  (``chain=solana``).

Both authenticate with the ``X-API-Key`` header; the key is injected from
secrets/config and is read-only (design "Security Considerations" item 9). The
adapter never makes a real call itself - it issues requests through the injected
:class:`~dex_agent.providers.clients.HttpClient` (optionally a
:class:`~dex_agent.providers.ratelimit.RateLimitedHttpClient` budgeting CU).

The deprecated **Snipers** and **Filtered Tokens** endpoints are intentionally
NOT used; discovery uses the Pump.fun new-tokens endpoint + token-search, and
bot/sniper detection is left to Token Swaps + Streams deltas (Task 8/4.5).

Mint/freeze authority is **not** sourced here (Moralis metadata is a supporting
risk input only); the authoritative source is the
:class:`~dex_agent.providers.adapters.solana_rpc.SolanaRpcAdapter`. Accordingly
:meth:`inspect_token` fills the supporting risk-signal fields and leaves the
authority fields unset.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from dex_agent.errors import NotFound
from dex_agent.models import HolderBalance, Network, PairSnapshot
from dex_agent.providers.adapters._common import (
    as_list,
    first_present,
    run_request,
    to_bool,
    to_decimal,
    to_int,
    parse_timestamp,
)
from dex_agent.providers.clients import HttpClient
from dex_agent.providers.interfaces import (
    ChainDataProvider,
    ChainTx,
    ContractArtifact,
    ContractInspectorProvider,
    DiscoveryFilters,
    MarketDataProvider,
    SecurityInputs,
    StateHash,
    TxWindow,
)
from dex_agent.result import Err, Ok, Result

SOLANA_GATEWAY = "https://solana-gateway.moralis.io"
DEEP_INDEX = "https://deep-index.moralis.io/api/v2.2"
MAX_BATCH = 100
PROVIDER = "Moralis"


class MoralisAdapter(MarketDataProvider, ChainDataProvider, ContractInspectorProvider):
    """Primary Solana market / chain / security-risk-input adapter."""

    def __init__(
        self,
        http: HttpClient,
        api_key: str,
        *,
        net: str = "mainnet",
        solana_base: str = SOLANA_GATEWAY,
        deep_index_base: str = DEEP_INDEX,
        analytics_bucket: str = "24h",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._http = http
        self._api_key = api_key
        self._net = net
        self._solana = solana_base.rstrip("/")
        self._deep = deep_index_base.rstrip("/")
        self._bucket = analytics_bucket
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # -- internal helpers ------------------------------------------------
    @property
    def _headers(self) -> Mapping[str, str]:
        return {"X-API-Key": self._api_key, "accept": "application/json"}

    def _get_solana(self, path: str, *, params: Mapping[str, Any] | None = None) -> Result[Any]:
        url = f"{self._solana}{path}"
        return run_request(
            lambda: self._http.request("GET", url, headers=self._headers, params=params),
            provider=PROVIDER,
        )

    def _get_deep(self, path: str, *, params: Mapping[str, Any] | None = None) -> Result[Any]:
        merged = {"chain": "solana"}
        if params:
            merged.update(params)
        url = f"{self._deep}{path}"
        return run_request(
            lambda: self._http.request("GET", url, headers=self._headers, params=merged),
            provider=PROVIDER,
        )

    def _post_solana(self, path: str, *, json: Any) -> Result[Any]:
        url = f"{self._solana}{path}"
        return run_request(
            lambda: self._http.request("POST", url, headers=self._headers, json=json),
            provider=PROVIDER,
        )

    def _bucket_value(self, value: Any) -> Any:
        """Pick the configured time bucket (e.g. ``24h``) from a bucketed field."""
        if isinstance(value, Mapping):
            return first_present(value, self._bucket, "24h", "h24", "1h", "total")
        return value

    # -- MarketDataProvider ---------------------------------------------
    def resolve_pairs(
        self, token_address: str, network: Network
    ) -> Result[list[PairSnapshot]]:
        result = self._get_solana(f"/token/{self._net}/{token_address}/pairs")
        if result.is_err():
            return result
        rows = as_list(result.value, "pairs", "result", "data")
        if not rows:
            return Err(NotFound("no pairs for token", identifier=token_address))
        now = self._clock()
        snapshots = [self._pair_to_snapshot(row, now, token_address=token_address) for row in rows]
        return Ok(snapshots)

    def _pair_to_snapshot(self, row: Mapping[str, Any], now: datetime, *, token_address: str | None = None) -> PairSnapshot:
        pair_id = str(
            first_present(row, "pairAddress", "pairId", "pair_address", "address") or ""
        )
        # Derive the token_address from the row if not explicitly provided.
        # Moralis pair responses may include the token mint under various keys.
        resolved_token = token_address or str(
            first_present(row, "tokenAddress", "token_address", "mint", "baseToken") or ""
        ) or None
        # For Pump.fun discovery: if no pair address is available, use the token
        # mint as the pair_id (since Moralis endpoints are mint-keyed anyway).
        if not pair_id and resolved_token:
            pair_id = resolved_token
        return PairSnapshot(
            pair_id=pair_id,
            price=to_decimal(first_present(row, "usdPrice", "priceUsd"), to_decimal("0")) or to_decimal("0"),
            liquidity=to_decimal(first_present(row, "liquidityUsd", "liquidity"), to_decimal("0")) or to_decimal("0"),
            market_cap=to_decimal(first_present(row, "marketCap", "marketCapUsd"), to_decimal("0")) or to_decimal("0"),
            fdv=to_decimal(first_present(row, "fullyDilutedValue", "fdv"), to_decimal("0")) or to_decimal("0"),
            buy_count=to_int(first_present(row, "buys", "buyCount")),
            sell_count=to_int(first_present(row, "sells", "sellCount")),
            buy_volume=to_decimal(first_present(row, "buyVolumeUsd"), to_decimal("0")) or to_decimal("0"),
            sell_volume=to_decimal(first_present(row, "sellVolumeUsd"), to_decimal("0")) or to_decimal("0"),
            fetched_at=now,
            token_address=resolved_token,
        )

    def fetch_pair_snapshot(self, pair_id: str, *, token_address: str | None = None) -> Result[PairSnapshot]:
        # On Solana the Moralis analytics + price endpoints are keyed by the
        # token mint address, NOT the pair/pool address. The caller should pass
        # ``token_address`` when available; if not provided we fall back to using
        # ``pair_id`` (which works when pair_id IS the token mint, e.g. for
        # tokens that use the mint as their primary key).
        mint = token_address or pair_id
        analytics_res = self._get_deep(f"/tokens/{mint}/analytics")
        if analytics_res.is_err():
            return analytics_res
        price_res = self._get_solana(f"/token/{self._net}/{mint}/price")
        if price_res.is_err():
            return price_res
        analytics = analytics_res.value if isinstance(analytics_res.value, Mapping) else {}
        price = price_res.value if isinstance(price_res.value, Mapping) else {}
        now = self._clock()
        snapshot = PairSnapshot(
            pair_id=pair_id,
            price=to_decimal(first_present(price, "usdPrice", "usdPriceFormatted"), to_decimal("0")) or to_decimal("0"),
            liquidity=to_decimal(first_present(analytics, "totalLiquidityUsd", "totalLiquidity"), to_decimal("0")) or to_decimal("0"),
            market_cap=to_decimal(first_present(analytics, "marketCap"), to_decimal("0")) or to_decimal("0"),
            fdv=to_decimal(first_present(analytics, "totalFullyDilutedValuation", "fullyDilutedValuation"), to_decimal("0")) or to_decimal("0"),
            buy_count=to_int(self._bucket_value(analytics.get("totalBuys"))),
            sell_count=to_int(self._bucket_value(analytics.get("totalSells"))),
            buy_volume=to_decimal(self._bucket_value(analytics.get("totalBuyVolume")), to_decimal("0")) or to_decimal("0"),
            sell_volume=to_decimal(self._bucket_value(analytics.get("totalSellVolume")), to_decimal("0")) or to_decimal("0"),
            fetched_at=now,
            token_address=mint,
        )
        return Ok(snapshot)

    def discover_recent_pairs(
        self, filters: DiscoveryFilters, since: datetime
    ) -> Result[list[PairSnapshot]]:
        exchange = filters.exchange or "pumpfun"
        result = self._get_solana(f"/token/{self._net}/exchange/{exchange}/new")
        if result.is_err():
            return result
        rows = as_list(result.value, "result", "tokens", "data")
        now = self._clock()
        out: list[PairSnapshot] = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            created = parse_timestamp(first_present(row, "createdAt", "created_at"), now)
            if created < since:
                continue
            # The Pump.fun new-tokens response includes the token mint address.
            # Derive it from the row and pass it to _pair_to_snapshot.
            token_mint = str(
                first_present(row, "mint", "tokenAddress", "token_address", "address") or ""
            ) or None
            snapshot = self._pair_to_snapshot(row, now, token_address=token_mint)
            # Override fetched_at with the actual creation time for recency checks.
            snapshot = PairSnapshot(
                pair_id=snapshot.pair_id,
                price=snapshot.price,
                liquidity=snapshot.liquidity,
                market_cap=snapshot.market_cap,
                fdv=snapshot.fdv,
                buy_count=snapshot.buy_count,
                sell_count=snapshot.sell_count,
                buy_volume=snapshot.buy_volume,
                sell_volume=snapshot.sell_volume,
                fetched_at=created,
                token_address=token_mint or snapshot.token_address,
            )
            out.append(snapshot)
        return Ok(out)

    # -- ChainDataProvider ----------------------------------------------
    def fetch_contract(
        self, token_address: str, network: Network
    ) -> Result[ContractArtifact]:
        result = self._get_solana(f"/token/{self._net}/{token_address}/metadata")
        if result.is_err():
            return result
        meta = result.value if isinstance(result.value, Mapping) else {}
        return Ok(self._metadata_to_artifact(token_address, network, meta))

    def _metadata_to_artifact(
        self, token_address: str, network: Network, meta: Mapping[str, Any]
    ) -> ContractArtifact:
        metaplex = meta.get("metaplex") if isinstance(meta.get("metaplex"), Mapping) else {}
        return ContractArtifact(
            token_address=token_address,
            network=network,
            mint_authority=None,  # not authoritative via Moralis (use Solana RPC)
            freeze_authority=None,
            has_transfer_fee_extension=False,
            update_authority=metaplex.get("updateAuthority"),
            is_mutable=to_bool(metaplex.get("isMutable")),
            is_verified=to_bool(meta.get("isVerifiedContract")),
            possible_spam=to_bool(meta.get("possibleSpam")),
            score=to_decimal(meta.get("score")),
            raw=dict(meta),
        )

    def fetch_contract_state_hash(self, token_address: str) -> Result[StateHash]:
        result = self._get_solana(f"/token/{self._net}/{token_address}/metadata")
        if result.is_err():
            return result
        meta = result.value if isinstance(result.value, Mapping) else {}
        metaplex = meta.get("metaplex") if isinstance(meta.get("metaplex"), Mapping) else {}
        digest = "|".join(
            str(x)
            for x in (
                metaplex.get("updateAuthority"),
                metaplex.get("isMutable"),
                meta.get("totalSupply"),
                meta.get("isVerifiedContract"),
            )
        )
        return Ok(StateHash(value=digest))

    def fetch_holder_distribution(
        self, token_address: str
    ) -> Result[list[HolderBalance]]:
        result = self._get_solana(f"/token/{self._net}/{token_address}/top-holders")
        if result.is_err():
            return result
        rows = as_list(result.value, "result", "holders", "data")
        holders = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            wallet = first_present(row, "ownerAddress", "address", "owner", "wallet")
            balance = to_decimal(
                first_present(row, "balanceFormatted", "balance", "amount"),
                to_decimal("0"),
            )
            if wallet is None:
                continue
            holders.append(HolderBalance(wallet=str(wallet), balance=balance or to_decimal("0")))
        return Ok(holders)

    def fetch_transactions(
        self, pair_id: str, window: TxWindow
    ) -> Result[list[ChainTx]]:
        # ``pair_id`` carries the token mint address for the Moralis swaps endpoint.
        result = self._get_solana(f"/token/{self._net}/{pair_id}/swaps")
        if result.is_err():
            return result
        rows = as_list(result.value, "result", "swaps", "data")
        txs: list[ChainTx] = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            block_time = parse_timestamp(
                first_present(row, "blockTimestamp", "block_timestamp", "blockTime"),
                window.start,
            )
            if not (window.start <= block_time <= window.end):
                continue
            tx_type = str(first_present(row, "transactionType", "type") or "").lower()
            txs.append(
                ChainTx(
                    signature=str(first_present(row, "transactionHash", "signature", "txHash") or ""),
                    wallet_address=str(first_present(row, "walletAddress", "wallet") or ""),
                    tx_type=tx_type,
                    bought_amount=self._amount(row.get("bought")),
                    sold_amount=self._amount(row.get("sold")),
                    block_time=block_time,
                    raw=dict(row),
                )
            )
        return Ok(txs)

    @staticmethod
    def _amount(value: Any) -> Any:
        if isinstance(value, Mapping):
            return to_decimal(first_present(value, "amount", "amountFormatted", "usdAmount"))
        return to_decimal(value)

    # -- ContractInspectorProvider --------------------------------------
    def inspect_token(
        self, token_address: str, network: Network
    ) -> Result[SecurityInputs]:
        meta_res = self._get_solana(f"/token/{self._net}/{token_address}/metadata")
        if meta_res.is_err():
            return meta_res
        meta = meta_res.value if isinstance(meta_res.value, Mapping) else {}
        metaplex = meta.get("metaplex") if isinstance(meta.get("metaplex"), Mapping) else {}
        # Token Score is a supporting risk input (best-effort; ignore failure).
        score = to_decimal(meta.get("score"))
        score_res = self._get_deep(f"/tokens/{token_address}/score")
        if score_res.is_ok() and isinstance(score_res.value, Mapping):
            score = to_decimal(score_res.value.get("score"), score)
        return Ok(
            SecurityInputs(
                token_address=token_address,
                update_authority=metaplex.get("updateAuthority"),
                is_mutable=to_bool(metaplex.get("isMutable")),
                is_verified=to_bool(meta.get("isVerifiedContract")),
                possible_spam=to_bool(meta.get("possibleSpam")),
                score=score,
                signal_source="Moralis",
                raw=dict(meta),
            )
        )

    # -- batch coalescing (Rate Limits & Real-Time Strategy) ------------
    def fetch_metadata_batch(
        self, token_addresses: list[str], network: Network = Network.SOLANA
    ) -> Result[list[ContractArtifact]]:
        """Coalesce token metadata lookups via POST batch (<=100 per call).

        Splits ``token_addresses`` into chunks of at most :data:`MAX_BATCH` and
        issues one POST ``/token/{net}/metadata`` per chunk, aggregating the
        artifacts. This is the batched path the rate-limiter budgets at 100 CU
        per call (design "Rate Limits & Real-Time Strategy").
        """
        out: list[ContractArtifact] = []
        for start in range(0, len(token_addresses), MAX_BATCH):
            chunk = token_addresses[start : start + MAX_BATCH]
            result = self._post_solana(
                f"/token/{self._net}/metadata", json={"addresses": chunk}
            )
            if result.is_err():
                return result
            rows = as_list(result.value, "result", "data")
            by_addr = {}
            for row in rows:
                if isinstance(row, Mapping):
                    addr = first_present(row, "mint", "address", "tokenAddress")
                    if addr is not None:
                        by_addr[str(addr)] = row
            for addr in chunk:
                meta = by_addr.get(addr, {})
                out.append(self._metadata_to_artifact(addr, network, meta))
        return Ok(out)


__all__ = ["MoralisAdapter", "SOLANA_GATEWAY", "DEEP_INDEX", "MAX_BATCH"]
