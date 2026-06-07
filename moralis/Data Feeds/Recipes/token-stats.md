> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Stats

> Maintain per-token transfer counters — how many transfers a token has had — as a continuous, reorg-safe aggregate in your own database. Mirrors the Moralis GET /erc20/{address}/stats endpoint.

### Question it answers

> "How many transfers has token **0x…** had?" Mirrors Moralis `GET /erc20/{address}/stats` (`{ transfers: { total } }`).

Each ERC-20 transfer event contributes `+1` to that token's counter. The shape is intentionally compact — one counter today — but the **pattern** is the value: fold any future per-token counter (holder-count delta, daily active addresses, …) onto the same row so a single read returns the full stats block for a token.

### What you get

One aggregated row per token, keyed by `token_address`:

| Column            | Description                                                    |
| ----------------- | -------------------------------------------------------------- |
| `chain_id`        | The chain the token lives on                                   |
| `token_address`   | The ERC-20 contract address (the counter key)                  |
| `transfers_total` | Net count of transfer events for the token — `transfers.total` |

`transfers_total` counts every row in the source transfer array, **including mints (`from = 0x0`) and burns (`to = 0x0`)** — matching the endpoint's "transfers of the token" semantics. See [Counter semantics](#counter-semantics) to exclude mints/burns.

### Source

The transform reads one per-block array and counts it:

`tokenTransfers`

This is by definition the ERC-20 transfer event collection (NFT and native transfers are separate arrays — `nftTokenTransfers`, `nativeTransfers`), so no token-standard filter is needed. Each event contributes `+1` to `transfers_total` for its `token_address`. `block_number` / `block_timestamp` come from the block envelope.

### Destination

| Destination                  | Table                                                           | Read pattern                                                                          |
| ---------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_token_stats`                                              | `ORDER BY (chain_id, token_address)`; net count via `sum(transfers_total)` or `FINAL` |
| **Postgres**                 | `token_stats` (materialized view over `token_transfer_events`)  | Unique index `(token_address)`                                                        |
| **MySQL**                    | `token_stats` (trigger-maintained over `token_transfer_events`) | Primary key `(token_address)`                                                         |

ClickHouse uses a **SummingMergeTree** counter table (not the collapsing pattern most recipes use): the table is keyed by `(chain_id, token_address)`, so every event for a token shares one key and the engine **sums** the per-event rows on background merges. The materialized view emits `transfers_total = sign` per event — `+1` for forward inserts, `-1` for reorg reverts — so the per-token sum is always the net count and is naturally reorg-safe.

### Full schema

Below is the complete read table this recipe produces. It's deliberately minimal — one counter — and is a starting point for the forward-compatible counter pattern: add more summable columns to land more per-token stats on the same row (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)).

<Accordion title="ClickHouse — fact_token_stats">
  ```sql theme={null}
  CREATE TABLE recipe_token_stats.fact_token_stats
  (
      chain_id          UInt32,
      token_address     String,
      transfers_total   Int64
  )
  ENGINE = ReplicatedSummingMergeTree(
      '/clickhouse/tables/{database}/fact_token_stats', '{replica}')
  ORDER BY (chain_id, token_address);
  ```

  SummingMergeTree sums every numeric column that isn't part of the `ORDER BY` tuple, so adding a new counter is just another `Int64` / `UInt64` column plus a projection branch in the materialized view — no engine change. Read the net counter with `sum(transfers_total)` or `FINAL` (which forces the merge first); **never** a bare `WHERE sign = 1`. A single-node setup can use `SummingMergeTree()` without the replication path.
</Accordion>

<Accordion title="Postgres — token_stats">
  ```sql theme={null}
  -- 1. Transfer events (sink target).
  CREATE TABLE public.token_transfer_events (
    position         BIGINT  NOT NULL,
    log_index        BIGINT  NOT NULL,
    block_number     BIGINT  NOT NULL,
    block_timestamp  BIGINT  NOT NULL,         -- unix seconds
    tx_hash          TEXT    NOT NULL,
    token_address    TEXT    NOT NULL,
    vendor_event_id  TEXT    NOT NULL
  );

  -- Row-uniqueness for idempotent ingestion.
  CREATE UNIQUE INDEX IF NOT EXISTS token_transfer_events_uq_event
    ON public.token_transfer_events (vendor_event_id);

  -- Per-token grouping index — lets the view's GROUP BY do an index scan, not a sort.
  CREATE INDEX IF NOT EXISTS token_transfer_events_token_idx
    ON public.token_transfer_events (token_address);

  -- 2. Per-token counter materialized view.
  CREATE MATERIALIZED VIEW public.token_stats AS
  SELECT
    token_address,
    COUNT(*)::BIGINT AS transfers_total
  FROM public.token_transfer_events
  GROUP BY token_address;

  CREATE UNIQUE INDEX IF NOT EXISTS token_stats_pk
    ON public.token_stats (token_address);
  ```

  Refresh on a schedule: `REFRESH MATERIALIZED VIEW CONCURRENTLY token_stats;`. MySQL keeps the same `token_transfer_events` table plus a trigger-maintained `token_stats` state table doing `INSERT … ON DUPLICATE KEY UPDATE transfers_total = transfers_total + 1`. Add another aggregate column to the view (Postgres) or another trigger column (MySQL) to land more counters.
</Accordion>

### Example reads

Per-token transfer counters on chain 1, most-transferred first — `sum()` is reorg-safe (ClickHouse):

```sql theme={null}
SELECT token_address,
       sum(transfers_total) AS transfers_total
