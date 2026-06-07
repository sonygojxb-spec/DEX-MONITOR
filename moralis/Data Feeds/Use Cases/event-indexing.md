> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Onchain Event Indexing

> A Data Feeds recipe bundle for indexing raw event logs — every event from a contract, or one event signature across all contracts — into your own database for custom decoding and analytics.

### Who it's for

Teams that need **raw onchain events** in their own database — protocol teams indexing their own contracts, analytics platforms building chain-wide event feeds, and data teams covering **custom or non-standard events** that the decoded endpoints don't model. The output is a complete, ordered, reorg-safe log table you decode against your own ABIs.

### Raw logs vs decoded recipes

Data Feeds ships two kinds of event data. Reach for raw logs when the decoded path doesn't cover what you need:

| Use…                                                                         | When                                                                                                                                                             |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Decoded recipes** (Token Transfers, Token Approvals, Swaps, NFT Transfers) | The event is a standard, already-decoded type — you want typed columns, no ABI decoding.                                                                         |
| **Raw log recipes** (this use case)                                          | A custom/unsupported contract or event, or you want *every* event a contract emits, or one signature chain-wide — and you'll decode `data` against your own ABI. |

### The recipe bundle

| Recipe                                                             | Role                                                                                                                                                                                            |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Contract Logs](/data-feeds/recipes/logs/contract-logs)            | Every raw event log emitted by a specific contract, in on-chain order. The "index my protocol's contracts" path. Optional `(contract, topic0)` grouping for high-volume contracts.              |
| [Logs by Event Signature](/data-feeds/recipes/logs/logs-by-topic0) | One event signature (`topic0`) across **all** contracts, chain-wide — every `Transfer`, `Approval`, `Swap`, etc. The "index one event everywhere" path. Optional `(topic0, contract)` grouping. |

### Two access patterns

```
Contract Logs            Logs by Event Signature
  key: contract_address    key: topic0
  "everything contract      "this event across
   X emitted"                all contracts"
```

* **By contract** — point Contract Logs at your protocol's addresses and get a complete, ordered event log per contract. Decode in your application against the contract ABI.
* **By event signature** — point Logs by Event Signature at a `topic0` and capture that event chain-wide. Because popular signatures (`Transfer`, `Approval`) span the whole chain, scope reads to a block range. Enable the optional `(topic0, contract)` grouping when you frequently narrow to specific contracts within a signature.

### Decoding the payload

Both recipes are intentionally raw: `topic0` is the event signature hash, `topic1…topic3` are the indexed parameters, and `data` is the ABI-encoded non-indexed payload as hex. Decode `data` (and interpret the indexed topics) against the event ABI in your application — Data Feeds delivers the complete, ordered, reorg-safe primitives; the decode layer stays under your control.

### Notes and considerations

* **EVM only.** Raw log extraction covers EVM event logs (`topic0…3` + `data`). Solana program logs are a different model.
* **Heavier source.** Logs come from the wide raw `block` data (all logs and transactions per block), so per-block volume is higher than the compact decoded recipes. `tx_hash` is recovered by joining each log to its sibling transaction row; drop that join if you don't need it.
* **Scope popular signatures.** A chain-wide `Transfer`/`Approval` feed is large — bound it to a block range and run the ClickHouse path for live, reorg-safe ingestion.
* **Pair with decoded recipes.** Use raw logs for the long tail and custom events; use the decoded recipes where a typed, ready-made shape already exists.

### Get started

Data Feeds is in early access.

<Card title="Request Early Access" icon="rocket" href="/data-feeds/early-access">
  Index any contract or event into your own infrastructure with the Moralis team.
</Card>
