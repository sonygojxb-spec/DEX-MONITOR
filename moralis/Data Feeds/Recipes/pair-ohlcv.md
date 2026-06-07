> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Pair OHLCV

> Sync time-bucketed OHLCV candles — open, high, low, close, volume, and trade count per DEX pair — built by aggregating on-chain swaps, into your own database. Mirrors the Moralis GET /pairs/{address}/ohlcv endpoint.

### Question it answers

> "Give me 1-hour OHLCV candles for pool/pair **0x…** — open, high, low, close, volume, and trade count per hour." Mirrors Moralis `GET /pairs/{address}/ohlcv`.

Candles are built by **aggregating swaps**, not reported by an exchange. This recipe is a downstream aggregation on top of the same trade ingest as Swaps by Pair: the sync lands every trade once (USD-enriched in-block), then a candle surface buckets those trades into fixed **1-hour** candles per `(pool_address, hour)`. "Price" per fill is the bought-leg (token1) in-block USD price already on the trade (`price_usd`); `volume` is `sum(abs(notional_usd))` and `trades` is the fill count.

### What you get

One candle row per `(pool_address, bucket_start)`, where `bucket_start` is the start of a 1-hour window. Only **priced** trades (a same-block USD price update for the bought leg) contribute:

| Column         | Description                                                                             |
| -------------- | --------------------------------------------------------------------------------------- |
| `chain_id`     | Chain the pool lives on                                                                 |
| `pool_address` | The DEX pair / pool                                                                     |
| `bucket_start` | Start of the 1-hour candle window                                                       |
| `open`         | First trade's `price_usd` in the bucket (by `event_ts`, tiebroken by `vendor_event_id`) |
| `high`         | `max(price_usd)` across the bucket                                                      |
| `low`          | `min(price_usd)` across the bucket                                                      |
| `close`        | Last trade's `price_usd` in the bucket                                                  |
| `volume`       | `sum(abs(notional_usd))` — absolute traded USD over the bucket                          |
| `trades`       | Count of priced fills in the bucket                                                     |

The candles sit on top of a trade fact table (`fact_swaps` / `swaps`) carrying every fill — `tx_hash`, `trader_address`, `token0/1_address`, `amount0/1`, `side`, `source_kind`, `protocol`, `price_usd`, `notional_usd` — so you can drop to the underlying trades whenever you need detail behind a candle.

### Source

The trade ingest is identical to Swaps by Pair: two projection branches expand the per-block swap arrays into one row per fill —

`tokenSwaps` (pool fills) · `aggregateTokenSwaps` (aggregator routes)

Each fill is USD-enriched **inline** from the same block's `tokenPriceUpdates` (reversed so the chronologically-last update wins on duplicate keys) — no separate price join at read time. The candle surface then aggregates these priced fills by hour.

### Destination

