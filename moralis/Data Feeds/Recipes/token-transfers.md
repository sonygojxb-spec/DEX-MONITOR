> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Transfers

> Sync every ERC-20 token transfer — by token or by wallet — as a flat, ordered event log into your own database.

### Question it answers

> "Give me every ERC-20 transfer — all transfers of token **0x…**, or every transfer wallet **0x…** sent or received."

One flat event log of token transfers, served two ways from a single sync: **by-token** (every movement of a given token) and **by-wallet** (every transfer a wallet was on either side of). Each row is one transfer carrying exactly one token and one amount — there's no USD enrichment, because a transfer event carries no price.

### What you get

One row per transfer, from Moralis-indexed, normalized per-block onchain data:

| Column                                           | Description                                      |
| ------------------------------------------------ | ------------------------------------------------ |
| `token_address`                                  | The transferred token's contract                 |
| `from_address`, `to_address`                     | Sender and recipient                             |
| `amount`                                         | Raw `uint256` token units (not decimal-adjusted) |
| `transfer_type`                                  | Transfer kind as emitted (`erc20`, …)            |
| `initiated_by`                                   | Address that initiated the transfer              |
| `block_number`, `log_index`, `transaction_index` | On-chain ordering tuple                          |
| `tx_hash`                                        | Transaction that produced the transfer           |
| `block_timestamp` / `event_ts`                   | Block time                                       |

### Source

The transform reads a single per-block array — `tokenTransfers` — and lands one row per transfer. Fields map straight from the source struct (`tokenAddress → token_address`, `fromAddress → from_address`, `toAddress → to_address`, `amount → amount`, `type → transfer_type`, `initiatedBy → initiated_by`).

There's no price join: transfers are unpriced, so there is no `amount_usd` column. The per-transfer `vendor_event_id` is widened beyond `(tx_hash, log_index)` so the id stays unique on Solana, where `logIndex` is not row-unique within an instruction (see [Multichain](#multichain)).

### Destination

