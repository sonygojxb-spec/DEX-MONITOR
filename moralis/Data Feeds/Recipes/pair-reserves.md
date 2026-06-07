> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Pair Reserves

> Sync the current reserve0 / reserve1 of any DEX pair — the pool's absolute token balances, kept latest-wins per pair — into your own database. Mirrors the Moralis GET /{pair_address}/reserves endpoint.

### Question it answers

> "What are the current `reserve0` / `reserve1` of DEX pair **0x…**?"

Mirrors Moralis `GET /{pair_address}/reserves` → `{ reserve0, reserve1 }`. The recipe lands the pool's absolute token balances and keeps the **latest observation per pair**, so a single read returns each pair's current reserves.

### What you get

The recipe lands **one observation per swap** — the pool's absolute token balances captured *after* each trade — and the current reserves of a pair are the highest-`(block_number, log_index)` observation for that pair:

| Column                             | Description                                                              |
| ---------------------------------- | ------------------------------------------------------------------------ |
| `pair_address`                     | The DEX pair (pool) the reserves belong to                               |
| `token0_address`, `token1_address` | The pool's two token sides                                               |
| `reserve0`                         | Pool's absolute `token0` balance after the swap (raw `uint256`, as text) |
| `reserve1`                         | Pool's absolute `token1` balance after the swap (raw `uint256`, as text) |
| `block_number`, `log_index`        | Recency key — the latest pair wins                                       |
| `event_ts` / `block_timestamp`     | Block time of the observation                                            |

These are **absolute snapshots, not deltas** — no running sum, no pre-window baseline, no genesis requirement. The latest snapshot in any window is the answer (**window-safe**).

### Source

The faithful source for reserves is `tokenSwaps`. Each swap carries `token0PostBalance` / `token1PostBalance` — the pool's absolute balances after the trade — which are exactly the pair's reserves. The transform projects one reserve observation per swap, keyed by pair.

`pairLiquidityChanges` is **not** used: it only fires on add/remove liquidity, so a running sum of its deltas misses all swap-driven reserve movement and is window-relative. Aggregated swaps are also not used — they carry an aggregator address, not a `pair_address`, so their post-balances can't be attributed to a specific pool.

### Destination

