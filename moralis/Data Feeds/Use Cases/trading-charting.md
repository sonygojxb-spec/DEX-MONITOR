> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Trading & Charting

> A Data Feeds recipe bundle for trading terminals, charting UIs, and bots — every DEX trade per pool and per token, candles, live reserves, and USD marks, synced into your own database.

### Who it's for

Teams building **trading terminals, charting UIs, market-data backends, and trading bots** — anything that needs live, owned market data keyed by pool/pair or by token. The goal is your own market-data store: every fill on a pool, every trade touching a token, OHLCV candles, current pool reserves, and a USD mark for every asset — all reorg-safe and current at the chain head.

### The recipe bundle

This use case combines the markets recipes. **Swaps by Pair** is the trade backbone (one row per fill); **Pair OHLCV** is a downstream aggregation of that same trade ingest; **Swaps by Token** re-keys the trades for token-centric views; **Pair Reserves** and **Token Prices** add live state and valuation.

| Recipe                                                       | Role in the terminal                                                                                                                                                    |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Swaps by Pair](/data-feeds/recipes/markets/swaps-by-pair)   | The trade backbone — every fill on a pool/pair (direct pool fills and aggregator-routed trades), one row per trade, USD-enriched in-block. The "trade tape" for a pool. |
| [Swaps by Token](/data-feeds/recipes/markets/swaps-by-token) | The same trades re-keyed by token — every trade that touched token X, found under either side of the pair. The token-centric tape.                                      |
| [Pair OHLCV](/data-feeds/recipes/markets/pair-ohlcv)         | Time-bucketed open/high/low/close + volume + trade count per pool, built by aggregating the swap ingest into candles.                                                   |
| [Pair Reserves](/data-feeds/recipes/markets/pair-reserves)   | Current `reserve0` / `reserve1` per pool, read from each swap's pool post-balances — live depth without a running sum.                                                  |
| [Token Prices](/data-feeds/recipes/token/token-prices)       | USD/native mark history per token, plus a latest-mark dictionary for carry-forward valuation of quiet positions.                                                        |

<Note>
  **Swaps by Pair, Swaps by Token, and Pair OHLCV share one trade projection.** They are the same trade ingest shaped three ways — one row per fill keyed by pool, the same fills re-keyed by token, and those fills bucketed into candles. Pick the keys your screens read; you don't need all three if one access pattern covers your UI.
</Note>

### How the pieces fit

```
                     ┌──►  Swaps by Pair    (trade tape, by pool)
trade fills  ────────┼──►  Swaps by Token   (trade tape, by token)
                     └──►  Pair OHLCV        (candles, by pool)

pool post-balances ──►  Pair Reserves       (live depth, by pool)
price updates      ──►  Token Prices        (USD/native marks, by token)
```

* **The swap recipes** all draw from the same normalized in-block trade events — direct pool fills (`tokenSwaps`) and aggregator-routed trades (`aggregateTokenSwaps`) — so every fill lands exactly once. Key by pool for a pool's tape, by token for a token's tape.
* **Pair OHLCV** is a downstream aggregation of that ingest: the same trades land, then a candle surface buckets them per `(pool, hour)`. "Price" per fill is the bought-leg in-block USD mark; `volume` is summed notional; `trades` is the count.
* **Pair Reserves** reads the pool's absolute `token0PostBalance` / `token1PostBalance` from each swap, so current reserves are simply the latest observation per pair — live depth without reconstructing a running sum.
* **Token Prices** is the connective tissue for valuation: join any trade, balance, or position to the token's mark, and use the latest-mark dictionary to value quiet positions with no fresh update.

### Building a pool overview

A trading terminal's pool screen wants the live tape, the candles, the current depth, and a mark — each from its own recipe, keyed by the same pool. Read ClickHouse with `FINAL` or a sign-aware aggregate so reorg `±1` pairs collapse before you aggregate; never a bare `WHERE sign = 1`.

The trade tape for a pool, newest first:

