> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Native Balances

> Sync each wallet's current native-asset (ETH/MATIC/…) balance into your own database, kept current from per-block onchain data. Mirrors the Moralis GET /{address}/balance and GET /wallets/balances endpoints.

### Question it answers

> "What is wallet **0x…**'s current native-asset (ETH / MATIC / …) balance?"

Mirrors Moralis `GET /{address}/balance` and `GET /wallets/balances`. It is the native-asset analog of [Token Balances by Wallet](/data-feeds/recipes/wallet/token-balances-by-wallet): each `nativeTransfers` event carries the absolute post-transfer native balance for both legs, so the latest observation per `(chain_id, wallet_address)` is the current balance — no replaying of deltas.

### What you get

The recipe lands **one row per balance observation** — each native transfer is unpivoted into two observations (the `from` leg and the `to` leg), each carrying that wallet's absolute native balance immediately after the transfer. There is **no `token_address` and no `token_id`** — the native asset is implied by the chain.

| Column                   | Description                                                                                          |
| ------------------------ | ---------------------------------------------------------------------------------------------------- |
| `wallet_address`         | The wallet whose post-transfer balance this row records                                              |
| `balance`                | Absolute native balance after the transfer (raw `uint256`, in wei)                                   |
| `leg`                    | `from` or `to` — which side of the transfer produced this observation                                |
| `block_number`           | Block the transfer landed in                                                                         |
| `native_seq`             | 1-based position of the transfer within the block's `nativeTransfers` array — the recency tiebreaker |
| `transaction_index`      | Informational only (not unique per native transfer)                                                  |
| `block_hash`, `event_ts` | Block hash and block time                                                                            |
| `vendor_event_id`        | Stable per-observation identity                                                                      |

Current balance is **latest-wins**: the most recent observation by `(block_number, native_seq)` per wallet is the live balance.

### Source

The transform reads one per-block array and unpivots it:

`nativeTransfers`

Each transfer becomes two observations — `(fromAddress, fromPostBalance)` and `(toAddress, toPostBalance)`. The zero address and empty post-balances are dropped, and `toAddress` (nullable on block-reward / fee-burn legs) is coalesced before those filters apply.

### Destination

