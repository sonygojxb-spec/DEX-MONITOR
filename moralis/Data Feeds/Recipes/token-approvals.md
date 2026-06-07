> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Approvals

> Sync the current ERC-20 allowances a wallet has granted — and to whom — as a continuous, reorg-safe feed into your own database. Mirrors the Moralis GET /wallets/{address}/approvals endpoint.

### Question it answers

> "What ERC-20 allowances has wallet **0x…** granted, and to whom?" Mirrors Moralis `GET /wallets/{address}/approvals`.

Each ERC-20 `Approval(owner, spender, value)` log is one approval event. The **current allowance** for an `(owner, token, spender)` triple is the latest approval by `(block_number, log_index)` — a fresh `approve` overwrites the prior allowance (latest-wins, the same machinery as the balances recipes). A revoke is just `approve(spender, 0)`, so it lands as a new event whose value is `'0'`.

### What you get

One row per approval event, keyed by the approving wallet (`owner_address`). The **current** allowance for a triple is the latest event, resolved with `argMax` (ClickHouse) or a latest-wins projection (Postgres / MySQL):

| Column                         | Description                                                                                        |
| ------------------------------ | -------------------------------------------------------------------------------------------------- |
| `owner_address`                | The approving wallet (the `owner` on the `Approval` log)                                           |
| `spender_address`              | The address authorized to spend                                                                    |
| `token_address`                | The ERC-20 token the allowance is for                                                              |
| `value`                        | The raw allowance amount — stored as text (an unlimited approve is `type(uint256).max`, 78 digits) |
| `block_number`, `log_index`    | On-chain ordering tuple; the latest pair per triple wins                                           |
| `tx_hash`                      | Transaction that produced the approval                                                             |
| `event_ts` / `block_timestamp` | Block time                                                                                         |

Compare `value` against `'0'` for the revoked / non-revoked distinction; do any arbitrary-precision arithmetic in your application layer.

### Source

The transform reads a single per-block array and lands one row per approval log:

`tokenApprovals`

The struct carries `approverAddress` (→ `owner_address`), `spenderAddress`, `tokenAddress`, and `amount` (→ `value`); `block_number` and `block_timestamp` come from the block envelope.

### Destination

| Destination                  | Table                                                               | Read pattern                                                                                                                                                 |
| ---------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **ClickHouse** (first-class) | `fact_token_approvals`                                              | Prefix scan on `(chain_id, owner_address, token_address, spender_address, …)`; current allowance via `argMax(value, (block_number, log_index))` over `FINAL` |
| **Postgres**                 | `token_approval_events` + `token_allowances` materialized view      | Partial index `(owner_address, token_address, spender_address) WHERE value <> '0'`                                                                           |
| **MySQL**                    | `token_approval_events` + maintained `token_allowances` state table | PK `(owner_address, token_address, spender_address)` with `value = '0'` cleanup                                                                              |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct. The fact table's sort key is owner-first, so "all allowances granted by owner Y" is a contiguous range read. Postgres keeps a flat event table plus a `token_allowances` materialized view (latest approve per triple, refreshed on a schedule); MySQL keeps the same event table plus a latest-wins state table.

### Full schema

Below is the complete read table this recipe produces — keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). The raw allowance `value` is stored as text on all three destinations: an unlimited approve uses `type(uint256).max` (78 digits), which overflows Postgres `NUMERIC(76,0)` and MySQL `DECIMAL(65,0)`.

<Accordion title="ClickHouse — fact_token_approvals">
  ```sql theme={null}
  CREATE TABLE recipe_token_approvals.fact_token_approvals
  (
      vendor_event_id   String,
      ingested_at       DateTime64(3),
      chain_id          UInt32,
      block_hash        String,
      block_number      UInt64,
      log_index         UInt32,
      event_ts          DateTime64(3),
      tx_hash           String,
      token_address     String,
      owner_address     String,
      spender_address   String,
      value             String,                 -- raw allowance; unlimited approve = uint256 max (78 digits)
      sign              Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_token_approvals', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, owner_address, token_address, spender_address, block_number, log_index, vendor_event_id);
  ```

  The `sign` column drives reorg collapsing. Read the current allowance with `argMax(value, (block_number, log_index))` over `FINAL` — never a bare `WHERE sign = 1`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
</Accordion>

