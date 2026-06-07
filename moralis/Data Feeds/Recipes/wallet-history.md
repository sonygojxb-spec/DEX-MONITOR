> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Wallet History

> Reconstruct a wallet's full chronological event feed — every transfer, swap, NFT move, approval, and LP change, with USD value per event — as a continuous sync into your own database.

### Question it answers

> "Show me the full chronological event feed for wallet **0x…**, newest first. Each row is one event with its actual payload — counterparty, amounts, token IDs, pair address, USD value — and I can filter by event type."

A single read returns what the public API stitches together client-side from `/wallets/{address}/erc20-transfers`, `/native-transactions`, `/nfts/transfers`, `/swaps`, `/approvals`, and `/defi/positions`. Storing it **pre-stitched**, in your own database, is the value.

### What you get

The recipe lands **one row per wallet-bearing event**. A wallet is "involved" if it is a non-empty `from`/`to` (or owner/approver) on the event. Six event types share one wide, flat table; per-type columns are populated as relevant:

| `event_type`       | Rows per event | Populated columns                                                    | USD value |
| ------------------ | -------------- | -------------------------------------------------------------------- | --------- |
| `token_transfer`   | 2 (from + to)  | `token_address`, `amount`                                            | ✅ inline  |
| `native_transfer`  | 2 (from + to)  | `amount`                                                             | —         |
| `nft_transfer`     | 2 (from + to)  | `token_address`, `token_id`, `amount`                                | —         |
| `swap`             | 1 (the wallet) | `pair_address`, `token_in/out_address`, `amount_in/out`              | ✅ inline  |
| `approval`         | 1 (approver)   | `spender_address`, `token_address`, `amount`                         | —         |
| `liquidity_change` | 1 (LP owner)   | `change_type`, `pair_address`, `token0/1_address`, `token0/1_amount` | ✅ inline  |

Each row also carries `direction` (`sent` · `received` · `self` · `minted` · `burned`), `counterparty`, `tx_hash`, `block_number`, `block_timestamp`, and `log_index`.

### Source

The transform reads six per-block arrays and `UNION`s them into the event feed:

`tokenTransfers` · `nativeTransfers` · `nftTokenTransfers` · `tokenSwaps` · `tokenApprovals` · `pairLiquidityChanges`

USD values are computed **inline** from the same block's `tokenPriceUpdates` — no separate price join at read time.

### Destination

| Destination                  | Table                      | Read pattern                                                                                           |
| ---------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------ |
| **ClickHouse** (first-class) | `fact_wallet_history_full` | Prefix scan on `(chain_id, wallet_address, block_number, log_index)`; read with `FINAL` or `sum(sign)` |
| **Postgres**                 | `wallet_history_full`      | Index on `(wallet_address, block_number DESC)`                                                         |
| **MySQL**                    | `wallet_history_full`      | Index on `(wallet_address, block_number)`                                                              |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct. The fact table's sort key is wallet-first, so a wallet's feed — optionally filtered by `event_type` — is a contiguous range read.

### Full schema

Below is the complete read table this recipe produces. It's the **full shape** — every event type's columns in one wide row. This is a starting point: keep the columns and event types you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). Raw `uint256` amounts and `token_id` are stored as text (they exceed numeric precision); USD columns are wide decimals so a low-decimals token × price never overflows.

<Accordion title="ClickHouse — fact_wallet_history_full">
  ```sql theme={null}
  CREATE TABLE recipe_wallet_history_full.fact_wallet_history_full
  (
      chain_id            UInt32,
      wallet_address      String,
      block_number        UInt64,
      log_index           UInt32,
      event_type          LowCardinality(String),   -- token_transfer | native_transfer | nft_transfer | swap | approval | liquidity_change
      vendor_event_id     String,
      block_timestamp     DateTime64(3),
      tx_hash             String,
      transaction_index   Nullable(Int32),
      direction           LowCardinality(String),   -- sent | received | self | minted | burned | n/a
      counterparty        String,
      token_address       String,
      amount              String,                   -- raw uint256
      amount_usd          Nullable(String),
      token_id            String,
      pair_address        String,
      token_in_address    String,
      amount_in           String,
      amount_in_usd       Nullable(String),
      token_out_address   String,
      amount_out          String,
      amount_out_usd      Nullable(String),
      spender_address     String,
      change_type         LowCardinality(String),   -- mint | burn | sync | ''
      token0_address      String,
      token0_amount       String,
      token0_amount_usd   Nullable(String),
      token1_address      String,
      token1_amount       String,
      token1_amount_usd   Nullable(String),
      sign                Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_wallet_history_full', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(block_timestamp))
  ORDER BY (chain_id, wallet_address, block_number, log_index, event_type, vendor_event_id);
  ```

  The `sign` column drives reorg collapsing — read with `FINAL` or `sum(sign)`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
</Accordion>