| Destination                  | Table                                                                     | Read pattern                                                                                                     |
| ---------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_native_balances`                                                    | Prefix scan on `(chain_id, wallet_address, block_number, native_seq)`; current balance via `argMax` over `FINAL` |
| **Postgres**                 | `native_balances` (materialized view over `native_balance_observations`)  | Partial index `(wallet_address) WHERE balance > 0`                                                               |
| **MySQL**                    | `native_balances` (trigger-maintained from `native_balance_observations`) | PK `(wallet_address)`                                                                                            |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct. The fact table's sort key is wallet-first, so a wallet's observations are a contiguous range read and `argMax` picks the live balance. Postgres collapses observations into a current-balance materialized view; MySQL keeps a trigger-maintained state table.

### Full schema

Below is the complete read table this recipe produces — observations keyed by wallet. Keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). The raw `balance` is a `uint256` in wei and is stored as text (it exceeds numeric precision); divide by `10^18` (the native decimals) in your app to read whole units.

<Accordion title="ClickHouse — fact_native_balances">
  ```sql theme={null}
  CREATE TABLE recipe_native_balances.fact_native_balances
  (
      vendor_event_id   String,
      ingested_at       DateTime64(3),
      chain_id          UInt32,
      block_hash        String,
      block_number      UInt64,
      transaction_index UInt32,                 -- informational only (not unique per native transfer)
      native_seq        UInt32,                 -- 1-based in-block ordinal; recency tiebreaker
      event_ts          DateTime64(3),
      wallet_address    String,
      balance           String,                 -- absolute post-transfer native balance, raw uint256 (wei)
      leg               LowCardinality(String), -- from | to
      sign              Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_native_balances', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, wallet_address, block_number, native_seq, vendor_event_id, leg);
  ```

  The `sign` column drives reorg collapsing — read with `FINAL` + `argMax`, never a bare `WHERE sign = 1`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
</Accordion>

<Accordion title="Postgres — native_balances">
  ```sql theme={null}
  -- Observations (sink target).
  CREATE TABLE public.native_balance_observations (
    position           BIGINT  NOT NULL,        -- block-level backfill cursor
    transaction_index  BIGINT  NOT NULL,        -- informational only
    native_seq         BIGINT  NOT NULL,        -- 1-based in-block ordinal; recency tiebreaker
    block_number       BIGINT  NOT NULL,
    block_timestamp    BIGINT  NOT NULL,        -- unix seconds
    wallet_address     TEXT    NOT NULL,
    balance            NUMERIC(76, 0) NOT NULL, -- absolute native balance (wei)
    leg                TEXT    NOT NULL,        -- from | to
    vendor_event_id    TEXT    NOT NULL
  );

  -- Recency index for the DISTINCT ON; leads with the DISTINCT ON key so
  -- REFRESH MATERIALIZED VIEW CONCURRENTLY avoids a sort.
  CREATE INDEX nbo_wallet_recency_idx
    ON public.native_balance_observations
    (wallet_address, block_number DESC, native_seq DESC);

  -- Current-balance materialized view: latest observation per wallet.
  CREATE MATERIALIZED VIEW public.native_balances AS
  SELECT DISTINCT ON (wallet_address)
    wallet_address, balance, block_number, native_seq, transaction_index, block_timestamp
  FROM public.native_balance_observations
  ORDER BY wallet_address, block_number DESC, native_seq DESC;

  CREATE UNIQUE INDEX native_balances_pk ON public.native_balances (wallet_address);

  -- Active (non-zero) native balances — this recipe's primary access path.
  CREATE INDEX native_balances_active_idx
    ON public.native_balances (wallet_address) WHERE balance > 0;
  -- Cleanup index for zeroed wallets.
  CREATE INDEX native_balances_zero_cleanup_idx
    ON public.native_balances (wallet_address) WHERE balance = 0;
  ```

  MySQL is the same shape with `DECIMAL(65,0)` for `balance` and a trigger-maintained `native_balances` state table (PK `wallet_address`, plus a `DELETE … WHERE balance = 0` cleanup). `position` is the block-level cursor used during backfill. Refresh the Postgres view on a schedule: `REFRESH MATERIALIZED VIEW CONCURRENTLY native_balances;`.
</Accordion>

### Example reads

Current native balance for a wallet (ClickHouse — `argMax` picks the latest observation):

```sql theme={null}
SELECT argMax(balance, (block_number, native_seq)) AS current_balance
FROM recipe_native_balances.fact_native_balances FINAL
WHERE chain_id = 1 AND wallet_address = lower('0x...')
GROUP BY wallet_address
HAVING current_balance != '0' AND current_balance != '';
```

All current non-zero native balances (mirrors `GET /wallets/balances`):

```sql theme={null}
SELECT wallet_address,
       argMax(balance, (block_number, native_seq)) AS current_balance
FROM recipe_native_balances.fact_native_balances FINAL
WHERE chain_id = 1
GROUP BY wallet_address
HAVING current_balance != '0' AND current_balance != ''
ORDER BY wallet_address;
```

Postgres — current balance for one wallet, after a refresh:

```sql theme={null}
REFRESH MATERIALIZED VIEW CONCURRENTLY native_balances;

SELECT balance FROM public.native_balances
WHERE wallet_address = lower('0x...');
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  The backfill cursor (`position`) is block-level, so realtime/hybrid on Postgres / MySQL is constrained by their single-column `UNIQUE` requirement. Run realtime/hybrid on ClickHouse; the Postgres / MySQL configs target `historical` backfill.
</Note>

### Multichain

The recipe is chain-parametrized via the `chain` setting — point it at any supported EVM chain or Solana. On Solana, the `vendor_event_id` already folds in `(transactionIndex, fromAddress, toAddress, amount, 'native')`, so observations stay row-unique even where Solana repeats indices within a transaction. The balance surface it produces is identical in shape.

### Recency: why `native_seq`, not `log_index`

`nativeTransfers` carry **no `logIndex`**, and `transactionIndex` is **not unique** per transfer (a single transaction with several internal native movements reuses it). "Which post-balance is current" is therefore tiebroken by **`native_seq`** — the 1-based position of each transfer within the block's `nativeTransfers` array. It is a stable block-global ordinal emitted in canonical order and computed once in the shared transform, so ClickHouse `argMax`, Postgres `DISTINCT ON`, and the MySQL trigger all converge on the same current balance per wallet.

### Fidelity gaps

* **No USD value.** Moralis `GET /{address}/balance` can return a USD-valued balance; that needs the native-asset/USD price at the block, which is not carried on `nativeTransfers`. Join against a native-price source (e.g. the wrapped-native pair from a [Token Prices](/data-feeds/recipes/token/token-prices) sync) to add it.
* **Raw wei, no decimals scaling.** `balance` is the raw `uint256` in wei; divide by `10^18` in your app to read whole native units.

### Related

<Columns cols={2}>
  <Card title="Token Balances by Wallet" href="/data-feeds/recipes/wallet/token-balances-by-wallet" icon="wallet">
    The ERC-20 sibling — every token a wallet holds, with balance.
  </Card>

  <Card title="Portfolio Tracking" href="/data-feeds/use-cases/portfolio-tracking" icon="chart-pie">
    Native balances are the base-asset leg of a wallet's portfolio.
  </Card>
</Columns>