| Destination                  | Trade table  | Candle surface                                                      | Read pattern                                            |
| ---------------------------- | ------------ | ------------------------------------------------------------------- | ------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_swaps` | `candles` (VIEW over `candles_agg`); `candles_exact` (reorg-exact)  | Prefix scan on `(chain_id, pool_address, bucket_start)` |
| **Postgres**                 | `swaps`      | `candles` (always-fresh VIEW) + `candles_mat` (REFRESHable matview) | Index on `(pool_address, bucket_start DESC)`            |
| **MySQL**                    | `swaps`      | `candles` (always-fresh VIEW)                                       | Index on `(pool_address, block_timestamp)`              |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct. Two candle surfaces ship on ClickHouse: `candles` is a low-latency accelerator backed by an `AggregatingMergeTree` that is sign-aware for additive measures, and `candles_exact` reads `fact_swaps FINAL` for always-exact OHLC. On Postgres/MySQL the `candles` VIEW aggregates `swaps` at read time and is correct the moment a backfill lands.

### Full schema

Below are the trade fact table and the candle surfaces this recipe produces. The candle columns are a fixed shape (`open`/`high`/`low`/`close`/`volume`/`trades`); the underlying trade table is the wider starting point — keep the columns you need (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). Raw `uint256` amounts are stored as text on ClickHouse and `NUMERIC(76,0)` on Postgres (they exceed standard numeric precision); USD columns are wide decimals so a low-decimals token × price never overflows.

<Accordion title="ClickHouse — fact_swaps + candles">
  ```sql theme={null}
  -- Trade fact: one row per fill, sign-carrying for reorg collapse.
  CREATE TABLE recipe_pair_ohlcv.fact_swaps
  (
      vendor_event_id     String,
      ingested_at         DateTime64(3),
      chain_id            UInt32,
      block_hash          String,
      block_number        UInt64,
      event_ts            DateTime64(3),
      pool_address        String,        -- pair (pool_fill) or aggregator
      token0_address      String,
      token1_address      String,
      amount0             String,        -- raw uint256
      amount1             String,        -- raw uint256
      trader_address      String,
      price_usd           Nullable(String),   -- bought-leg (token1) USD price
      notional_usd        Nullable(String),   -- signed token1 amount × price
      side                LowCardinality(String),   -- buy | sell
      source_kind         LowCardinality(String),   -- aggregator | pool_fill
      protocol            LowCardinality(String),
      sign                Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_swaps', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, pool_address, event_ts, vendor_event_id);

  -- Candle accelerator: one state-row per (chain, pool, hour).
  -- Additive measures are sign-weighted so reorg −1 rows subtract cleanly.
  CREATE TABLE recipe_pair_ohlcv.candles_agg
  (
      chain_id        UInt32,
      pool_address    String,
      bucket_start    DateTime,                       -- toStartOfHour(event_ts)
      open_state      AggregateFunction(argMin, Float64, DateTime64(3)),
      high_state      AggregateFunction(max,    Float64),
      low_state       AggregateFunction(min,    Float64),
      close_state     AggregateFunction(argMax, Float64, DateTime64(3)),
      volume_state    AggregateFunction(sum,    Float64),
      trades_state    AggregateFunction(sum,    Int64)
  )
  ENGINE = ReplicatedAggregatingMergeTree(
      '/clickhouse/tables/{database}/candles_agg', '{replica}')
  PARTITION BY (chain_id, toYYYYMM(bucket_start))
  ORDER BY (chain_id, pool_address, bucket_start);

  -- candles VIEW: finalizes the aggregate state to scalars (the fast surface).
  CREATE VIEW recipe_pair_ohlcv.candles AS
  SELECT
      chain_id,
      pool_address,
      bucket_start,
      argMinMerge(open_state)  AS open,
      maxMerge(high_state)     AS high,
      minMerge(low_state)      AS low,
      argMaxMerge(close_state) AS close,
      sumMerge(volume_state)   AS volume,
      sumMerge(trades_state)   AS trades
  FROM recipe_pair_ohlcv.candles_agg
  GROUP BY chain_id, pool_address, bucket_start
  HAVING trades > 0;

  -- candles_exact VIEW: reorg-EXACT — FINAL collapses each +1/−1 pair before
  -- aggregating, so OHLC reflects only canonical trades. Slower; use after a reorg
  -- may have retracted an hour's all-time high/low.
  CREATE VIEW recipe_pair_ohlcv.candles_exact AS
  SELECT
      chain_id,
      pool_address,
      toStartOfHour(event_ts)                      AS bucket_start,
      argMin(toFloat64OrZero(price_usd), event_ts) AS open,
      max(toFloat64OrZero(price_usd))              AS high,
      min(toFloat64OrZero(price_usd))              AS low,
      argMax(toFloat64OrZero(price_usd), event_ts) AS close,
      sum(abs(toFloat64OrZero(notional_usd)))      AS volume,  -- absolute traded USD
      count()                                      AS trades
  FROM recipe_pair_ohlcv.fact_swaps FINAL
  WHERE price_usd IS NOT NULL AND price_usd != ''
  GROUP BY chain_id, pool_address, bucket_start;
  ```

  The `sign` column on `fact_swaps` drives reorg collapsing. `candles` is the low-latency accelerator; `candles_exact` is always reorg-exact (see fidelity gaps). A single-node setup can use the non-replicated engines (`CollapsingMergeTree(sign)`, `AggregatingMergeTree`) without the replication path.
</Accordion>

<Accordion title="Postgres — swaps + candles">
  ```sql theme={null}
  -- Flat one-row-per-trade landing table (the Swaps by Pair ingest).
  CREATE TABLE public.swaps (
    position           BIGINT      NOT NULL,
    log_index          BIGINT,                 -- NULL for aggregator rows
    transaction_index  BIGINT,
    block_number       BIGINT      NOT NULL,
    block_timestamp    BIGINT      NOT NULL,    -- unix seconds
    tx_hash            TEXT        NOT NULL,
    vendor_event_id    TEXT        NOT NULL,
    trader_address     TEXT        NOT NULL,
    pool_address       TEXT        NOT NULL,    -- pair (pool_fill) or aggregator
    token0_address     TEXT        NOT NULL,
    token1_address     TEXT        NOT NULL,
    amount0            NUMERIC(76, 0)  NOT NULL,
    amount1            NUMERIC(76, 0)  NOT NULL,
    price_usd          NUMERIC(38, 18),
    notional_usd       NUMERIC(38, 18),
    side               TEXT        NOT NULL,
    source_kind        TEXT        NOT NULL,    -- aggregator | pool_fill
    protocol           TEXT        NOT NULL
  );

  -- Candle aggregation reads pool_address + block_timestamp.
  CREATE INDEX swaps_pool_ts_idx ON public.swaps (pool_address, block_timestamp);
  CREATE INDEX swaps_block_idx   ON public.swaps (block_number);

  -- candles: always-fresh 1-hour OHLCV VIEW (the read surface).
  -- Only priced trades participate; open/close use the array_agg-ORDER-BY idiom.
  CREATE VIEW public.candles AS
  SELECT
    pool_address,
    date_trunc('hour', to_timestamp(block_timestamp)) AS bucket_start,
    (array_agg(price_usd ORDER BY block_timestamp ASC,  vendor_event_id ASC))[1]  AS open,
    max(price_usd)                                     AS high,
    min(price_usd)                                     AS low,
    (array_agg(price_usd ORDER BY block_timestamp DESC, vendor_event_id DESC))[1] AS close,
    sum(abs(notional_usd))                             AS volume,  -- absolute traded USD
    count(*)                                           AS trades
  FROM public.swaps
  WHERE price_usd IS NOT NULL
  GROUP BY pool_address, date_trunc('hour', to_timestamp(block_timestamp));

  -- OPTIONAL accelerator: a REFRESHable matview when read-time aggregation gets
  -- expensive. Refresh on a schedule (cron / pg_cron) after the backfill lands.
  -- CREATE MATERIALIZED VIEW public.candles_mat AS
  --   SELECT * FROM public.candles WITH NO DATA;
  -- CREATE UNIQUE INDEX candles_mat_pk ON public.candles_mat (pool_address, bucket_start);
  -- SELECT public.refresh_candles();   -- REFRESH MATERIALIZED VIEW CONCURRENTLY
  ```

  MySQL is the same shape with `DECIMAL(38,18)` for the USD columns and `DECIMAL(76,0)` for raw amounts, and ships the `candles` VIEW only. `position` is the block-level cursor used during backfill. To change the bucket interval, swap `date_trunc('hour', …)` (and the ClickHouse `toStartOfHour` / partition expression) for your target window.
</Accordion>

### Example reads

Newest 24 hourly candles for one pool (ClickHouse, fast accelerator):

```sql theme={null}
SELECT bucket_start, open, high, low, close, volume, trades
FROM recipe_pair_ohlcv.candles
WHERE chain_id = 1
  AND pool_address = lower('0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640')  -- USDC/WETH 0.05% v3
ORDER BY bucket_start DESC
LIMIT 24;
```

Same window, reorg-exact (collapses +1/−1 pairs via `FINAL` before aggregating):

```sql theme={null}
SELECT bucket_start, open, high, low, close, volume, trades
FROM recipe_pair_ohlcv.candles_exact
WHERE chain_id = 1
  AND pool_address = lower('0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640')
ORDER BY bucket_start DESC
LIMIT 24;
```

Sanity-check OHLC ordering across every candle (should return 0):

```sql theme={null}
SELECT count() FROM recipe_pair_ohlcv.candles
WHERE NOT (low <= open AND low <= close AND open <= high AND close <= high
           AND volume > 0 AND trades > 0);
```

On Postgres / MySQL the `candles` VIEW reads the same way, keyed on `pool_address`:

```sql theme={null}
SELECT pool_address, bucket_start, open, high, low, close, volume, trades
FROM candles
WHERE pool_address = lower('0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640')
ORDER BY bucket_start DESC
LIMIT 24;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  **Realtime on Postgres / MySQL is not supported for this shape.** The realtime reorg path needs a single-column unique on the block-level position, but trades are array-expanded (many per block), so these tables can only carry a composite unique. Run realtime/hybrid on ClickHouse, where the collapsing log table corrects reorgs per-block and the candle accelerator is sign-aware. The Postgres/MySQL configs are intended for `historical` backfill — re-run the backfill (and `REFRESH` the candle matview) to pick up corrections.
</Note>

### Multichain

The recipe is chain-parametrized — point it at any supported EVM chain or Solana, and the candle math is chain-agnostic. On Solana, the same `logIndex` can repeat across events in one instruction, so the pool-fill event identity is widened (with `token0Address`, `token1Address`, `token0Amount`) to keep trade rows distinct; the candle surface it produces is identical in shape.

### Fidelity gaps

* **Fixed 1-hour interval (v1).** Moralis' `/pairs/{address}/ohlcv` takes a `timeframe` param (1m/5m/1h/1d/…); this recipe ships a single fixed **1-hour** bucket. For other intervals, change the bucket expression (`toStartOfHour` / `date_trunc('hour', …)` / the MySQL modulus) to your target window.
* **Trade-reconstructed, not exchange-reported.** Candles are built from on-chain swap fills, so they may differ slightly from a DEX's own reported OHLC (which can apply off-chain smoothing or a different price reference). No off-chain smoothing is applied.
* **Price = bought-leg in-block USD; no carry-forward.** A candle only includes trades whose bought-leg token had a same-block `tokenPriceUpdate`. Thin/illiquid pools with no in-block price update in an hour produce **no candle for that hour** (a gap), rather than a flat carry-forward candle. Dense pools (the majority of volume) are unaffected.
* **ClickHouse `candles` high/low under reorg.** The fast accelerator's `high`/`low` are monotonic state functions; a reorg `−1` row cannot retract an extreme, so if a reorg removes an hour's all-time high/low, `candles` may stay slightly wide until the next canonical trade re-establishes the range. Read **`candles_exact`** when post-reorg precision matters. `volume` and `trades` are sign-weighted and always exact on both surfaces.
* **`volume` is absolute traded USD.** `notional_usd` carries the **signed** token1 delta (V3/V4 report signed swap amounts — negative when the token leaves the pool), so `volume` uses `abs(notional_usd)` (×reorg-sign on ClickHouse) — otherwise buy/sell legs cancel and volume goes negative. This is the canonical OHLCV "traded value" definition.
* **Missing-decimals volume outliers.** A handful of exotic tokens arrive with `token1` decimals absent/0 (coalesced to 0 in the shared swap transform); their raw amount isn't decimal-scaled and `notional_usd` is wildly inflated, producing an implausibly large candle `volume`. OHLC prices are unaffected (they use per-unit `price_usd`). Filter `volume < 1e12` for a clean volume distribution; a production deployment should source token decimals from a metadata table rather than the in-event field.

### Related

<Columns cols={2}>
  <Card title="Swaps by Pair" href="/data-feeds/recipes/markets/swaps-by-pair" icon="arrow-right-arrow-left">
    The per-trade ingest these candles aggregate — every fill on a pair.
  </Card>

  <Card title="Trading & Charting" href="/data-feeds/use-cases/trading-charting" icon="chart-candlestick">
    The use case OHLCV candles power.
  </Card>
</Columns>
