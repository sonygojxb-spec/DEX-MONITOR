> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# How Data Feeds Works

> Understand the Data Feeds workflow: start from a recipe or a custom schema, configure your pipeline, and have indexed blockchain data delivered into your own database.

### Overview

Moralis Data Feeds handles the complexity of blockchain data indexing so you can focus on building. It reads Moralis-indexed, normalized per-block onchain data and continuously projects it into your own database. The workflow is straightforward:

### 1. Define

Start from a **recipe** or define a **custom schema**:

* **Recipes** – ready-made blueprints that reconstruct popular Moralis endpoints (wallet history, balances, prices, swaps, holders, raw logs). The fastest on-ramp. [Browse recipes →](/data-feeds/recipes/overview)
* **Custom** – specify exactly which chains, contracts, events, and data types to index, with your own schema
* **Chains** – EVM, Bitcoin, Solana, Stellar, Hyperliquid, or a custom chain via your own RPC
* **Data types** – raw data, decoded data, or both

### 2. Configure

Set up your schema and transformation rules:

* Define your data models and field mappings (or adapt a recipe's)
* Configure transformations and enrichments (e.g. inline USD valuation)
* Set up filters to capture only the data you need
* Choose your mode: **historical** backfill, **realtime** tail, or **hybrid** (both)

### 3. Deploy

Moralis deploys and manages the indexing infrastructure:

* No infrastructure to provision or maintain
* Automatic scaling based on data volume
* Built-in redundancy and fault tolerance
* Continuous monitoring and alerting

### 4. Deliver

Data lands directly in your own database:

* Real-time delivery as events occur on-chain
* Historical backfills delivered in parallel
* Reorg-safe: corrections converge your tables on canonical state automatically
* Data arrives in your schema, ready to query

### Delivery destinations

Data Feeds syncs into the database you run, indexed for your access pattern.

| Destination    | Notes                                                                                                      |
| -------------- | ---------------------------------------------------------------------------------------------------------- |
| **ClickHouse** | First-class — the only destination with live, reorg-safe ingestion. Best for production and large windows. |
| **Postgres**   | Historical backfill, analytics, and smaller windows.                                                       |
| **MySQL**      | Historical backfill and existing MySQL stacks.                                                             |

### Architecture benefits

| Benefit                 | Description                                                                    |
| ----------------------- | ------------------------------------------------------------------------------ |
| **Fully Managed**       | Moralis handles all infrastructure, scaling, and maintenance                   |
| **Low Latency**         | Optimised pipelines for minimal delay between on-chain events and delivery     |
| **Guaranteed Delivery** | No data loss, with built-in retries and exactly-once-effective semantics       |
| **Reorg-Safe**          | Chain reorganizations are corrected automatically so your data stays canonical |
| **Cost Efficient**      | Pay for the data you need, not unused infrastructure                           |

### Get Started

Data Feeds is onboarding enterprise teams now. Work directly with Moralis engineering on your specific requirements.

<Card title="Request an early-access account" icon="rocket" href="/data-feeds/early-access">
  Partner with our team to stand up your pipelines — production-grade from day one.
</Card>
