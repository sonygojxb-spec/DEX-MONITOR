> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Swaps by Wallet

> Sync every DEX trade made by a wallet — pool fills and aggregator-routed trades, USD-enriched at block time — keyed for by-trader lookups in your own database.

### Question it answers

> "Give me every DEX trade made by wallet **0x…**, newest first — direct pool fills and aggregator-routed trades alike, each with its USD notional, side, and protocol."

A single prefix scan returns what the public Moralis Swaps endpoints serve, pre-shaped and keyed by trader so a wallet's trade history is a contiguous range read.

### What you get

The recipe lands **one row per trade** — a trade belongs to exactly one trader (`fromAddress`), so there's no per-side fan-out. Both direct pool fills and aggregator-routed trades land in the same table:

| Column                               | Description                                                                 |
| ------------------------------------ | --------------------------------------------------------------------------- |
| `trader_address`                     | The wallet that made the trade                                              |
| `event_ts`, `block_number`           | When the trade happened                                                     |
| `tx_hash`                            | Transaction that produced the trade                                         |
| `pool_address`                       | The pair (pool fill) or aggregator (aggregator route)                       |
| `token0_address`, `token1_address`   | The two legs of the trade                                                   |
| `amount0`, `amount1`                 | Raw `uint256` amounts moved on each leg                                     |
| `side`                               | `buy` / `sell` — decided by the base token's pool-balance delta             |
| `source_kind`                        | `pool_fill` (direct pool) or `aggregator` (router)                          |
| `price_usd`                          | Bought-leg (`token1`) USD price at block time                               |
| `notional_usd`                       | Trade value: `token1Amount / 10^token1Decimals × price_usd`                 |
| `protocol`                           | The DEX protocol of the fill                                                |
| `fee_amount`, `fee_token`, `fee_usd` | Pool-fill fees (bps fees converted to absolute), `NULL` for aggregator rows |

### Source

The transform reads two per-block arrays and unions them into the trade feed, so every fill is captured exactly once:

`tokenSwaps` (direct pool fills, `source_kind = 'pool_fill'`) · `aggregateTokenSwaps` (aggregator routes, `source_kind = 'aggregator'`)

The two branches are disjoint by construction. USD enrichment is computed **inline** from the same block's `tokenPriceUpdates` — a per-block price map is built once and the bought leg is priced O(log N) per trade, with no separate price join at read time.

### Destination