```sql theme={null}
SELECT  event_ts, side, source_kind,
        token0_address, token1_address,
        amount0, amount1, notional_usd, protocol
FROM    recipe_swaps_by_pair.fact_swaps_by_pair FINAL
WHERE   chain_id = 1
  AND   pool_address = lower('0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640')
ORDER BY event_ts DESC
LIMIT 50;
```

The hourly candles backing the chart (fast sign-aware accelerator):

```sql theme={null}
SELECT  bucket_start, open, high, low, close, volume, trades
FROM    recipe_pair_ohlcv.candles
WHERE   chain_id = 1
  AND   pool_address = lower('0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640')
ORDER BY bucket_start DESC
LIMIT 24;
```

The current depth (latest reserves; `FINAL` collapses reorg pairs before `argMax`):

```sql theme={null}
SELECT  pair_address,
        argMax(reserve0, (block_number, log_index)) AS reserve0,
        argMax(reserve1, (block_number, log_index)) AS reserve1
FROM    recipe_pair_reserves.fact_pair_reserves FINAL
WHERE   chain_id = 1
  AND   pair_address = lower('0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640')
GROUP BY pair_address;
```

And the latest USD mark for either side, via the Token Prices dictionary (O(1), refreshes every 30–60s — no fresh trade required):

```sql theme={null}
SELECT dictGetOrDefault(
         'recipe_token_price_history.latest_token_price_dict', 'usd_price',
         tuple(1, lower('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')), '0'
       ) AS usd_price;
```

For a token's market overview across all its pools, swap `fact_swaps_by_pair` for `recipe_swaps_by_token.fact_swaps_by_token` keyed on `token_address`.

### Notes and considerations

* **EVM + Solana.** The trade, candle, reserve, and price recipes are chain-parametrized. On Solana, repeated `logIndex` within one instruction means the pool-fill `vendor_event_id` should be widened (e.g. with the token addresses/amounts) to keep rows distinct; the candle math is chain-agnostic.
* **One trade, two pool addresses.** A fill observed both as a direct pool fill (`pairAddress`) and as part of an aggregator route (`aggregatorAddress`) appears under both — they are distinct events by design. `source_kind` (`pool_fill` vs `aggregator`) tells them apart.
* **USD is in-block only.** Trades, candles, and notional are enriched from same-block `tokenPriceUpdates` — no cross-block carry-forward. Illiquid or brand-new tokens with no in-block mark leave `price_usd` / `notional_usd` `NULL` (and produce candle gaps for that hour). For valuing quiet positions, use the Token Prices latest-mark dictionary, which carries the last on-chain mark forward.
* **OHLCV is fixed 1-hour and trade-reconstructed.** Candles are built from on-chain swap fills, so they can differ slightly from a DEX's own reported OHLC. For other intervals, re-bucket the trade ingest. Use `candles` for the fast accelerator and `candles_exact` (over `fact_swaps FINAL`) when post-reorg precision on high/low matters; `volume` and `trades` are sign-weighted and always exact.
* **Reserves need an in-window swap.** Current reserves come from swap post-balances, so a pool appears only if it had at least one swap with resolved post-balances in the ingested window. Quiet pools have unchanged reserves by definition — widen the window to pick them up.
* **Run ClickHouse in `hybrid` for live terminals.** It backfills history then hands off to a seamless, reorg-safe realtime tail at the chain head. Postgres/MySQL are first-class for historical backfill; the trade recipes expand many rows per block, so live/reorg-safe ingestion is ClickHouse-only.
* **Pair with other bundles.** Add [Swaps by Wallet](/data-feeds/recipes/markets/swaps-by-wallet) for per-user trade history, or see [Token Analytics](/data-feeds/use-cases/token-analytics) and [Portfolio Tracking](/data-feeds/use-cases/portfolio-tracking) for adjacent recipe bundles.

### Get started

Data Feeds is in early access.

<Card title="Request Early Access" icon="rocket" href="/data-feeds/early-access">
  Build a live, owned market-data backend with the Moralis team.
</Card>
