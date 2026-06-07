> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Prices

> Sync a token's full USD / native mark price history — every in-block price update for each pair and protocol — as a continuous feed into your own database, with a carry-forward latest mark for valuing quiet positions.

### Question it answers

> "Give me the USD / native mark price history for token **0x…**, newest first — and the freshest mark right now so I can value a position that hasn't traded recently."

Token Prices is the **valuation join target** across Data Feeds. Any "what is this worth in USD" question — a transfer's value, a portfolio's worth, a trade's notional — joins a token's mark at a given block from this feed.

### What you get

The recipe lands **one row per in-block price update** — Moralis' continuous mark for each `(token, pair, protocol)` at the block it changed. A token traded across several pairs or protocols produces several marks per block; the table keeps them all, keyed for by-token lookups.

| Column                     | Description                                                      |
| -------------------------- | ---------------------------------------------------------------- |
| `token_address`            | The token the mark prices                                        |
| `pair_address`             | The pair the mark was observed on                                |
| `protocol`                 | The DEX/protocol that produced the mark                          |
| `usd_price`                | USD mark, carried as text for full precision — cast at read time |
| `native_price`             | Native-asset mark (e.g. ETH), text for full precision            |
| `block_number`, `event_ts` | When the mark was set (block height and block time)              |
| `tx_hash`                  | Transaction the price update came from                           |
| `chain_id`                 | Chain the mark belongs to                                        |

On ClickHouse, a companion **`latest_token_price_dict`** dictionary keeps the freshest mark per `(chain_id, token_address)` for O(1) carry-forward valuation of tokens that haven't updated recently.

### Source

The transform reads one per-block array — `tokenPriceUpdates` — and lands one row per entry. Each entry is Moralis' mark for a `(token, pair, protocol)` at that block. There is no read-time join: every mark is already a row keyed by token.

### Destination