| Destination                  | Table                                                                 | By-pair access                                                      |
| ---------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_pair_reserves`                                                  | `argMax(reserveN, (block_number, log_index))` per pair over `FINAL` |
| **Postgres**                 | `pair_reserves` (materialized view over `pair_reserve_observations`)  | Unique index `(pair_address)`                                       |
| **MySQL**                    | `pair_reserves` (trigger-maintained over `pair_reserve_observations`) | Primary key `(pair_address)`                                        |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct: a reorg negates the rolled-back block's observations (`sign = -1`) and re-emits the corrected ones. Read with `FINAL` to collapse the `±1` pair, then `argMax` to pick the latest observation — never a bare `WHERE sign = 1`.

Postgres and MySQL append append-only observations and derive a **latest-wins** current-reserves surface per pair: Postgres via a `DISTINCT ON (pair_address) … ORDER BY block_number DESC, log_index DESC` materialized view, MySQL via an `AFTER INSERT` upsert trigger.

### Full schema

The ClickHouse fact table is the per-pair observation table; the current reserves are an `argMax` over it. Reserves are raw `uint256` stored as text (matching the API's string reserves) — `argMax` over text ordered by the numeric recency key is exact. Keep the columns you need (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)).

<Accordion title="ClickHouse — fact_pair_reserves">
  ```sql theme={null}
  CREATE TABLE recipe_pair_reserves.fact_pair_reserves
  (
      vendor_event_id   String,
      ingested_at       DateTime64(3),
      chain_id          UInt32,
      block_hash        String,
      block_number      UInt64,
      log_index         UInt32,
      event_ts          DateTime64(3),
      pair_address      String,
      token0_address    String,
      token1_address    String,
      reserve0          String,          -- absolute pool reserve0 after this swap
      reserve1          String,
      sign              Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_pair_reserves', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, pair_address, block_number, log_index, vendor_event_id);
  ```

  The `sign` column drives reorg collapsing — read with `FINAL` then `argMax`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
</Accordion>

<Accordion title="Postgres — pair_reserves">
  ```sql theme={null}
  -- 1. Observations (sink target): one raw row per swap.
  CREATE TABLE public.pair_reserve_observations (
    position         BIGINT  NOT NULL,
    log_index        BIGINT  NOT NULL,
    block_number     BIGINT  NOT NULL,
    block_timestamp  BIGINT  NOT NULL,         -- unix seconds
    pair_address     TEXT    NOT NULL,
    token0_address   TEXT    NOT NULL,
    token1_address   TEXT    NOT NULL,
    reserve0         NUMERIC(76, 0) NOT NULL,  -- absolute pool reserve0 post-swap
    reserve1         NUMERIC(76, 0) NOT NULL,
    vendor_event_id  TEXT    NOT NULL
  );

  -- Speeds the DISTINCT ON (latest-per-pair) the materialized view computes.
  CREATE INDEX IF NOT EXISTS pro_pair_recency_idx
    ON public.pair_reserve_observations
    (pair_address, block_number DESC, log_index DESC);

  -- 2. Current-reserves materialized view: latest observation per pair.
  CREATE MATERIALIZED VIEW public.pair_reserves AS
  SELECT DISTINCT ON (pair_address)
    pair_address,
    token0_address,
    token1_address,
    reserve0,
    reserve1,
    block_number,
    log_index,
    block_timestamp
  FROM public.pair_reserve_observations
  ORDER BY pair_address, block_number DESC, log_index DESC;

  -- Required by REFRESH MATERIALIZED VIEW CONCURRENTLY and the by-pair lookup.
  CREATE UNIQUE INDEX IF NOT EXISTS pair_reserves_pk
    ON public.pair_reserves (pair_address);
  ```

  MySQL is the same shape: an append-only `pair_reserve_observations` table plus a `pair_reserves` table kept current by an `AFTER INSERT` latest-wins upsert trigger, with `reserve0` / `reserve1` as `DECIMAL(65,0)`. `position` is the block-level cursor used during backfill.
</Accordion>

### Example reads

Current reserves of a pair — latest observation; `FINAL` collapses reorg `±1` pairs before `argMax` (ClickHouse):

```sql theme={null}
SELECT pair_address,
       argMax(token0_address, (block_number, log_index)) AS token0,
       argMax(token1_address, (block_number, log_index)) AS token1,
       argMax(reserve0, (block_number, log_index))       AS reserve0,
       argMax(reserve1, (block_number, log_index))       AS reserve1
FROM recipe_pair_reserves.fact_pair_reserves FINAL
WHERE chain_id = 1 AND pair_address = lower('0x...')
GROUP BY pair_address;
```

Largest pools by latest `reserve0` (ClickHouse):

```sql theme={null}
SELECT pair_address,
       argMax(reserve0, (block_number, log_index)) AS reserve0
FROM recipe_pair_reserves.fact_pair_reserves FINAL
WHERE chain_id = 1
GROUP BY pair_address
ORDER BY toFloat64OrZero(reserve0) DESC
LIMIT 100;
```

Postgres — refresh the view, then look up the pair:

```sql theme={null}
REFRESH MATERIALIZED VIEW CONCURRENTLY pair_reserves;

SELECT reserve0, reserve1 FROM public.pair_reserves
WHERE pair_address = lower('0x...');
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  The Postgres / MySQL realtime reorg path needs a single-column `UNIQUE` on the position column, but `position` is block-level. Run **realtime / hybrid on ClickHouse** (the collapsing log table corrects reorgs per block); the Postgres / MySQL configs target `historical` backfill and re-derive their current-reserves surface on refresh.
</Note>

### Multichain

The recipe is chain-parametrized via the `chain` setting — point it at any supported EVM chain or Solana. On Solana, the event identity already folds in `(pair_address, token0PostBalance, token1PostBalance)` on top of `(transaction_hash, log_index)`, so it stays row-unique despite Solana's repeated log indices within an instruction.

### Fidelity gaps

* **Only pairs with a swap in-window get current reserves.** Reserves are read from swap post-balances, so a pair appears only if it had at least one swap with resolved post-balances in the ingested window. A pool that is quiet (no swaps) for the whole window won't be present — but quiet pools have unchanged reserves by definition, so widening the window picks them up.
* **Swaps without resolved post-balances are skipped.** `token0PostBalance` / `token1PostBalance` are nullable; rows where either is null/empty, or where the swap has no pair address, are filtered out.
* **V4 pair addresses** arrive as `poolId_0xaddress` (\~109 chars) and are stored **raw** for a key that's consistent across destinations. MySQL caps `pair_address` at `VARCHAR(160)`; Postgres `TEXT` and ClickHouse `String` are unbounded.
* **MySQL precision ceiling.** MySQL `DECIMAL(65,0)` cannot represent a full 78-digit `uint256` — though no real reserve approaches that magnitude. Postgres (`NUMERIC(76,0)`) and ClickHouse (`String`) carry the larger range.

### Related

<Columns cols={2}>
  <Card title="Swaps by Pair" href="/data-feeds/recipes/markets/swaps-by-pair" icon="arrow-right-arrow-left">
    Every DEX trade for a pair — the same swap stream these reserves derive from.
  </Card>

  <Card title="Pair OHLCV" href="/data-feeds/recipes/markets/pair-ohlcv" icon="chart-candlestick">
    Per-pair price candles for charting.
  </Card>
</Columns>
