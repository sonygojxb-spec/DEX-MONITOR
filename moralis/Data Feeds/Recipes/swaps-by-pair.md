> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Swaps by Pair

> Sync every DEX trade on a pool/pair — direct pool fills and aggregator-routed trades, USD-enriched in-block — keyed by pool address so a pair's trade feed is a prefix scan, into your own database.

### Question it answers

> "Give me every DEX trade on pool/pair **0x…**, newest first — each row is one trade with both token legs, the side, the protocol, and a USD notional."

Same trade projection as [Swaps by Token](/data-feeds/recipes/markets/swaps-by-token), but keyed by the **pool/pair address** with **one row per trade** (no per-token-side unpivot). `pool_address` is the **pair address** for direct pool fills and the **aggregator address** for aggregator-routed trades.

### What you get

One row per trade, keyed by `pool_address`:

| Column                                                   | Description                                                                |
| -------------------------------------------------------- | -------------------------------------------------------------------------- |
| `pool_address`                                           | Pair address (pool fills) or aggregator address (aggregator-routed trades) |
| `token0_address`, `token1_address`                       | The pair's two tokens                                                      |
| `amount0`, `amount1`                                     | Raw token-unit deltas for each leg (`uint256` as text)                     |
| `side`                                                   | `buy` · `sell` — derived from the base token's pool-balance delta          |
| `source_kind`                                            | `pool_fill` (direct pool) · `aggregator` (aggregator-routed)               |
| `price_usd`                                              | Bought-leg (`token1`) USD price; `NULL` with no in-block price update      |
| `notional_usd`                                           | `token1Amount / 10^token1Decimals × price_usd`; `NULL` if unpriced         |
| `protocol`                                               | DEX/protocol identifier                                                    |
| `fee_amount`, `fee_token`, `fee_usd`                     | Trade fee — pool fills only (`NULL` on aggregator rows)                    |
| `trader_address`                                         | The trading wallet                                                         |
| `block_number`, `event_ts`, `tx_hash`, `vendor_event_id` | On-chain ordering and identity                                             |

### Source

The transform reads two per-block trade arrays and projects them into one feed:

`tokenSwaps` (direct pool fills, `source_kind='pool_fill'`, `pool_address = pairAddress`) · `aggregateTokenSwaps` (aggregator-routed trades, `source_kind='aggregator'`, `pool_address = aggregatorAddress`)

The two branches are disjoint by construction — together they give every fill exactly once. USD values are computed **inline** from the same block's `tokenPriceUpdates` (the chronologically-last update wins on duplicate keys) — no separate price join at read time.

### Destination