| Destination                  | Table                  | Read pattern                                                                            |
| ---------------------------- | ---------------------- | --------------------------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_swaps_by_wallet` | Prefix scan on `(chain_id, trader_address, event_ts)`; read with `FINAL` or `sum(sign)` |
| **Postgres**                 | `swaps`                | Index on `(trader_address, block_number DESC)`                                          |
| **MySQL**                    | `swaps`                | Index on `(trader_address, block_number)`                                               |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct — a trade's `+1/−1` pair shares an identical key and collapses cleanly. The fact table's sort key is trader-first, so a wallet's trade history is a contiguous range read.

### Full schema

Below is the complete read table this recipe produces. It's a starting point — keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). Raw `uint256` amounts are stored as text in ClickHouse (they exceed numeric precision) and as `NUMERIC(76, 0)` in Postgres; USD columns are wide decimals so a low-decimals token × price never overflows.

<Accordion title="ClickHouse — fact_swaps_by_wallet">
  ```sql theme={null}
  CREATE TABLE recipe_swaps_by_wallet.fact_swaps_by_wallet
  (
      vendor_event_id     String,
      ingested_at         DateTime64(3),
      chain_id            UInt32,
      block_hash          String,
      block_number        UInt64,
      event_ts            DateTime64(3),
      trader_address      String,
      pool_address        String,
      token0_address      String,
      token1_address      String,
      amount0             String,                   -- raw uint256
      amount1             String,                   -- raw uint256
      price_usd           Nullable(String),         -- bought-leg (token1) USD price
      notional_usd        Nullable(String),         -- token1 amount × price_usd
      side                LowCardinality(String),   -- buy | sell
      source_kind         LowCardinality(String),   -- aggregator | pool_fill
      protocol            LowCardinality(String),
      fee_amount          Nullable(String),
      fee_token           Nullable(String),
      fee_usd             Nullable(String),
      sign                Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_swaps_by_wallet', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, trader_address, event_ts, vendor_event_id);
  ```

  The `sign` column drives reorg collapsing — read with `FINAL` or `sum(sign)`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
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
    amount0            NUMERIC(76, 0)  NOT NULL,   -- raw uint256
    amount1            NUMERIC(76, 0)  NOT NULL,   -- raw uint256
    price_usd          NUMERIC(38, 18),
    notional_usd       NUMERIC(38, 18),
    side               TEXT        NOT NULL,
    source_kind        TEXT        NOT NULL,    -- aggregator | pool_fill
    protocol           TEXT        NOT NULL,
    fee_amount         NUMERIC(76, 0),
    fee_token          TEXT,
    fee_usd            NUMERIC(38, 18)
  );

  -- By-wallet access (the recipe's primary purpose).
  CREATE INDEX IF NOT EXISTS swaps_trader_block_idx
    ON public.swaps (trader_address, block_number DESC);
  -- By-token access helpers.
  CREATE INDEX IF NOT EXISTS swaps_token0_block_idx
    ON public.swaps (token0_address, block_number DESC);
  CREATE INDEX IF NOT EXISTS swaps_token1_block_idx
    ON public.swaps (token1_address, block_number DESC);
  -- Block-range helper.
  CREATE INDEX IF NOT EXISTS swaps_block_idx
    ON public.swaps (block_number);
  ```

  MySQL is the same shape with `DECIMAL(38,18)` for the USD columns and `DECIMAL(76,0)` for raw amounts. `position` is the block-level cursor used during backfill.
</Accordion>

### Example reads

All trades made by a wallet, newest first (ClickHouse):

```sql theme={null}
SELECT event_ts, side, source_kind, amount0, amount1, notional_usd, protocol
FROM recipe_swaps_by_wallet.fact_swaps_by_wallet FINAL
WHERE chain_id = 1
  AND trader_address = lower('0x28C6c06298d514Db089934071355E5743bf21d60')
ORDER BY event_ts DESC
LIMIT 50;
```

24h USD volume per wallet (sign-aware, cheaper than `FINAL`):

```sql theme={null}
SELECT trader_address,
       sumIf(toFloat64OrZero(notional_usd), sign =  1)
     - sumIf(toFloat64OrZero(notional_usd), sign = -1) AS volume_usd
FROM recipe_swaps_by_wallet.fact_swaps_by_wallet
WHERE chain_id = 1 AND event_ts >= now() - INTERVAL 1 DAY
GROUP BY trader_address
ORDER BY volume_usd DESC
LIMIT 25;
```

The same by-wallet read on Postgres / MySQL:

```sql theme={null}
SELECT block_number, side, source_kind, amount0, amount1, notional_usd, protocol
FROM swaps
WHERE trader_address = lower('0x28C6...')
ORDER BY block_number DESC
LIMIT 50;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  The realtime reorg path needs a single-column unique on the block-level position, but `position` is block-level (many trades share one block), so array-expanded trade rows can only carry a composite unique. Run realtime/hybrid on **ClickHouse**, where the collapsing log table corrects reorgs per-block. The Postgres / MySQL configs are intended for `historical` backfill.
</Note>

### Multichain

The recipe is chain-parametrized — point it at any supported EVM chain or Solana. On Solana, the same `logIndex` can be assigned to multiple events in one instruction, so the pool-fill event identity is widened with `(token0_address, token1_address, token0_amount)` to keep rows distinct; the trade feed it produces is identical in shape.

### Fidelity gaps

* **`notional_usd` is single-leg.** The trade value is computed from the bought leg (`token1`) only — `token1Amount / 10^token1Decimals × price_usd`. If the bought token had no in-block price update, `price_usd`, `notional_usd`, and `fee_usd` are `NULL`.
* **`amount0` / `amount1` are raw `uint256`.** They are not decimal-scaled — divide by `10^token_decimals` (sourced from a Token Metadata sync) to read human amounts.
* **Fees are pool-fill only.** `fee_*` columns are populated for direct pool fills (bps fees converted to an absolute amount); aggregator rows leave them `NULL`.

### Related

<Columns cols={2}>
  <Card title="Swaps by Token" href="/data-feeds/recipes/markets/swaps-by-token" icon="coins">
    The same trade feed keyed by token instead of trader.
  </Card>

  <Card title="Token Analytics" href="/data-feeds/use-cases/token-analytics" icon="chart-line">
    The use case this trade feed powers.
  </Card>
</Columns>
