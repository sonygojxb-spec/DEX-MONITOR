> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Data Feeds Recipes

> Pre-built blueprints that reconstruct Moralis's most popular endpoints — wallet history, balances, prices, swaps, holders — as continuous syncs into your own ClickHouse, Postgres, or MySQL.

### What a recipe is

A **recipe** is a ready-made blueprint that reconstructs one popular Moralis endpoint as a continuous sync into a database you own. Instead of calling an API per request, you run the recipe once and the data lands — and stays current — in your own ClickHouse, Postgres, or MySQL.

Each recipe ships everything you need to run it:

<Columns cols={3}>
  <Card title="Sync config" icon="gear-code">
    The source data, the projection that shapes it, and the destination wiring.
  </Card>

  <Card title="Schema" icon="table-list">
    The destination DDL — tables, indexes, and materialized views.
  </Card>

  <Card title="Queries" icon="magnifying-glass">
    The exact reads that answer the endpoint's question.
  </Card>
</Columns>

Recipes are **blueprints, not turnkey deployments** — they show the projection, schema, index layout, and reorg strategy for each access pattern. Lift the pieces you need.

### How a recipe works

Every recipe is the same three-stage pipeline:

```
Data Feeds source  →  transform (projection)  →  your database
```

1. **Source** — normalized per-block data from Data Feeds. One block carries arrays of every event type (token transfers, native transfers, NFT transfers, swaps, approvals, price updates, and more).
2. **Transform** — a projection that expands the arrays you care about into one row per event and shapes them into the endpoint's schema.
3. **Destination** — the rows land in your database, indexed for the access pattern the endpoint serves (by wallet, by token, by pair, …).

The same source event stream can land **different ways** for different questions — e.g. "balances by wallet" and "balances by token" are the same sync with a different sort key.

### Schema & flexibility

Every recipe page includes a **full schema** — the complete set of columns that access pattern can produce — but nothing about it is fixed. Recipes are blueprints you shape to your needs:

* **Select the columns you want.** Start from the full wide table and keep only the fields your app reads. The projection pulls just the source fields behind the columns you keep, so trimming the schema trims the work.
* **Select the events you want.** Multi-event recipes (like [Wallet History](/data-feeds/recipes/wallet/wallet-history)) union several event types into one table — drop the branches you don't need.
* **Choose your keys and indexes.** The sort key and indexes are tuned for the headline access pattern; re-key for yours. Optional structures (like the by-`topic0` grouping on the [log recipes](/data-feeds/recipes/logs/contract-logs)) ship commented-out — enable them only when you need them.
* **Pick your destination types.** Adjust column types to fit your warehouse. The shipped DDL flags where precision matters — raw `uint256` amounts as text, USD as wide decimals.

In other words: the full schema is a **starting point, not a contract**. Take the complete shape and pare it down.

### Destinations

Recipes support three destinations. **ClickHouse is the first-class path** — it's the only one that handles live, reorg-safe ingestion:

| Destination    | Best for                                        | Realtime / reorg-safe                                |
| -------------- | ----------------------------------------------- | ---------------------------------------------------- |
| **ClickHouse** | Production, large windows, live tailing         | ✅ Yes — corrects chain reorganizations automatically |
| **Postgres**   | Historical backfill, analytics, smaller windows | Backfill-first                                       |
| **MySQL**      | Historical backfill, existing MySQL stacks      | Backfill-first                                       |

ClickHouse recipes use a **collapsing log-table** pattern: events land in a wide table, and a companion log table carries one signed row per block. When the chain reorganizes, the log emits a counter-row and ClickHouse collapses the pair on merge — so your tables converge on canonical state without manual cleanup. Read canonical state with `FINAL` or a sign-aware aggregate, never a bare `WHERE sign = 1`.

Postgres and MySQL recipes write flat, uniquely-keyed event tables and are **first-class for historical backfill**. For live/reorg-safe ingestion on these shapes, use ClickHouse.

### Modes

| Mode         | What it does                                  | Default for      |
| ------------ | --------------------------------------------- | ---------------- |
| `historical` | One-shot backfill of a block window           | Postgres / MySQL |
| `realtime`   | Live tail from the chain head                 | —                |
| `hybrid`     | Backfill, then a seamless handoff to realtime | ClickHouse       |

### Token Prices is the connective tissue

