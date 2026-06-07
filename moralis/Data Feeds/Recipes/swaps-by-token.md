> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Swaps by Token

> Sync every DEX trade that touched a token — pool fills and aggregator-routed trades, USD-enriched at block time — into your own database, keyed for fast by-token lookups.

### Question it answers

> "Give me every DEX trade that touched token **0x…**, newest first — with the amount on each side, the USD notional, the protocol, and whether it was a buy or a sell."

A single read returns what the public Moralis Swaps endpoints serve by token, stored **pre-shaped and indexed by token** in your own database. Both direct pool fills and aggregator-routed trades are captured, so you see every fill of the token once.

### What you get

The recipe lands **one row per (trade, token side)** — each trade is unpivoted so it appears under both of its tokens, and a by-token lookup is a prefix scan. Key columns of the fact table:

| Column                                | Description                                                           |
| ------------------------------------- | --------------------------------------------------------------------- |
| `token_address`                       | This side's token (the leg you're querying by)                        |
| `counter_token_address`               | The other token in the trade                                          |
| `leg`                                 | `token0` or `token1` — which side of the underlying trade this row is |
| `side`                                | `buy` or `sell` — derived from the base token's pool-balance delta    |
| `side_amount`                         | Raw amount of `token_address` (uint256, as text)                      |
| `counter_amount`                      | Raw amount of `counter_token_address`                                 |
| `notional_usd`                        | Trade notional in USD (bought-leg amount × in-block price)            |
| `price_usd`                           | Bought-leg (token1) USD price used for the notional                   |
| `source_kind`                         | `pool_fill` (direct pool) or `aggregator` (aggregator-routed)         |
| `protocol`                            | DEX/protocol label                                                    |
| `fee_amount`, `fee_token`, `fee_usd`  | Trade fee (pool fills only)                                           |
| `trader_address`, `pool_address`      | Trader and pool/aggregator address                                    |
| `block_number`, `event_ts`, `tx_hash` | On-chain ordering and time                                            |

### Source

The transform reads two per-block trade arrays and unions them into the trade feed:

`tokenSwaps` (direct pool fills) · `aggregateTokenSwaps` (aggregator-routed trades)

The two branches are disjoint by construction — pool fills are keyed off the pair address, aggregator routes off the aggregator address — so together they give every fill exactly once. USD values are computed **inline** from the same block's `tokenPriceUpdates` (the chronologically-last update wins on duplicate keys), so no separate price join is needed at read time.

### Destination

