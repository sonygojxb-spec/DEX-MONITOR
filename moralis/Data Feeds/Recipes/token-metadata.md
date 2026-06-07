> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Metadata

> Sync ERC-20 token metadata — name, symbol, decimals, total supply, and deployer — captured at deploy time into your own database. Mirrors the Moralis GET /erc20/metadata endpoint.

### Question it answers

> "Give me the ERC-20 metadata — `name` / `symbol` / `decimals` / `total_supply` — for token **0x…**." Mirrors Moralis `GET /erc20/metadata`.

The recipe lands one observation per **TOKEN-type deployed contract** and projects it into a one-row-per-token metadata surface. Token metadata is fixed at deploy time, so there is normally exactly one row per `(chain_id, token_address)` — the latest deploy by `(block_number, transaction_index)` is canonical (defensive against a CREATE2 re-deploy at a reused address).

### What you get

One row per token contract, keyed by `token_address`:

| Column                              | Description                                                                                          |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `token_address`                     | The deployed token contract address                                                                  |
| `name`                              | ERC-20 token name (raw string; may contain quotes/odd characters)                                    |
| `symbol`                            | ERC-20 token symbol                                                                                  |
| `decimals`                          | ERC-20 decimals — apply at read time to scale `total_supply` and any raw amounts                     |
| `total_supply`                      | Raw `uint256` supply, **no decimals applied** — divide by `10^decimals` for the human-readable value |
| `deployer_address`                  | Address that deployed the contract                                                                   |
| `block_number`, `transaction_index` | Deploy position (the recency tiebreaker for re-deploys)                                              |
| `block_timestamp` / `event_ts`      | Deploy block time                                                                                    |

Token contracts are filtered to real ERC-20 deploys: a contract is kept only if its `symbol` is non-empty and ≤ 100 chars, `decimals` ≤ 50, and `deployer_address` is non-empty.

### Source

The transform reads the per-block `deployedContracts` array, filtered to entries whose `type` contains `TOKEN` (the token-contract slice of the block EVM data). Each surviving entry becomes one row. `deployedContracts` carries no log index, so `transaction_index` is the intra-block tiebreaker — one deploy per `(tx, contract)`.

### Destination

| Destination                  | Table                                                                   | Read pattern                                                                                                                         |
| ---------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **ClickHouse** (first-class) | `fact_token_metadata`                                                   | Prefix scan on `(chain_id, token_address)`; read with `FINAL`, take latest deploy via `argMax(…, (block_number, transaction_index))` |
| **Postgres**                 | `token_metadata` (materialized view over `token_metadata_observations`) | Unique index on `(token_address)`                                                                                                    |
| **MySQL**                    | `token_metadata` (latest-wins trigger state table over observations)    | Primary key on `(token_address)`                                                                                                     |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct. The fact table's sort key is token-first, so a token's metadata is a point lookup. Postgres derives the current-metadata surface as a `DISTINCT ON (token_address)` materialized view; MySQL maintains it incrementally via an `AFTER INSERT` latest-wins trigger.

### Full schema

The complete read table this recipe produces. Keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). `total_supply` is the raw `uint256` stored as text / wide integer (it exceeds standard numeric precision); apply `decimals` at read time for the human-readable value.

<Accordion title="ClickHouse — fact_token_metadata">
  ```sql theme={null}
  CREATE TABLE recipe_token_metadata.fact_token_metadata
  (
      vendor_event_id     String,
      ingested_at         DateTime64(3),
      chain_id            UInt32,
      block_hash          String,
      block_number        UInt64,
      transaction_index   UInt32,
      event_ts            DateTime64(3),
      token_address       String,
      deployer_address    String,
      name                String,
      symbol              String,
      decimals            Int16,
      total_supply        String,                     -- raw uint256, no decimals applied
      sign                Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_token_metadata', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, token_address, block_number, transaction_index, vendor_event_id);
  ```

  The `sign` column drives reorg collapsing — read with `FINAL` or a sign-aware aggregate, and take the latest deploy with `argMax(…, (block_number, transaction_index))`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path. Because metadata is fixed at deploy, there is normally one row per token; the latest-deploy logic only matters for a CREATE2 re-deploy at a reused address.
</Accordion>