| Destination                  | Table                | By-pair access                                                                           |
| ---------------------------- | -------------------- | ---------------------------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_swaps_by_pair` | Prefix scan on `(chain_id, pool_address, event_ts, …)`; read with `FINAL` or `sum(sign)` |
| **Postgres**                 | `swaps`              | Index lead `(pool_address, block_number DESC)`                                           |
| **MySQL**                    | `swaps`              | Index lead `(pool_address, block_number)`                                                |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct — the `+1/−1` reorg pair for a trade shares an identical key and collapses cleanly. The fact table's sort key is pool-first, so a pair's full trade feed is a contiguous range read.

### Full schema

The complete read table this recipe produces — one row per trade. Keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). Raw `uint256` amounts are stored as text in ClickHouse (they exceed numeric precision); USD columns are nullable so an unpriced token leaves them empty.

<Accordion title="ClickHouse — fact_swaps_by_pair">
  ```sql theme={null}
  CREATE TABLE recipe_swaps_by_pair.fact_swaps_by_pair
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
      price_usd           Nullable(String),
      notional_usd        Nullable(String),
      side                LowCardinality(String),   -- buy | sell
      source_kind         LowCardinality(String),   -- aggregator | pool_fill
      protocol            LowCardinality(String),
      fee_amount          Nullable(String),
      fee_token           Nullable(String),
      fee_usd             Nullable(String),
      sign                Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_swaps_by_pair', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, pool_address, event_ts, vendor_event_id);
  ```

  The `sign` column drives reorg collapsing — read with `FINAL` or `sum(sign)`, never a bare `WHERE sign=1`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
</Accordion>

<Accordion title="Postgres — swaps">
  ```sql theme={null}
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
    protocol           TEXT        NOT NULL,
    fee_amount         NUMERIC(76, 0),
    fee_token          TEXT,
    fee_usd            NUMERIC(38, 18)
  );

  -- By-pair access (the recipe's primary purpose).
  CREATE INDEX IF NOT EXISTS swaps_pool_block_idx
    ON public.swaps (pool_address, block_number DESC);
  -- Token + trader + block-range helpers.
  CREATE INDEX IF NOT EXISTS swaps_token0_block_idx
    ON public.swaps (token0_address, block_number DESC);
  CREATE INDEX IF NOT EXISTS swaps_token1_block_idx
    ON public.swaps (token1_address, block_number DESC);
  CREATE INDEX IF NOT EXISTS swaps_trader_block_idx
    ON public.swaps (trader_address, block_number DESC);
  CREATE INDEX IF NOT EXISTS swaps_block_idx
    ON public.swaps (block_number);
  ```

  MySQL is the same shape with `DECIMAL(38,18)` for the USD columns. Amounts use `NUMERIC(76,0)` so large raw `uint256` balances never overflow. `position` is the block-level cursor used during backfill.
</Accordion>

### Example reads

All trades on a pool/pair, newest first (ClickHouse):

```sql theme={null}
SELECT event_ts, side, source_kind, token0_address, token1_address,
       amount0, amount1, notional_usd, protocol
FROM recipe_swaps_by_pair.fact_swaps_by_pair FINAL
WHERE chain_id = 1
  AND pool_address = lower('0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640')
ORDER BY event_ts DESC
LIMIT 50;
```

24h USD volume per pool (sign-aware, cheaper than `FINAL`):

```sql theme={null}
SELECT pool_address,
       sumIf(toFloat64OrZero(notional_usd), sign =  1)
     - sumIf(toFloat64OrZero(notional_usd), sign = -1) AS volume_usd
FROM recipe_swaps_by_pair.fact_swaps_by_pair
WHERE chain_id = 1 AND event_ts >= now() - INTERVAL 1 DAY
GROUP BY pool_address
ORDER BY volume_usd DESC
LIMIT 25;
```

Postgres / MySQL:

```sql theme={null}
SELECT block_number, side, source_kind, token0_address, token1_address,
       amount0, amount1, notional_usd, protocol
FROM swaps
WHERE pool_address = lower('0x88e6...')
ORDER BY block_number DESC
LIMIT 50;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  The realtime reorg path needs a single-column `UNIQUE` on the position column, but `position` is block-level (many trades per block), so array-expanded trade rows can only carry a composite unique. Run realtime/hybrid on **ClickHouse** (the log table corrects reorgs per-block via the collapsing companion table); the Postgres / MySQL configs are intended for `historical` backfill.
</Note>

### Multichain

The recipe is chain-parametrized — point it at any supported EVM chain or Solana. On Solana, the same `logIndex` can be assigned to multiple events in one instruction, so for production the pool-fill event identity is widened with `(token0_address, token1_address, token0_amount)` to keep rows distinct; the trade feed it produces is identical in shape.

### Fidelity gaps

* **`price_usd` / `notional_usd` / `fee_usd` are `NULL`** when the relevant token had no in-block `tokenPriceUpdate` (illiquid or brand-new tokens). The recipe enriches only from same-block price updates — there is no cross-block carry-forward.
* **`fee_*` is populated for pool fills only.** Aggregator-routed trades carry no per-fill fee, so `fee_amount` / `fee_token` / `fee_usd` are `NULL` on `source_kind='aggregator'` rows.
* **One trade can appear under two `pool_address` values** when it is observed both as a direct pool fill (the pair address) and as part of an aggregator route (the aggregator address). These are distinct events with distinct `vendor_event_id`s by design — the two source arrays are disjoint per event.

### Related

<Columns cols={2}>
  <Card title="Swaps by Token" href="/data-feeds/recipes/markets/swaps-by-token" icon="coins">
    The same trade projection, keyed by token with one row per token side.
  </Card>

  <Card title="Pair OHLCV" href="/data-feeds/recipes/markets/pair-ohlcv" icon="chart-candlestick">
    Roll a pair's trades into candlesticks for charting.
  </Card>

  <Card title="Trading & Charting" href="/data-feeds/use-cases/trading-charting" icon="chart-line">
    The use case this per-pair trade feed powers.
  </Card>

  <Card title="Token Analytics" href="/data-feeds/use-cases/token-analytics" icon="chart-mixed">
    Pool-level volume and trade flow for token analytics.
  </Card>
</Columns>
