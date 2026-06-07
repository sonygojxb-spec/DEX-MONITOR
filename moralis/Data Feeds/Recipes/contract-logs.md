> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Contract Logs

> Sync every raw event log emitted by a contract — all topics and raw data, in on-chain order — into your own database. Mirrors the Moralis GET /{address}/logs endpoint.

### Question it answers

> "Give me every raw event log emitted by contract **0x…**, in on-chain order." Mirrors Moralis `GET /{address}/logs`.

This is the **raw** event log — `topic0…topic3` plus the ABI-encoded `data` payload — keyed by the emitting contract. Unlike the decoded recipes (Token Transfers, Token Approvals, Swaps), it does not decode event names or arguments; you decode `data` in your application against the contract's ABI. Use it to index **any contract's events**, including custom or non-standard ones the decoded recipes don't cover.

### What you get

One row per log, keyed by the emitting contract:

| Column                                           | Description                                                                    |
| ------------------------------------------------ | ------------------------------------------------------------------------------ |
| `contract_address`                               | The emitting contract (the log's address)                                      |
| `block_number`, `transaction_index`, `log_index` | On-chain ordering tuple                                                        |
| `tx_hash`                                        | Transaction that produced the log                                              |
| `topic0`                                         | Event signature hash (`keccak256` of the canonical signature) — always present |
| `topic1`, `topic2`, `topic3`                     | Indexed event parameters; `NULL` when the log has fewer topics                 |
| `data`                                           | Raw, ABI-encoded, non-indexed payload as hex — decode in your app              |
| `block_timestamp`                                | Block time                                                                     |

### On-chain ordering

A log's canonical position is the tuple **`(block_number, transaction_index, log_index)`** — block height, then the transaction's position in the block, then the log's index within the transaction. Every destination is keyed `contract_address` first, then that tuple, so "all logs for a contract, in order" is a sort-free range scan:

* **ClickHouse** — `ORDER BY (chain_id, contract_address, block_number, transaction_index, log_index, …)`; a prefix scan returns rows already ordered.
* **Postgres / MySQL** — a composite index on `(contract_address, block_number, transaction_index, log_index)` answers the read with no filesort step.

### Optional: group by event signature (topic0)

The primary key already leads with `contract_address`, so "all `Transfer` logs for contract X" prefix-scans to the contract and filters `topic0` within it. On a **high-volume contract that emits many event types**, an opt-in `(contract_address, topic0, …)` structure makes that read a tight `(contract, topic0)` range that stays sort-free *and* skips the contract's other event types.

These are shipped **commented-out** in each schema (extra write cost + storage) — uncomment to enable:

| Destination | Optional structure                                                                                                                     |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Postgres    | `CREATE INDEX … (contract_address, topic0, block_number, transaction_index, log_index)`                                                |
| MySQL       | `ADD KEY (contract_address, topic0, block_number, transaction_index, log_index)`                                                       |
| ClickHouse  | A `topic0` `bloom_filter` skip-index (light), or a projection sorted by `(chain_id, contract_address, topic0, …)` (sort-free, heavier) |

### Source

Raw logs aren't a decoded entity array — they live in the flattened `block` raw-passthrough array, where each block is expanded into items discriminated by `itemType` (`log` / `transaction` / …). The transform `ARRAY JOIN`s `block`, keeps `itemType = 'log'`, and lands one row per log. A log row carries **no transaction hash**, so `tx_hash` is recovered by joining each log to its sibling `itemType = 'transaction'` row on `(block_number, transaction_index)`.

### Destination

| Destination                  | Table           | By-contract access                                                               |
| ---------------------------- | --------------- | -------------------------------------------------------------------------------- |
| **ClickHouse** (first-class) | `fact_logs`     | Prefix scan on `(chain_id, contract_address, …)`; read with `FINAL`              |
| **Postgres**                 | `contract_logs` | Composite index `(contract_address, block_number, transaction_index, log_index)` |
| **MySQL**                    | `contract_logs` | Composite key `(contract_address, block_number, transaction_index, log_index)`   |

Logs are immutable append-only events, so the ClickHouse fact table is a plain collapsing table — each log is one row, and a chain reorganization cancels it via the companion log table. There's no latest-wins logic; every log is a distinct row.

### Full schema

The complete read table. Keep the columns you need; `topic1…topic3` and `data` are nullable raw fields you decode in your app (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)).

<Accordion title="ClickHouse — fact_logs (contract-keyed)">
  ```sql theme={null}
  CREATE TABLE recipe_logs_by_contract.fact_logs
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
  ORDER BY (chain_id, contract_address, block_number, transaction_index, log_index, vendor_event_id);

  -- OPTIONAL (commented out by default): accelerate "specific event type for this
  -- contract" reads on high-volume contracts. Enable at most one.
  -- (a) lightweight topic0 skip-index:
  -- ALTER TABLE recipe_logs_by_contract.fact_logs
  --   ADD INDEX idx_topic0 topic0 TYPE bloom_filter GRANULARITY 4;
  -- (b) sort-free projection keyed (contract_address, topic0, …):
  -- ALTER TABLE recipe_logs_by_contract.fact_logs
  --   ADD PROJECTION proj_contract_topic0
  --   (SELECT * ORDER BY (chain_id, contract_address, topic0, block_number, transaction_index, log_index));
  ```

  Postgres / MySQL mirror this as a flat `contract_logs` table with a composite index `(contract_address, block_number, transaction_index, log_index)` and the optional `(contract_address, topic0, …)` index commented out.
</Accordion>

### Example reads

All logs emitted by a contract, in on-chain order (ClickHouse):

```sql theme={null}
SELECT block_number, transaction_index, log_index, tx_hash,
       topic0, topic1, topic2, topic3, data
FROM recipe_logs_by_contract.fact_logs FINAL
WHERE chain_id = 1 AND contract_address = lower('0x...')
ORDER BY block_number, transaction_index, log_index
LIMIT 100;
```

Only a specific event type (`0xddf2…` = `keccak("Transfer(address,address,uint256)")`):

```sql theme={null}
SELECT block_number, transaction_index, log_index, tx_hash, topic1, topic2, data
FROM recipe_logs_by_contract.fact_logs FINAL
WHERE chain_id = 1 AND contract_address = lower('0x...')
  AND topic0 = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
ORDER BY block_number, transaction_index, log_index
LIMIT 100;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`**, **Postgres / MySQL `historical`**. For live/reorg-safe ingestion use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  This recipe reads the wide raw `block` column (every log **and** transaction per block), so per-block bytes are higher than the decoded recipes. The transaction rows are read only to recover `tx_hash` — drop that join if you don't need it.
</Note>

### EVM only

Contract Logs extracts EVM event logs (`topic0…3` + `data`). Solana program logs are a different model and aren't emitted into this array.

### Fidelity gaps

Raw on-chain log primitives — emitter, all topics, raw data, block, tx hash, on-chain ordering — are fully covered. Fields with no onchain source are omitted: `decoded_event` (needs the contract ABI — decode in your app) and transaction receipt fields beyond `tx_hash`.

### Related

<Columns cols={2}>
  <Card title="Logs by Event Signature" href="/data-feeds/recipes/logs/logs-by-topic0" icon="layer-group">
    The sibling — index one event type across all contracts.
  </Card>

  <Card title="Onchain Event Indexing" href="/data-feeds/use-cases/event-indexing" icon="cube">
    The use case these raw-log recipes power.
  </Card>
</Columns>