<Accordion title="Postgres — wallet_history_full">
  ```sql theme={null}
  CREATE TABLE public.wallet_history_full (
    position             BIGINT          NOT NULL,
    chain_id             BIGINT          NOT NULL,
    block_number         BIGINT          NOT NULL,
    block_timestamp      BIGINT          NOT NULL,      -- unix seconds
    tx_hash              TEXT            NOT NULL,
    log_index            BIGINT          NOT NULL,
    wallet_address       TEXT            NOT NULL,
    event_type           TEXT            NOT NULL,
    vendor_event_id      TEXT            NOT NULL,
    direction            TEXT            NOT NULL,
    counterparty         TEXT            NOT NULL,
    token_address        TEXT            NOT NULL,
    amount               TEXT            NOT NULL,       -- raw uint256
    amount_usd           NUMERIC(65, 18) NULL,
    token_id             TEXT            NOT NULL,
    pair_address         TEXT            NOT NULL,
    token_in_address     TEXT            NOT NULL,
    amount_in            TEXT            NOT NULL,
    amount_in_usd        NUMERIC(65, 18) NULL,
    token_out_address    TEXT            NOT NULL,
    amount_out           TEXT            NOT NULL,
    amount_out_usd       NUMERIC(65, 18) NULL,
    spender_address      TEXT            NOT NULL,
    change_type          TEXT            NOT NULL,
    token0_address       TEXT            NOT NULL,
    token0_amount        TEXT            NOT NULL,
    token0_amount_usd    NUMERIC(65, 18) NULL,
    token1_address       TEXT            NOT NULL,
    token1_amount        TEXT            NOT NULL,
    token1_amount_usd    NUMERIC(65, 18) NULL
  );

  -- Primary access pattern: every event for a wallet, newest first.
  CREATE INDEX ON public.wallet_history_full (chain_id, wallet_address, block_number DESC);
  -- Event-type filter within a wallet.
  CREATE INDEX ON public.wallet_history_full (chain_id, wallet_address, event_type, block_number DESC);
  ```

  MySQL is the same shape with `DECIMAL(65,18)` for the USD columns. `position` is the block-level cursor used during backfill.
</Accordion>

### Example reads

A wallet's full feed, newest first (ClickHouse):

```sql theme={null}
SELECT block_number, log_index, event_type, direction, counterparty,
       token_address, amount, amount_usd
FROM recipe_wallet_history_full.fact_wallet_history_full FINAL
WHERE chain_id = 1
  AND wallet_address = lower('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')
ORDER BY block_number DESC, log_index DESC
LIMIT 50;
```

Only swaps and token transfers (the `event_type` filter compresses the scan further):

```sql theme={null}
SELECT block_number, event_type, token_in_address, amount_in,
       token_out_address, amount_out, amount_in_usd, amount_out_usd
FROM recipe_wallet_history_full.fact_wallet_history_full FINAL
WHERE chain_id = 1
  AND wallet_address = lower('0xd8dA…96045')
  AND event_type IN ('swap', 'token_transfer')
ORDER BY block_number DESC, log_index DESC;
```

Per-event-type breakdown (sign-aware, cheaper than `FINAL`):

```sql theme={null}
SELECT event_type, sum(sign) AS events
FROM recipe_wallet_history_full.fact_wallet_history_full
WHERE chain_id = 1 AND wallet_address = lower('0xd8dA…96045')
GROUP BY event_type
ORDER BY events DESC;
```

### USD valuation and fidelity gaps

* **Swaps and LP changes** carry per-leg decimals, so their `*_usd` columns are true dollar values (`raw / 10^decimals × price`).
* **Token transfers** have no decimals field on the transfer event, so `amount_usd` is `raw_amount × price` (**unscaled**). Divide by `10^token_decimals` to read dollars — fold in a decimals lookup from a Token Metadata sync if you need it pre-scaled.
* **Native and NFT transfers** leave USD `NULL` — native pricing needs a separate native-price feed; NFT pricing is out of scope (use an NFT Trades recipe for trade-priced data).
* **Approvals** leave USD `NULL` by design — an unlimited allowance × price is meaningless.

### Lightweight variant: transaction pointers

If you only need a wallet's **transaction list** — one pointer per `(wallet, tx)`, not the full payload — there's a slimmer variant that lands just the deduplicated pointers from the transfer arrays. Use the full feed above when you need amounts, counterparties, and USD value; use the pointer variant when you only need "which transactions touched this wallet."

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

### Multichain

The recipe is chain-parametrized via the `chain` setting — point it at any supported EVM chain or Solana. On Solana, the event identity is widened to stay unique under Solana's repeated log indices; the wallet feed it produces is identical in shape.

### Powers these use cases

<Columns cols={2}>
  <Card title="Accounting & Tax" href="/data-feeds/use-cases/accounting" icon="calculator">
    The chronological, USD-valued event feed behind a ledger.
  </Card>

  <Card title="Compliance & AML" icon="shield-check">
    Full counterparty and transfer trail per address.
  </Card>
</Columns>