| Destination                  | Table                                                   | Read pattern                                                                           |
| ---------------------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_token_price_update` (+ `latest_token_price_dict`) | Prefix scan on `(chain_id, token_address, event_ts)`; read with `FINAL` or `sum(sign)` |
| **Postgres**                 | `token_price_updates`                                   | Index on `(token_address, block_number DESC)`                                          |
| **MySQL**                    | `token_price_updates`                                   | Index on `(token_address, block_number)`                                               |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct. The fact table's sort key is token-first, so a token's full price history is a contiguous range read; the `latest_token_price_dict` dictionary holds the carry-forward mark for quiet positions.

### Full schema

Below is the complete read table this recipe produces. It's a starting point: keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). `usd_price` and `native_price` are carried as text to preserve full precision across many orders of magnitude — cast at read time.

<Accordion title="ClickHouse — fact_token_price_update">
  ```sql theme={null}
  CREATE TABLE recipe_token_price_history.fact_token_price_update
  (
      vendor_event_id     String,
      ingested_at         DateTime64(3),
      chain_id            UInt32,
      block_hash          String,
      block_number        UInt64,
      event_ts            DateTime64(3),
      token_address       String,
      pair_address        String,
      protocol            LowCardinality(String),
      usd_price           String,                   -- toString(usdPrice), cast at read time
      native_price        String,                   -- toString(nativePrice)
      sign                Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_token_price_update', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, token_address, event_ts, vendor_event_id);

  -- OPTIONAL (carry-forward valuation): the freshest USD mark per token, O(1).
  -- Refreshes every 30-60s, so a quiet token carries its last on-chain mark
  -- forward without a new price event. argMax over FINAL/sign=1 is reorg-correct.
  CREATE DICTIONARY recipe_token_price_history.latest_token_price_dict
  (
      chain_id        UInt32,
      token_address   String,
      usd_price       String,
      block_number    UInt64,
      event_ts        DateTime64(3)
  )
  PRIMARY KEY chain_id, token_address
  SOURCE(CLICKHOUSE(
      QUERY $$
          SELECT chain_id, token_address,
                 argMax(usd_price, (block_number, event_ts)) AS usd_price,
                 max(block_number) AS block_number,
                 max(event_ts)     AS event_ts
          FROM recipe_token_price_history.fact_token_price_update FINAL
          WHERE sign = 1
          GROUP BY chain_id, token_address
      $$
  ))
  LAYOUT(COMPLEX_KEY_HASHED())
  LIFETIME(MIN 30 MAX 60);
  ```

  The `sign` column drives reorg collapsing — read with `FINAL` or `sum(sign)`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path. Inside the dictionary the `WHERE sign = 1` is safe (not the bare-`WHERE` anti-pattern) because `FINAL` has already collapsed the ±1 reorg pairs.
</Accordion>

<Accordion title="Postgres — token_price_updates">
  ```sql theme={null}
  CREATE TABLE public.token_price_updates (
    position           BIGINT      NOT NULL,
    log_index          BIGINT,
    transaction_index  BIGINT,
    block_number       BIGINT      NOT NULL,
    block_timestamp    BIGINT      NOT NULL,    -- unix seconds
    tx_hash            TEXT        NOT NULL,
    vendor_event_id    TEXT        NOT NULL,
    token_address      TEXT        NOT NULL,
    pair_address       TEXT        NOT NULL,
    protocol           TEXT        NOT NULL,
    usd_price          NUMERIC(38, 18),
    native_price       NUMERIC(38, 18)
  );

  -- By-token price history (the recipe's primary purpose).
  CREATE INDEX ON public.token_price_updates (token_address, block_number DESC);
  -- Block-range helper.
  CREATE INDEX ON public.token_price_updates (block_number);
  ```

  MySQL is the same shape with `DECIMAL(38,18)` for the price columns. `position` is the block-level cursor used during backfill. The explicit `NUMERIC(38,18)` precision keeps room for marks that span many orders of magnitude.
</Accordion>

### Example reads

A token's price history, newest first (ClickHouse):

```sql theme={null}
SELECT event_ts, usd_price, native_price, pair_address, protocol
FROM recipe_token_price_history.fact_token_price_update FINAL
WHERE chain_id = 1
  AND token_address = lower('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
ORDER BY event_ts DESC
LIMIT 50;
```

The latest carry-forward mark via the dictionary (O(1), refreshes every 30–60s):

```sql theme={null}
SELECT dictGetOrDefault(
         'recipe_token_price_history.latest_token_price_dict', 'usd_price',
         tuple(1, lower('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')), '0'
       ) AS usd_price;
```

Hourly close per token (last mark in each hour bucket, sign-aware):

```sql theme={null}
SELECT toStartOfHour(event_ts) AS hour,
       argMax(usd_price, (block_number, event_ts)) AS close_usd
FROM recipe_token_price_history.fact_token_price_update
WHERE chain_id = 1
  AND token_address = lower('0xA0b8…')
  AND sign = 1
GROUP BY hour
ORDER BY hour DESC
LIMIT 24;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  The realtime reorg path needs a single-column `UNIQUE` on the position column, but `position` is block-level — many price updates share one block — so the array-expanded rows can only carry a composite unique. Run realtime/hybrid on **ClickHouse**, where the collapsing log table corrects reorgs per-block. The Postgres / MySQL configs are intended for `historical` backfill.
</Note>

### Multichain

The recipe is chain-parametrized via the `chain` setting — point it at any supported EVM chain or Solana. On Solana, the same `logIndex` can be assigned to multiple events in one instruction, so the event identity is widened with `pairAddress` (or `protocol`) to keep marks distinct; the price feed it produces is identical in shape.

### Fidelity and valuation notes

* **Precision.** `usd_price` and `native_price` are carried as strings end-to-end to preserve full precision; cast at read time (`toDecimal*` on ClickHouse, the `NUMERIC` / `DECIMAL` columns on Postgres / MySQL).
* **Multiple marks per block.** A token priced on several pairs/protocols lands one row per `(pair, protocol)` per block. Pick a venue (filter `pair_address` / `protocol`) or aggregate (`argMax`) depending on whether you want a specific venue's mark or a representative one.
* **Carry-forward staleness.** The `latest_token_price_dict` refreshes every 30–60s, so a quiet token's mark is at most \~a minute stale without needing a fresh price event — but it does not interpolate between updates.

### Related

<Columns cols={2}>
  <Card title="Token Transfers" href="/data-feeds/recipes/token/token-transfers" icon="right-left">
    The per-token transfer ledger you value against these marks.
  </Card>

  <Card title="Portfolio Tracking" href="/data-feeds/use-cases/portfolio-tracking" icon="chart-pie">
    Token Prices is the valuation join target behind portfolio worth.
  </Card>
</Columns>