Any "what is this worth in USD" question — a transfer's value, a portfolio's worth, a trade's notional — needs prices. The [Token Prices](/data-feeds/recipes/token/token-prices) recipe is the shared join target across the accounting, portfolio, and trading use cases. Several recipes (like [Wallet History](/data-feeds/recipes/wallet/wallet-history)) also fold per-block USD values inline so common reads need no extra join.

### Recipe catalogue

Recipes are grouped by the kind of data they serve. ⭐ marks the most popular endpoints.

| Domain              | Recipe                                                                            | Answers                                             |
| ------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------- |
| **Wallet**          | [Wallet History](/data-feeds/recipes/wallet/wallet-history) ⭐                     | Every event a wallet was involved in                |
|                     | [Token Balances by Wallet](/data-feeds/recipes/wallet/token-balances-by-wallet) ⭐ | Every token a wallet holds, with balance            |
|                     | [Native Balances](/data-feeds/recipes/wallet/native-balances)                     | Native-asset balance per wallet                     |
|                     | [NFTs by Wallet](/data-feeds/recipes/wallet/nfts-by-wallet) ⭐                     | Every NFT a wallet holds                            |
|                     | [Token Approvals](/data-feeds/recipes/wallet/token-approvals)                     | Current allowances a wallet has granted             |
| **Token**           | [Token Prices](/data-feeds/recipes/token/token-prices) ⭐                          | USD/native mark history for a token                 |
|                     | [Token Holders](/data-feeds/recipes/token/token-holders) ⭐                        | All non-zero holders of a token                     |
|                     | [Token Balances by Token](/data-feeds/recipes/token/token-balances-by-token)      | Holder balances, keyed by token                     |
|                     | [Token Transfers](/data-feeds/recipes/token/token-transfers)                      | Every transfer of a token                           |
|                     | [Token Stats](/data-feeds/recipes/token/token-stats)                              | Per-token transfer counters                         |
|                     | [Token Metadata](/data-feeds/recipes/token/token-metadata)                        | Name, symbol, decimals, supply                      |
| **Swaps & Markets** | [Swaps by Wallet](/data-feeds/recipes/markets/swaps-by-wallet) ⭐                  | Every DEX trade made by a wallet                    |
|                     | [Swaps by Token](/data-feeds/recipes/markets/swaps-by-token) ⭐                    | Every DEX trade touching a token                    |
|                     | [Swaps by Pair](/data-feeds/recipes/markets/swaps-by-pair)                        | Every DEX trade on a pool/pair                      |
|                     | [Pair OHLCV](/data-feeds/recipes/markets/pair-ohlcv)                              | Candles per pool                                    |
|                     | [Pair Reserves](/data-feeds/recipes/markets/pair-reserves)                        | Current reserves per pool                           |
| **NFT**             | [NFT Trades](/data-feeds/recipes/nft/nft-trades)                                  | Marketplace trades per collection / token / wallet  |
|                     | [NFT Transfers](/data-feeds/recipes/nft/nft-transfers)                            | Every NFT movement                                  |
|                     | [NFT Owners by Contract](/data-feeds/recipes/nft/nft-owners-by-contract)          | Current owners of a collection                      |
|                     | [NFT Collection Metadata](/data-feeds/recipes/nft/nft-collection-metadata)        | Collection-level metadata                           |
| **Logs & Events**   | [Contract Logs](/data-feeds/recipes/logs/contract-logs)                           | Every raw event log emitted by a contract           |
|                     | [Logs by Event Signature](/data-feeds/recipes/logs/logs-by-topic0)                | One event signature (`topic0`) across all contracts |

<Note>
  These are blueprints, not turnkey deployments — lift the projection, schema, and queries you need. See the use cases for ready-made recipe bundles: [Accounting & Tax](/data-feeds/use-cases/accounting), [Portfolio Tracking](/data-feeds/use-cases/portfolio-tracking), [Token Analytics](/data-feeds/use-cases/token-analytics), [Trading & Charting](/data-feeds/use-cases/trading-charting), [NFT Marketplace](/data-feeds/use-cases/nft-marketplace), [Compliance & AML](/data-feeds/use-cases/compliance-aml), and [Onchain Event Indexing](/data-feeds/use-cases/event-indexing).
</Note>

### Get started

Data Feeds is currently in early access.

<Card title="Request Early Access" icon="rocket" href="/data-feeds/early-access">
  Work directly with the Moralis team to run recipes against your own infrastructure.
</Card>