| Destination                  | Table                  | Read pattern                                                                                                                                                                        |
| ---------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_token_transfers` | Prefix scan on `(chain_id, token_address, block_number)` for by-token; `bloom_filter` skip-indexes on `from_address` / `to_address` for by-wallet; read with `FINAL` or `sum(sign)` |
| **Postgres**                 | `token_transfers`      | Index on `(token_address, block_number DESC)`; plus `(from_address, …)` and `(to_address, …)`                                                                                       |
| **MySQL**                    | `token_transfers`      | Index on `(token_address, block_number)`; plus `(from_address, …)` and `(to_address, …)`                                                                                            |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct: the `+1/−1` reorg pair for a row shares an identical key and collapses on merge. The fact table's sort key is token-first, so all transfers of a token are a contiguous range read; by-wallet reads are accelerated by data-skipping bloom filters rather than a second sort key.

### Full schema

Below is the complete read table this recipe produces. It's a starting point — keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). `amount` is stored raw (`uint256` token units) because the transfer event carries no decimals; scale by `10^token_decimals` at read time.

<Accordion title="ClickHouse — fact_token_transfers">
  ```sql theme={null}
  CREATE TABLE recipe_token_transfers.fact_token_transfers
  (
      vendor_event_id     String,
      ingested_at         DateTime64(3),
      chain_id            UInt32,
      block_hash          String,
      block_number        UInt64,
      event_ts            DateTime64(3),
      token_address       String,
      from_address        String,
      to_address          String,
      amount              String,        -- raw uint256 token units
      transfer_type       LowCardinality(String),
      initiated_by        String,
      tx_hash             String,
      log_index           Nullable(UInt32),
      transaction_index   Nullable(Int32),
      sign                Int8,
      -- by-wallet skip indexes: prune granules that cannot contain the wallet.
      INDEX bf_from from_address TYPE bloom_filter(0.01) GRANULARITY 4,
      INDEX bf_to   to_address   TYPE bloom_filter(0.01) GRANULARITY 4
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_token_transfers', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, token_address, block_number, vendor_event_id);
  ```

  The `sign` column drives reorg collapsing — read with `FINAL` or `sum(sign)`, never a bare `WHERE sign = 1`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
</Accordion>

<Accordion title="Postgres — token_transfers">
  ```sql theme={null}
  CREATE TABLE public.token_transfers (
    position           BIGINT      NOT NULL,
    log_index          BIGINT,
    transaction_index  BIGINT,
    block_number       BIGINT      NOT NULL,
    block_timestamp    BIGINT      NOT NULL,    -- unix seconds
    tx_hash            TEXT        NOT NULL,
    vendor_event_id    TEXT        NOT NULL,
    token_address      TEXT        NOT NULL,
    from_address       TEXT        NOT NULL,
    to_address         TEXT        NOT NULL,
    amount             NUMERIC(76, 0)  NOT NULL,   -- raw uint256 token units
    transfer_type      TEXT        NOT NULL,
    initiated_by       TEXT        NOT NULL
  );

  -- By-token access (the recipe's primary purpose).
  CREATE INDEX IF NOT EXISTS token_transfers_token_block_idx
    ON public.token_transfers (token_address, block_number DESC);
  -- By-wallet access (either side).
  CREATE INDEX IF NOT EXISTS token_transfers_from_block_idx
    ON public.token_transfers (from_address, block_number DESC);
  CREATE INDEX IF NOT EXISTS token_transfers_to_block_idx
    ON public.token_transfers (to_address, block_number DESC);
  -- Block-range helper.
  CREATE INDEX IF NOT EXISTS token_transfers_block_idx
    ON public.token_transfers (block_number);
  ```

  MySQL is the same shape with the same indexes. `amount` uses `NUMERIC(76, 0)` so large raw `uint256` values don't overflow; `position` is the block-level cursor used during backfill.
</Accordion>

### Example reads

All transfers of a token, newest first (ClickHouse):

```sql theme={null}
SELECT block_number, from_address, to_address, amount, transfer_type, tx_hash
FROM recipe_token_transfers.fact_token_transfers FINAL
WHERE chain_id = 1
  AND token_address = lower('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
ORDER BY block_number DESC
LIMIT 50;
```

All transfers involving a wallet on either side (bloom-pruned):

```sql theme={null}
SELECT block_number, token_address, from_address, to_address, amount
FROM recipe_token_transfers.fact_token_transfers FINAL
WHERE chain_id = 1
  AND (from_address = lower('0x...') OR to_address = lower('0x...'))
ORDER BY block_number DESC
LIMIT 50;
```

Net amount received by a wallet for one token (sign-aware, cheaper than `FINAL`):

```sql theme={null}
SELECT
  sumIf(toFloat64OrZero(amount), to_address = lower('0xwallet') AND sign =  1)
- sumIf(toFloat64OrZero(amount), to_address = lower('0xwallet') AND sign = -1)
  AS received
FROM recipe_token_transfers.fact_token_transfers
WHERE chain_id = 1 AND token_address = lower('0xtoken');
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  The realtime reorg path needs a single-column `UNIQUE` on the position column, but `position` is block-level (many transfers share one block), so array-expanded transfer rows can only carry a composite unique. Run realtime/hybrid on **ClickHouse**, where the collapsing log table corrects reorgs per-block. The Postgres / MySQL configs are intended for `historical` backfill.
</Note>

### Multichain

The recipe is chain-parametrized via the `chain` setting — point it at any supported EVM chain or Solana. On Solana, multiple events in one instruction can share a `logIndex`, so the `vendor_event_id` is widened with `(from_address, to_address, token_address, amount)` to keep rows distinct; the transfer log it produces is identical in shape.

### Fidelity gaps

The recipe lands exactly what the `tokenTransfers` array carries. Fields a transfers endpoint might surface that have **no onchain source in this array** are omitted:

* **USD value** — a transfer carries no price. Pricing requires joining the same-block price data; that's out of scope for a plain transfer log (see Token Prices for the price-join pattern).
* **Token metadata** (`symbol`, `name`, `decimals`, logo, verified/spam flags) — these come from a separate token-metadata sync, not the transfer event. `amount` is therefore stored raw, not decimal-adjusted.
* **Pre/post balances** — the balance surface lives in the balances recipes (Token Balances by Token / by Wallet); this transfer log stays a flat event stream.

### Related

<Columns cols={2}>
  <Card title="Token Holders" href="/data-feeds/recipes/token/token-holders" icon="users">
    The balance roll-up these transfers feed — all non-zero holders of a token.
  </Card>

  <Card title="Accounting & Tax" href="/data-feeds/use-cases/accounting" icon="calculator">
    Per-asset transfer ledgers for reconciliation, valued via Token Prices.
  </Card>
</Columns>