FROM recipe_token_stats.fact_token_stats
WHERE chain_id = 1
GROUP BY token_address
ORDER BY transfers_total DESC
LIMIT 10;
```

A single token — this is the read that mirrors `GET /erc20/{address}/stats`:

```sql theme={null}
SELECT sum(transfers_total) AS transfers_total
FROM recipe_token_stats.fact_token_stats
WHERE chain_id = 1
  AND token_address = lower('0x...');
```

Same query via `FINAL` (forces the background merge first; identical result):

```sql theme={null}
SELECT token_address, transfers_total
FROM recipe_token_stats.fact_token_stats FINAL
WHERE chain_id = 1
ORDER BY transfers_total DESC
LIMIT 10;
```

### Counter semantics

`transfers_total` includes **mints and burns**, matching the endpoint's "transfers of the token" definition — every `+1` of supply movement is counted, with no `from = 0x0` / `to = 0x0` filter. The ClickHouse fact table carries only the aggregated counter, so to exclude mints/burns query the Postgres/MySQL event table (which retains per-event rows) — or add `from`/`to` columns to the transform and event-table schema if you need that surface in ClickHouse:

```sql theme={null}
-- Postgres: counts excluding mints + burns (requires from/to columns on the event table).
SELECT token_address, COUNT(*) AS transfers_total
FROM public.token_transfer_events
WHERE token_address = lower('0x...')
GROUP BY token_address;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live, reorg-corrected counters, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  On Postgres / MySQL the counter **only ever increments** in `historical` mode — there is no reorg-safe row-deletion path on these destinations, and the per-event `vendor_event_id` uniqueness only guards against double-ingestion of the same canonical event. `position` is block-level and array-expanded transfer rows share it, which constrains realtime/hybrid here. Run realtime/hybrid on **ClickHouse**, which corrects reorgs per-block via signed `-1` rows.
</Note>

### Multichain

The recipe is chain-parametrized via the `chain` setting — point it at any supported EVM chain or Solana. On Solana, every SPL token transfer contributes `+1`; the `vendor_event_id` is widened to stay unique even where a log index repeats within an instruction, so per-token counts round-trip identically in shape.

### Related

<Columns cols={2}>
  <Card title="Token Transfers" href="/data-feeds/recipes/token/token-transfers" icon="arrow-right-arrow-left">
    The per-event transfer ledger this counter is derived from.
  </Card>

  <Card title="Token Analytics" href="/data-feeds/use-cases/token-analytics" icon="chart-line">
    The use case per-token stats power.
  </Card>
</Columns>
