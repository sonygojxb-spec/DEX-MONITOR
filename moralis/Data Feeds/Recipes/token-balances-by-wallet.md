> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Balances by Wallet

> Sync every ERC-20 token a wallet holds, with its current non-zero balance, into your own database — a portfolio lookup that's a single prefix scan.

### Question it answers

> "Give me every token wallet **0x…** holds, with its current non-zero balance."

This is the by-wallet portfolio read. It's the same ingest as Token Balances by Token, sorted the other way: this recipe keys **wallet-first** so one wallet's full token holdings are a contiguous range read, while the sibling keys token-first to list a token's holders.

### What you get

The recipe lands **one balance observation per wallet, per transfer leg**. Each `token_transfer` carries absolute post-transfer balances (`from_post_balance` / `to_post_balance`), so every transfer becomes two observations — one for the sender, one for the receiver. The **latest observation per `(wallet, token)`** is the current balance ("latest-wins").

| Column                      | Description                                                                                                             |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `chain_id`                  | Chain identifier                                                                                                        |
| `wallet_address`            | The holder — leading sort key                                                                                           |
| `token_address`             | The ERC-20 contract                                                                                                     |
| `balance`                   | Absolute post-transfer balance for this wallet, raw `uint256` (the latest per `(wallet, token)` is the current balance) |
| `leg`                       | `from` or `to` — which side of the transfer produced this observation                                                   |
| `block_number`, `log_index` | On-chain ordering tuple — picks the latest observation                                                                  |
| `event_ts`                  | Block time                                                                                                              |
| `vendor_event_id`           | Stable per-observation identity (keeps rows unique)                                                                     |

The zero address is excluded, so a token's balance going to `0` on a full transfer-out is a real observation you read as the current state — not a missing row.

### Source

The transform reads one per-block array — `tokenTransfers` — and unpivots each transfer into two per-wallet observations: `(from_address, from_post_balance)` and `(to_address, to_post_balance)`. Because the source supplies **absolute** post-balances on each transfer, there's no running-sum reconstruction: the latest observation is the balance.

### Destination