| Destination                  | Table                 | Read pattern                                                                           |
| ---------------------------- | --------------------- | -------------------------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_swaps_by_token` | Prefix scan on `(chain_id, token_address, event_ts)`; read with `FINAL` or `sum(sign)` |
| **Postgres**                 | `swaps`               | Indexes on `token0_address` and `token1_address`, each `(…, block_number DESC)`        |
| **MySQL**                    | `swaps`               | Indexes on `token0_address` and `token1_address`                                       |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct. The fact table is token-first, so all trades for a token — newest first — are a contiguous range read. Postgres/MySQL keep a flat one-row-per-trade `swaps` table and reach a token via either side's index.

### Full schema

Below is the complete read table this recipe produces. It's a starting point: keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). Raw `uint256` amounts and fees are stored as text in ClickHouse and as `NUMERIC(76, 0)` in Postgres (explicit precision so large raw balances never overflow); USD columns are nullable wide decimals.

<Accordion title="ClickHouse — fact_swaps_by_token">
  ```sql theme={null}
  CREATE TABLE recipe_swaps_by_token.fact_swaps_by_token
  (
      vendor_event_id         String,
      ingested_at             DateTime64(3),
      chain_id                UInt32,
      block_hash              String,
      block_number            UInt64,
      event_ts                DateTime64(3),
      token_address           String,        -- this side's token (token0 or token1)
      counter_token_address   String,
      leg                     LowCardinality(String),  -- 'token0' | 'token1'
      side_amount             String,        -- this token's amount (raw uint256)
      counter_amount          String,
      trader_address          String,
      pool_address            String,
      price_usd               Nullable(String),
      notional_usd            Nullable(String),
      side                    LowCardinality(String),  -- buy | sell
      source_kind             LowCardinality(String),  -- aggregator | pool_fill
      protocol                LowCardinality(String),
      fee_amount              Nullable(String),
      fee_token               Nullable(String),
      fee_usd                 Nullable(String),
      sign                    Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_swaps_by_token', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, token_address, event_ts, vendor_event_id, leg);
  ```

  Each trade is unpivoted into two rows (`leg = 'token0'` and `'token1'`) so it's found under both tokens. `leg` is part of the `ORDER BY` so the two sides never collapse into each other, while the `+1/−1` reorg pair for one side shares an identical key and collapses cleanly. Read with `FINAL` or `sum(sign)` — never a bare `WHERE sign = 1`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
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
    pool_address       TEXT        NOT NULL,
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

  -- By-token access (the recipe's primary purpose).
  CREATE INDEX IF NOT EXISTS swaps_token0_block_idx
    ON public.swaps (token0_address, block_number DESC);
  CREATE INDEX IF NOT EXISTS swaps_token1_block_idx
    ON public.swaps (token1_address, block_number DESC);
  -- Trader + block-range helpers.
  CREATE INDEX IF NOT EXISTS swaps_trader_block_idx
    ON public.swaps (trader_address, block_number DESC);
  CREATE INDEX IF NOT EXISTS swaps_block_idx
    ON public.swaps (block_number);
  ```

  MySQL is the same shape with `DECIMAL(38,18)` for the USD columns. The Postgres/MySQL table is one row per trade (not unpivoted), so a by-token read filters either `token0_address` or `token1_address`. `position` is the block-level cursor used during backfill.
</Accordion>

### Example reads

All trades touching a token, newest first (ClickHouse):

```sql theme={null}
SELECT event_ts, leg, side, side_amount, counter_amount,
       notional_usd, protocol, source_kind
FROM recipe_swaps_by_token.fact_swaps_by_token FINAL
WHERE chain_id = 1
  AND token_address = lower('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
ORDER BY event_ts DESC
LIMIT 50;
```

24h USD volume per token (sign-aware, cheaper than `FINAL`):

```sql theme={null}
SELECT token_address,
       sumIf(toFloat64OrZero(notional_usd), sign =  1)
     - sumIf(toFloat64OrZero(notional_usd), sign = -1) AS volume_usd
FROM recipe_swaps_by_token.fact_swaps_by_token
WHERE chain_id = 1 AND event_ts >= now() - INTERVAL 1 DAY
GROUP BY token_address
ORDER BY volume_usd DESC
LIMIT 25;
```

By-token read on Postgres / MySQL (either side matches):

```sql theme={null}
SELECT block_number, side, source_kind, amount0, amount1, notional_usd, protocol
FROM swaps
WHERE token0_address = lower('0xA0b8...') OR token1_address = lower('0xA0b8...')
ORDER BY block_number DESC
LIMIT 50;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  The realtime reorg path needs a single-column unique on the position cursor, but `position` is block-level (many trades per block), so the array-expanded trade rows can only carry a composite unique. Run **realtime/hybrid on ClickHouse**, where the collapsing log table corrects reorgs per-block; the Postgres/MySQL configs are intended for `historical` backfill.
</Note>

### Multichain

The recipe is chain-parametrized — point it at any supported EVM chain or Solana. On Solana, multiple events in one instruction can share a `logIndex`, so the pool-fill event identity is widened (with the token addresses and amount) to keep rows distinct; the by-token feed it produces is identical in shape.

### USD valuation and fidelity gaps

* **`notional_usd`** is the bought-leg (`token1`) amount scaled by its decimals × the in-block price (`token1Amount / 10^token1Decimals × price`), so it's a true dollar value when the token had an in-block price update.
* **`price_usd`, `notional_usd`, `fee_usd`** are `NULL` when the bought token had **no in-block price update** — there's no off-block price backfill at write time. Join the Token Prices sync for fuller coverage.
* **`fee_*`** is populated for **pool fills only**; bps-style fees (V3/V4/CL) are converted to an absolute amount, and already-absolute fees pass through. Aggregator-routed rows leave fees `NULL`.
* **`side`** (`buy`/`sell`) is derived from the lower-priority (base) token's pool-balance delta on the trade.

### Related

<Columns cols={2}>
  <Card title="Swaps by Pair" href="/data-feeds/recipes/markets/swaps-by-pair" icon="arrow-right-arrow-left">
    The sibling — every trade keyed by pool/pair address.
  </Card>

  <Card title="Token Analytics" href="/data-feeds/use-cases/token-analytics" icon="chart-mixed">
    The use case this by-token trade feed powers.
  </Card>
</Columns>