<Accordion title="Postgres — token_metadata">
  ```sql theme={null}
  -- 1. Observations (sink target) — append-only, one row per deploy.
  CREATE TABLE public.token_metadata_observations (
    position           BIGINT          NOT NULL,
    transaction_index  BIGINT,
    block_number       BIGINT          NOT NULL,
    block_timestamp    BIGINT          NOT NULL,    -- unix seconds
    tx_hash            TEXT            NOT NULL,
    vendor_event_id    TEXT            NOT NULL,
    token_address      TEXT            NOT NULL,
    deployer_address   TEXT            NOT NULL,
    name               TEXT            NOT NULL,
    symbol             TEXT            NOT NULL,
    decimals           SMALLINT        NOT NULL,
    total_supply       NUMERIC(76, 0)              -- raw uint256, no decimals applied
  );

  -- Speeds the DISTINCT ON (latest-per-token) the materialized view computes.
  CREATE INDEX IF NOT EXISTS tmo_token_recency_idx
    ON public.token_metadata_observations
    (token_address, block_number DESC, transaction_index DESC);

  -- 2. Current-metadata materialized view: latest deploy per token_address.
  CREATE MATERIALIZED VIEW public.token_metadata AS
  SELECT DISTINCT ON (token_address)
    token_address,
    name,
    symbol,
    decimals,
    total_supply,
    block_number,
    deployer_address
  FROM public.token_metadata_observations
  ORDER BY token_address, block_number DESC, transaction_index DESC;

  -- Required by REFRESH MATERIALIZED VIEW CONCURRENTLY (one row per token).
  CREATE UNIQUE INDEX IF NOT EXISTS token_metadata_pk
    ON public.token_metadata (token_address);

  -- Lookup helper.
  CREATE INDEX IF NOT EXISTS token_metadata_symbol_idx
    ON public.token_metadata (symbol);
  ```

  Refresh the view on a schedule: `REFRESH MATERIALIZED VIEW CONCURRENTLY token_metadata;`. `total_supply` is `NUMERIC(76, 0)` — the explicit precision keeps large raw supplies from overflowing. MySQL is the same shape with `DECIMAL(65,0)` for `total_supply` and `VARCHAR(255)` for `name` / `symbol`, maintaining `token_metadata` incrementally via an `AFTER INSERT` latest-wins trigger. `position` is the block-level cursor used during backfill.
</Accordion>

### Example reads

Metadata for one token, latest deploy wins (ClickHouse):

```sql theme={null}
SELECT
  token_address,
  argMax(name,             (block_number, transaction_index)) AS name,
  argMax(symbol,           (block_number, transaction_index)) AS symbol,
  argMax(decimals,         (block_number, transaction_index)) AS decimals,
  argMax(total_supply,     (block_number, transaction_index)) AS total_supply,
  argMax(deployer_address, (block_number, transaction_index)) AS deployer_address
FROM recipe_token_metadata.fact_token_metadata FINAL
WHERE chain_id = 1 AND token_address = lower('0x...')
GROUP BY token_address;
```

All tokens deployed in a block range (ClickHouse):

```sql theme={null}
SELECT token_address, name, symbol, decimals, block_number
FROM recipe_token_metadata.fact_token_metadata FINAL
WHERE chain_id = 1 AND block_number BETWEEN 19000000 AND 19001000
ORDER BY block_number, transaction_index;
```

Current metadata for one token (Postgres, after refreshing the view):

```sql theme={null}
SELECT token_address, name, symbol, decimals, total_supply
FROM public.token_metadata
WHERE token_address = lower('0x...');
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  The Postgres / MySQL realtime reorg path needs a single-column `UNIQUE` on the position column, but `position` is block-level (one block can deploy several token contracts), so array-expanded rows can only carry a composite unique. Run realtime/hybrid on **ClickHouse**, where the collapsing log table corrects reorgs per-block. The Postgres / MySQL configs are intended for `historical` backfill — a once-off metadata census is the dominant use of this recipe anyway.
</Note>

### Multichain

The recipe is chain-parametrized via the `chain` setting — point it at any supported EVM chain. The `vendor_event_id` already includes `chain_id`, `tx_hash`, `transaction_index`, and `token_address`, so rows stay unique without the Solana log-index widening other recipes need. Note that SPL token metadata does not flow through `deployedContracts` the way EVM contract deploys do — this recipe is **EVM-shaped**.

### Fidelity gaps

The core on-chain fields — `token_address`, `name`, `symbol`, `decimals`, `total_supply`, plus `block_number` and `deployer_address` — are fully sourced. A few enrichment fields `GET /erc20/metadata` returns are **not** sourced here, as they come from off-chain or separate pipelines:

* `logo` / `thumbnail` / `logo_hash` — off-chain logo CDN assets.
* `validated` / `possible_spam` / `verified_contract` — Moralis spam & verification heuristics.
* `categories` — editorial token categorisation.
* `created_at` (wall-clock) — this recipe carries on-chain `block_number` / `block_timestamp` instead.

Also note `total_supply` is the **raw** `uint256` with no decimals applied — divide by `10^decimals` for the human-readable supply.

### Related

<Columns cols={2}>
  <Card title="Token Holders" href="/data-feeds/recipes/token/token-holders" icon="users">
    All non-zero holders of a token — pair with metadata for decimals and symbol.
  </Card>

  <Card title="Token Analytics" href="/data-feeds/use-cases/token-analytics" icon="chart-line">
    The use case this metadata census powers — the decimals lookup behind every scaled amount.
  </Card>
</Columns>