| Destination                  | Table                                                                   | By-wallet access                                                                                         |
| ---------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_balances_by_wallet`                                               | Prefix scan on `(chain_id, wallet_address, token_address, …)`; current balance via `argMax` over `FINAL` |
| **Postgres**                 | `token_balances` (materialized view over `token_balance_observations`)  | Partial index `(wallet_address, token_address) WHERE balance > 0`                                        |
| **MySQL**                    | `token_balances` (trigger-maintained over `token_balance_observations`) | PK `(wallet_address, token_address)` + `DELETE … WHERE balance = 0` cleanup                              |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct. The fact table's sort key is wallet-first, so a wallet's holdings are a contiguous range read; you collapse to the current balance per token with `argMax` over `FINAL`.

### Full schema

Below is the complete read table this recipe produces. It's a starting point — keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). Raw `uint256` balances are stored as text (ClickHouse) or `NUMERIC(76, 0)` (Postgres) so they never overflow.

<Accordion title="ClickHouse — fact_balances_by_wallet">
  ```sql theme={null}
  CREATE TABLE recipe_token_balances_by_wallet.fact_balances_by_wallet
  (
      vendor_event_id   String,
      ingested_at       DateTime64(3),
      chain_id          UInt32,
      block_hash        String,
      block_number      UInt64,
      log_index         UInt32,
      event_ts          DateTime64(3),
      token_address     String,
      wallet_address    String,
      balance           String,                   -- absolute post-transfer balance, raw uint256
      leg               LowCardinality(String),   -- from | to
      sign              Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_balances_by_wallet', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, wallet_address, token_address, block_number, log_index, vendor_event_id, leg);
  ```

  The `sign` column drives reorg collapsing — read with `FINAL` then `argMax`, or a sign-aware aggregate, never a bare `WHERE sign = 1`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
</Accordion>

<Accordion title="Postgres — token_balances">
  ```sql theme={null}
  -- 1. Observations (sink target): one row per wallet, per transfer leg.
  CREATE TABLE public.token_balance_observations (
    position         BIGINT  NOT NULL,
    log_index        BIGINT  NOT NULL,
    block_number     BIGINT  NOT NULL,
    block_timestamp  BIGINT  NOT NULL,         -- unix seconds
    token_address    TEXT    NOT NULL,
    wallet_address   TEXT    NOT NULL,
    balance          NUMERIC(76, 0) NOT NULL,
    leg              TEXT    NOT NULL,
    vendor_event_id  TEXT    NOT NULL
  );

  -- Recency index leads with the DISTINCT ON keys so the REFRESH avoids a sort.
  CREATE INDEX tbo_token_wallet_recency_idx
    ON public.token_balance_observations
    (token_address, wallet_address, block_number DESC, log_index DESC);

  -- 2. Current-balance materialized view: latest observation per (token, wallet).
  CREATE MATERIALIZED VIEW public.token_balances AS
  SELECT DISTINCT ON (token_address, wallet_address)
    token_address,
    wallet_address,
    balance,
    block_number,
    log_index,
    block_timestamp
  FROM public.token_balance_observations
  ORDER BY token_address, wallet_address, block_number DESC, log_index DESC;

  CREATE UNIQUE INDEX token_balances_pk
    ON public.token_balances (token_address, wallet_address);

  -- This recipe's primary access path: active balances held by a wallet.
  CREATE INDEX token_balances_by_wallet_active_idx
    ON public.token_balances (wallet_address, token_address)
    WHERE balance > 0;

  -- Sibling access path (all non-zero holders of a token).
  CREATE INDEX token_balances_by_token_active_idx
    ON public.token_balances (token_address, wallet_address)
    WHERE balance > 0;

  -- Cleanup index for zeroed positions.
  CREATE INDEX token_balances_zero_cleanup_idx
    ON public.token_balances (wallet_address, token_address)
    WHERE balance = 0;
  ```

  Refresh the view on a schedule: `REFRESH MATERIALIZED VIEW CONCURRENTLY token_balances;`. MySQL is the same shape with a trigger-maintained `token_balances` table and a `DELETE … WHERE balance = 0` cleanup. `position` is the block-level cursor used during backfill.
</Accordion>

### Example reads

Every token a wallet holds, current non-zero balance only (ClickHouse — `argMax` over `FINAL` picks the latest observation per token):

```sql theme={null}
SELECT token_address,
       argMax(balance, (block_number, log_index)) AS current_balance
FROM recipe_token_balances_by_wallet.fact_balances_by_wallet FINAL
WHERE chain_id = 1 AND wallet_address = lower('0x...')
GROUP BY token_address
HAVING current_balance != '0' AND current_balance != ''
ORDER BY token_address;
```

Postgres (after `REFRESH MATERIALIZED VIEW CONCURRENTLY token_balances;`):

```sql theme={null}
SELECT token_address, balance FROM public.token_balances
WHERE wallet_address = lower('0x...') AND balance > 0
ORDER BY balance DESC;
```

MySQL:

```sql theme={null}
SELECT token_address, balance FROM token_balances
WHERE wallet_address = LOWER('0x...') AND balance > 0
ORDER BY balance DESC;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  The backfill cursor (`position`) is block-level, so realtime/hybrid on Postgres / MySQL is constrained by their single-column `UNIQUE` requirement. Run realtime/hybrid on **ClickHouse**; the Postgres / MySQL configs target `historical` backfill.
</Note>

### Multichain

The recipe is chain-parametrized — point it at any supported EVM chain or Solana. On Solana, the per-observation identity already folds `(from, to, token, amount)` into `vendor_event_id` so rows stay unique under Solana's repeated `logIndex`; the balances it produces are identical in shape.

### Fidelity gaps

* **Raw balances only.** `balance` is the raw `uint256` post-transfer amount — divide by `10^token_decimals` to read human units. Fold in a decimals lookup from a Token Metadata sync if you need it pre-scaled.
* **No USD value.** This recipe lands quantities, not dollar value. Join to a Token Prices sync at read time for portfolio valuation.
* **Latest-wins semantics.** A `(wallet, token)` row reflects the most recent transfer-derived post-balance. Direct mints/burns or rebases that emit a transfer are captured; balance changes with no transfer event are not.

### Related

<Columns cols={2}>
  <Card title="Token Balances by Token" href="/data-feeds/recipes/token/token-balances-by-token" icon="coins">
    The sibling — same ingest, keyed token-first to list a token's holders.
  </Card>

  <Card title="Portfolio Tracking" href="/data-feeds/use-cases/portfolio-tracking" icon="wallet">
    The use case this balance feed powers.
  </Card>
</Columns>
