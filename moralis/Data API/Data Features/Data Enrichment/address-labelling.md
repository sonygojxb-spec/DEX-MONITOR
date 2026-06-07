> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Address & Entity Labeling

> Moralis enriches blockchain data with human-readable labels and entities, helping you understand who is behind on-chain activity.

Moralis enriches blockchain data with **human-readable labels and entities**, helping you understand *who* is behind on-chain activity.

This includes both:

* **Address labels** (e.g. “Coinbase Hot Wallet”)
* **Entities** (e.g. Coinbase, Uniswap, BlackRock)

Together, they provide identity, context, and discoverability across wallets, transactions, and protocols.

***

## What Are Entities?

**Entities** represent real-world organizations, projects, protocols, or individuals that control one or more blockchain addresses.

Examples include:

* Companies and institutions (e.g. exchanges, funds, TradFi firms)
* DeFi protocols and DAOs
* NFT marketplaces and collections
* Public individuals

Entities build on top of address labels by grouping **multiple related addresses** under a single, identifiable actor.

***

## Why Entities Matter

Historically, blockchain data exposed only raw addresses or simple labels.\
This made it difficult to answer higher-level questions like:

* Who is interacting with this wallet?
* Which addresses belong to the same organization?
* How does an entity operate across chains?

With Entities, Moralis provides:

* **In-depth context**\
  Entities include metadata such as name, logo, description, and website.
* **Cross-address visibility**\
  Multiple addresses can be linked to a single entity, giving a more complete picture of activity.
* **Better discovery and analysis**\
  You can search for entities and analyze their on-chain behavior, rather than dealing with individual addresses in isolation.

***

## Entity-Enriched Responses

When supported, Moralis APIs enrich address fields with both **labels** and **entity information**.

Example:

```json theme={null}
{
  "hash": "0x70c30285a9a4cc1c147cc94e5d0cefebe693fffd5fd5cbf727e2f86b6829d71b",
  "nonce": "6810858",
  "transaction_index": "72",
  "from_address": "Oxa9d1e08c7793af67e9d92fe308d5697fb81d3e43",
  "from_address_label": "Coinbase: Hot Wallet",
  "from_address_entity": "Coinbase",
  "from_address_entity_logo": "https://entities-logos.s3.us-east-1.amazonaws.com/coinbase.png",
  "to_address": "Oxa9d1e08c7793af67e9d92fe308d5697fb81d3e43",
  "to_address_label": "Blackrock Wallet",
  "to_address_entity": "Blackrock, Inc",
  "to_address_entity_logo": "https://entities-logos.s3.us-east-1.amazonaws.com/blackrock.png",
  "value": "0",
  "gas": "207128",
  "gas_price": "32393720336",
  "input": "0xa9059cbb000000000000000000000000c476723407b737c173bdfd87c7abc80f6856e6320000000000000000000000000000000000000000000000008533e3870aec3000",
  "receipt_cumulative_gas_used": "8535588",
  "receipt_gas_used": "52089",
  "receipt_contract_address": null,
  "receipt_root": null,
  "receipt_status": "1",
  "block_timestamp": "2023-06-26T16:48:23.000Z",
  "block_number": "17564884",
  "block_hash": "0x4e61fbb792a84c419a22ffcc590cbcb2f5a1b88d8e864d608e3544a3594c0e69",
  "transfer_index": [17564884, 72]
}
```

This allows you to display transactions as **entity-to-entity interactions**, rather than raw address transfers.

***

## Where Entity & Address Labeling Is Available

Entity and address labeling is supported on:

* Any endpoint that includes `from_address` and `to_address`
* Dedicated **Entity API** endpoints for discovery and lookup

This means labeling is automatically available across:

* Transactions
* Wallet activity
* Transfers
* DeFi interactions

***

## Entity Coverage

Moralis currently supports:

* **500+ entities**
* **10,000+ labeled addresses**

Coverage is strongest across:

* Ethereum
* Polygon
* BNB Chain
* Optimism
* Base
* Arbitrum

### Supported Entity Categories

Entities span a wide range of categories, including:

* Centralized Exchange
* Decentralized Exchange
* NFT Marketplace
* DeFi
* TradFi
* Fund
* DAO
* Bridge
* Stablecoin
* Lending / Borrowing
* Liquid Staking / Restaking
* NFT Collection
* Gaming
* Wallet
* MEV
* Real World Assets
* Privacy
* Cross-chain Infrastructure
* Individual
* Misc

Coverage and categorisation are continuously expanding.

***

## Common Use Cases

Address & Entity Labeling enables you to:

* Build readable transaction feeds
* Detect interactions with known exchanges, protocols, or institutions
* Power compliance, monitoring, and analytics workflows
* Aggregate activity at the entity level instead of per address

***

## Notes & Limitations

* Labeling and entity assignment is **best-effort**
* Not all addresses belong to known entities
* New entities and labels are added continuously as coverage expands
