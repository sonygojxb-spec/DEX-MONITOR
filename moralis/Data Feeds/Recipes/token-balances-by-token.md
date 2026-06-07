> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Balances by Token

> Sync the current non-zero balance of every wallet that holds a given token into your own database — the holder list behind a token, latest-wins per wallet.

### Question it answers

> "Give me the non-zero balance of every wallet that holds token **0x…**, largest first."

This is the by-token sort of the same balance data the public API exposes per holder — the holder list and balances for a single token. The sibling recipe [Token Balances by Wallet](/data-feeds/recipes/wallet/token-balances-by-wallet) is the exact same data sorted the other way (wallet-first); in production you land the source once and add both read shapes.

### What you get

The recipe lands **one balance observation per side of every transfer**, then resolves the **latest observation per `(token, wallet)`** as the current balance. Moralis-indexed transfers carry the *absolute* post-transfer balance of both sides (`fromPostBalance` / `toPostBalance`), so no running-sum reconstruction is needed — the highest `(block_number, log_index)` observation is the truth.

| Column                         | Description                                                             |
| ------------------------------ | ----------------------------------------------------------------------- |
| `token_address`                | The token being held (the read key)                                     |
| `wallet_address`               | The holder                                                              |
| `balance`                      | Absolute balance after this transfer, raw `uint256` as text             |
| `block_number`, `log_index`    | Recency tuple — the latest pair wins per `(token, wallet)`              |
| `event_ts` / `block_timestamp` | Block time of the observation                                           |
| `leg`                          | `from` or `to` — which side of the transfer this observation came from  |
| `vendor_event_id`              | Stable per-observation identity (keeps the two unpivoted rows distinct) |

Each transfer yields two observations: `(from_address, from_post_balance)` and `(to_address, to_post_balance)`. The EVM zero address (mint/burn counterparty) and any side without a producer-resolved post-balance are skipped.

### Source

The transform reads one per-block array — `tokenTransfers` — and **unpivots** each transfer into the two per-wallet balance observations it carries. Balance comes straight from the transfer's `fromPostBalance` / `toPostBalance`; there is no separate balance feed or join.

### Destination