<Accordion title="Postgres — token_approval_events + token_allowances">
  ```sql theme={null}
  -- 1. Approval events (sink target) — one row per Approval log.
  CREATE TABLE public.token_approval_events (
    position         BIGINT  NOT NULL,
    log_index        BIGINT  NOT NULL,
    block_number     BIGINT  NOT NULL,
    block_timestamp  BIGINT  NOT NULL,          -- unix seconds
    tx_hash          TEXT    NOT NULL,
    token_address    TEXT    NOT NULL,
    owner_address    TEXT    NOT NULL,
    spender_address  TEXT    NOT NULL,
    value            TEXT    NOT NULL,           -- allowance; max-uint = 78 digits
    vendor_event_id  TEXT    NOT NULL
  );

  -- Recency index leading with the DISTINCT ON keys so REFRESH avoids a sort.
  CREATE INDEX tae_owner_token_spender_recency_idx
    ON public.token_approval_events
    (owner_address, token_address, spender_address, block_number DESC, log_index DESC);

  -- 2. Current-allowance materialized view: latest approve per (owner, token, spender).
  CREATE MATERIALIZED VIEW public.token_allowances AS
  SELECT DISTINCT ON (owner_address, token_address, spender_address)
    owner_address, token_address, spender_address,
    value, tx_hash, block_number, log_index, block_timestamp
  FROM public.token_approval_events
  ORDER BY owner_address, token_address, spender_address, block_number DESC, log_index DESC;

  CREATE UNIQUE INDEX token_allowances_pk
    ON public.token_allowances (owner_address, token_address, spender_address);

  -- Primary access path: all live allowances granted by an owner.
  CREATE INDEX token_allowances_by_owner_active_idx
    ON public.token_allowances (owner_address, token_address, spender_address)
    WHERE value <> '0';

  -- Sibling access path: who can spend a given token on behalf of others.
  CREATE INDEX token_allowances_by_spender_idx
    ON public.token_allowances (spender_address, token_address);
  ```

  MySQL is the same shape with `VARCHAR(80)` for `value` and a trigger-maintained `token_allowances` state table doing the latest-wins upsert. `position` is the block-level cursor used during backfill.
</Accordion>

### Example reads

All current allowances granted by an owner — latest approve per token + spender, dropping revoked (`'0'`) rows (ClickHouse):

```sql theme={null}
SELECT token_address,
       spender_address,
       argMax(value, (block_number, log_index)) AS current_allowance
FROM recipe_token_approvals.fact_token_approvals FINAL
WHERE chain_id = 1 AND owner_address = lower('0x...')
GROUP BY token_address, spender_address
HAVING current_allowance != '0' AND current_allowance != ''
ORDER BY token_address, spender_address;
```

Postgres — refresh the projection, then read the live allowances:

```sql theme={null}
REFRESH MATERIALIZED VIEW CONCURRENTLY token_allowances;

SELECT token_address, spender_address, value
FROM public.token_allowances
WHERE owner_address = lower('0x...') AND value <> '0'
ORDER BY token_address, spender_address;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  Realtime / hybrid on Postgres / MySQL is constrained: the block-level cursor means array-expanded approval rows share a `position`, which collides with the single-column `UNIQUE` requirement. Run realtime / hybrid on **ClickHouse**, which corrects reorgs per-block via the collapsing log table; the Postgres / MySQL configs target `historical` backfill.
</Note>

### EVM only

`tokenApprovals` is an EVM ERC-20 `Approval` log array. SPL token delegation on Solana is a different model and is not emitted into this array.

### Fidelity gaps

On-chain primitives — owner, spender, token, raw allowance value, block, and tx hash — are fully covered. Response fields of `GET /wallets/{address}/approvals` with no on-chain source are intentionally omitted:

* `value_formatted` — needs token `decimals`; scale `value` by `10^token_decimals` using a Token Metadata sync.
* `token.name` / `token.symbol` / `token.logo` / `token.decimals` — token metadata, not in `tokenApprovals`.
* `spender.entity` / `spender.entity_logo` / `spender.address_label` — off-chain spender labelling.

### Related

<Columns cols={2}>
  <Card title="Wallet History" href="/data-feeds/recipes/wallet/wallet-history" icon="clock-rotate-left">
    The full chronological event feed — approvals included alongside transfers and swaps.
  </Card>

  <Card title="Compliance & AML" icon="shield-check">
    Outstanding allowances are a core risk surface for wallet monitoring.
  </Card>
</Columns>
