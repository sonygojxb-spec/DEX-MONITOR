> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Logs by Event Signature

> Sync every raw event log of one signature — every Transfer, Approval, or Swap — across all contracts, chain-wide, into your own database. The by-event-type sibling of Contract Logs.

### Question it answers

> "Give me every raw event log of signature **T** (`topic0`), chain-wide, in on-chain order."

The by-event-type mirror of [Contract Logs](/data-feeds/recipes/logs/contract-logs) — the **same** raw-log extraction, but keyed by the event signature (`topic0`) instead of the emitting contract. Use it to index one event **across all contracts**: every `Transfer`, every `Approval`, every Uniswap `Swap` — typically scoped to a block range.

### What you get

One row per log, keyed by event signature. Same columns as Contract Logs — `topic0…topic3`, `data`, `contract_address`, `tx_hash`, and the `(block_number, transaction_index, log_index)` ordering tuple — but `topic0` leads the sort key so a chain-wide "all logs of this signature" read is a contiguous range.

### On-chain ordering

Every destination is keyed `topic0` first, then the on-chain tuple:

* **ClickHouse** — `ORDER BY (chain_id, topic0, block_number, transaction_index, log_index, …)`. `topic0` is low cardinality (one value per signature), so it's a cheap, highly selective leading key.
* **Postgres / MySQL** — a composite index on `(topic0, block_number, transaction_index, log_index)`; `WHERE topic0 = T AND block_number BETWEEN … ORDER BY …` is answered by an index range scan with no filesort.

Logs with an empty `topic0` (anonymous events) are filtered out — they have no signature to key on.

### Optional: scope to a contract (topic0 + contract)

The primary key leads with `topic0`, so "all `Transfer` logs emitted by contract X" prefix-scans to the signature and filters `contract_address` within it. Because a popular signature (`Transfer`, `Approval`) spans **millions of contracts**, an opt-in `(topic0, contract_address, …)` structure makes that read a tight `(topic0, contract)` range that stays sort-free *and* skips the signature's other contracts. Shipped **commented-out** in each schema:

| Destination | Optional structure                                                                                                                               |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Postgres    | `CREATE INDEX … (topic0, contract_address, block_number, transaction_index, log_index)`                                                          |
| MySQL       | `ADD KEY (topic0, contract_address, block_number, transaction_index, log_index)`                                                                 |
| ClickHouse  | A `contract_address` `bloom_filter` skip-index (light), or a projection sorted by `(chain_id, topic0, contract_address, …)` (sort-free, heavier) |

### Destination

| Destination                  | Table        | By-signature access                                                    |
| ---------------------------- | ------------ | ---------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_logs`  | Prefix scan on `(chain_id, topic0, …)`; read with `FINAL`              |
| **Postgres**                 | `topic_logs` | Composite index `(topic0, block_number, transaction_index, log_index)` |
| **MySQL**                    | `topic_logs` | Composite key `(topic0, block_number, transaction_index, log_index)`   |

Same source and reorg model as Contract Logs (raw `block` array → `itemType = 'log'`, `tx_hash` recovered from the sibling transaction row; immutable append-only logs in a collapsing table).

### Full schema

Identical columns to [Contract Logs](/data-feeds/recipes/logs/contract-logs#full-schema) — the only difference is the sort key leads with `topic0`. Keep the columns you need (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)).

<Accordion title="ClickHouse — fact_logs (topic0-keyed)">
  ```sql theme={null}
  CREATE TABLE recipe_logs_by_topic0.fact_logs
  (
      vendor_event_id   String,
      ingested_at       DateTime64(3),
      chain_id          UInt32,
      block_hash        String,
      block_number      UInt64,
      transaction_index UInt32,
      log_index         UInt32,
      event_ts          DateTime64(3),
      tx_hash           String,
      contract_address  String,
      topic0            String,
      topic1            Nullable(String),
      topic2            Nullable(String),
      topic3            Nullable(String),
      data              Nullable(String),   -- raw ABI-encoded payload (hex)
      sign              Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_logs', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, topic0, block_number, transaction_index, log_index, vendor_event_id);

  -- OPTIONAL (commented out by default): accelerate "specific contract within a
  -- signature" reads. Enable at most one.
  -- (a) lightweight contract_address skip-index:
  -- ALTER TABLE recipe_logs_by_topic0.fact_logs
  --   ADD INDEX idx_contract contract_address TYPE bloom_filter GRANULARITY 4;
  -- (b) sort-free projection keyed (topic0, contract_address, …):
  -- ALTER TABLE recipe_logs_by_topic0.fact_logs
  --   ADD PROJECTION proj_topic0_contract
  --   (SELECT * ORDER BY (chain_id, topic0, contract_address, block_number, transaction_index, log_index));
  ```

  Postgres / MySQL mirror this as a flat `topic_logs` table keyed `(topic0, block_number, transaction_index, log_index)`, with the optional `(topic0, contract_address, …)` index commented out.
</Accordion>

### Example reads

All logs of an event signature in a block range, in on-chain order (ClickHouse):

```sql theme={null}
SELECT block_number, transaction_index, log_index, contract_address,
       tx_hash, topic1, topic2, topic3, data
FROM recipe_logs_by_topic0.fact_logs FINAL
WHERE chain_id = 1
  AND topic0 = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
  AND block_number BETWEEN 18000000 AND 18010000
ORDER BY block_number, transaction_index, log_index
LIMIT 100;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`**, **Postgres / MySQL `historical`**. For live/reorg-safe ingestion use ClickHouse.

<Warning>
  A `topic0`-keyed sync is heavy for popular signatures — `Transfer` and `Approval` span the whole chain. Scope reads to a block range, and for chain-heavy backfills run the ClickHouse path.
</Warning>

### EVM only

Like Contract Logs, this extracts EVM event logs (`topic0…3` + `data`); Solana program logs are a different model.

### Related

<Columns cols={2}>
  <Card title="Contract Logs" href="/data-feeds/recipes/logs/contract-logs" icon="file-lines">
    The sibling — every log from one contract, keyed by emitter.
  </Card>

  <Card title="Onchain Event Indexing" href="/data-feeds/use-cases/event-indexing" icon="cube">
    The use case these raw-log recipes power.
  </Card>
</Columns>