| Destination                  | Table                                                                  | By-token read pattern                                                                                                                        |
| ---------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_balances_by_token`                                               | Prefix scan on `(chain_id, token_address, wallet_address, …)`; current balance via `argMax(balance, (block_number, log_index))` over `FINAL` |
| **Postgres**                 | `token_balances` (materialized view over `token_balance_observations`) | Partial index `(token_address, wallet_address) WHERE balance > 0`                                                                            |
| **MySQL**                    | `token_balances` (trigger-maintained over observations)                | PK `(token_address, wallet_address)` + `DELETE … WHERE balance = 0` cleanup                                                                  |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct: a reorg negates the rolled-back block's observations (`sign = -1`) and re-emits the corrected ones, and `FINAL` collapses the pair before `argMax` runs. Read canonical state with `FINAL` or a sign-aware aggregate — never a bare `WHERE sign = 1`.

On Postgres and MySQL the sink appends observations and the current-balance projection is derived: Postgres via a `DISTINCT ON (token_address, wallet_address)` materialized view, MySQL via an `AFTER INSERT` latest-wins upsert trigger plus a periodic zero-balance cleanup.

### Full schema

Below is the complete read table this recipe produces — the per-wallet balance observations, keyed by token. Keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). Raw `uint256` balances are stored as text in ClickHouse (they exceed numeric precision); Postgres uses an explicit `NUMERIC(76, 0)` so large raw balances don't overflow a narrower inferred type.

<Accordion title="ClickHouse — fact_balances_by_token">
  ```sql theme={null}
  CREATE TABLE recipe_token_balances_by_token.fact_balances_by_token
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
      balance           String,          -- absolute balance after this transfer (raw uint256)
      leg               LowCardinality(String),   -- 'from' | 'to'
      sign              Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_balances_by_token', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, token_address, wallet_address, block_number, log_index, vendor_event_id, leg);
  ```

  The `leg` (`from` / `to`) keeps the two unpivoted rows of one transfer distinct; the `+1`/`−1` reorg pair for one leg shares a key and collapses. Read with `FINAL` then `argMax`, or a sign-aware aggregate. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
</Accordion>

<Accordion title="Postgres — token_balances (materialized view)">
  ```sql theme={null}
  -- Observations (sink target). Append-only, keyed on the block-level position.
  CREATE TABLE public.token_balance_observations (
    position         BIGINT  NOT NULL,
    log_index        BIGINT  NOT NULL,
    block_number     BIGINT  NOT NULL,
    block_timestamp  BIGINT  NOT NULL,         -- unix seconds
    token_address    TEXT    NOT NULL,
    wallet_address   TEXT    NOT NULL,
    balance          NUMERIC(76, 0) NOT NULL,  -- absolute balance after the transfer
    leg              TEXT    NOT NULL,         -- 'from' | 'to'
    vendor_event_id  TEXT    NOT NULL
  );

  -- Speeds the DISTINCT ON (latest-per-key) the materialized view computes.
  CREATE INDEX IF NOT EXISTS tbo_token_wallet_recency_idx
    ON public.token_balance_observations
    (token_address, wallet_address, block_number DESC, log_index DESC);

  -- Current-balance projection: latest observation per (token, wallet).
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

  -- Required by REFRESH MATERIALIZED VIEW CONCURRENTLY.
  CREATE UNIQUE INDEX IF NOT EXISTS token_balances_pk
    ON public.token_balances (token_address, wallet_address);

  -- Active holders of a token (this recipe's primary access path).
  CREATE INDEX IF NOT EXISTS token_balances_by_token_active_idx
    ON public.token_balances (token_address, wallet_address)
    WHERE balance > 0;

  -- Sibling access path: all non-zero balances held by a wallet.
  CREATE INDEX IF NOT EXISTS token_balances_by_wallet_active_idx
    ON public.token_balances (wallet_address, token_address)
    WHERE balance > 0;

  -- Cleanup index: find zeroed-out positions to prune.
  CREATE INDEX IF NOT EXISTS token_balances_zero_cleanup_idx
    ON public.token_balances (token_address, wallet_address)
    WHERE balance = 0;
  ```

  The materialized view is the current-balance projection — refresh it on a schedule with `REFRESH MATERIALIZED VIEW CONCURRENTLY token_balances;` (the `CONCURRENTLY` form needs the unique index above and never blocks readers). MySQL is the same shape with a trigger-maintained `token_balances` table and a periodic `DELETE … WHERE balance = 0` standing in for the cleanup index.
</Accordion>

### Example reads

All current non-zero holders of a token, largest first — `FINAL` collapses reorg `±1` pairs before `argMax` resolves the latest balance per wallet (ClickHouse):

```sql theme={null}
SELECT wallet_address,
       argMax(balance, (block_number, log_index)) AS current_balance
FROM recipe_token_balances_by_token.fact_balances_by_token FINAL
WHERE chain_id = 1 AND token_address = lower('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
GROUP BY wallet_address
HAVING current_balance != '0' AND current_balance != ''
ORDER BY toFloat64OrZero(current_balance) DESC
LIMIT 100;
```

Holder count for a token:

```sql theme={null}
SELECT countDistinct(wallet_address) FROM (
  SELECT wallet_address,
         argMax(balance, (block_number, log_index)) AS bal
  FROM recipe_token_balances_by_token.fact_balances_by_token FINAL
  WHERE chain_id = 1 AND token_address = lower('0xA0b8...')
  GROUP BY wallet_address
  HAVING bal != '0' AND bal != ''
);
```

Postgres — refresh the view, then query the partial index:

```sql theme={null}
REFRESH MATERIALIZED VIEW CONCURRENTLY token_balances;

SELECT wallet_address, balance FROM public.token_balances
WHERE token_address = lower('0xA0b8...') AND balance > 0
ORDER BY balance DESC LIMIT 100;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  **Postgres / MySQL are backfill-first here.** The realtime reorg path needs a single-column unique key on the position column, but the recipe's position is block-level — so the Postgres / MySQL configs target `historical`. The Postgres materialized view and the MySQL cleanup are also not reorg-aware on their own; under realtime you would re-derive them. ClickHouse handles reorgs automatically via `sign`, so run realtime/hybrid there.
</Note>

### Multichain

The recipe is chain-parametrized — point it at any supported EVM chain or Solana. On Solana, the per-observation `vendor_event_id` already folds in `(from, to, token, amount)`, so each observation stays row-unique despite Solana's repeated `logIndex` within an instruction; the holder list it produces is identical in shape.

### Fidelity notes

* **Latest-wins, not a delta sum.** Balances are absolute post-transfer observations, so the current balance is purely the most recent observation per `(token, wallet)`. There is no running-sum reconstruction and no dependence on having seen every prior transfer.
* **Raw amounts only.** `balance` is the raw `uint256` (text in ClickHouse, `NUMERIC(76, 0)` in Postgres). It is not decimal-scaled and carries no USD value — divide by `10^token_decimals` for human units (fold in a decimals lookup from a Token Metadata sync), and join Token Prices if you need USD.
* **Zero address excluded.** Mint/burn counterparties (the EVM zero address) and sides without a producer-resolved post-balance are not holders and are skipped at unpivot time.

### Related

<Columns cols={2}>
  <Card title="Token Balances by Wallet" href="/data-feeds/recipes/wallet/token-balances-by-wallet" icon="wallet">
    The sibling — the same balance data sorted wallet-first.
  </Card>

  <Card title="Token Analytics" href="/data-feeds/use-cases/token-analytics" icon="chart-line">
    The use case holder lists and balances power.
  </Card>
</Columns>
