> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# NFT Rarity

> Understand how Moralis calculates NFT rarity across collections using trait frequency analysis, rarity scores, rankings, and refreshable on-demand processing for ERC721 and ERC1155 NFTs. 

## Overview

NFT rarity measures how **unique an NFT is within its collection**, based on how common or uncommon its attributes are compared to other NFTs in the same collection.

In most NFT collections, traits such as background, color, accessories, or attributes appear at different frequencies. NFTs with **less common trait combinations** are considered rarer and are often perceived as more valuable by collectors, marketplaces, and analytics platforms.

Moralis provides **deterministic, collection-wide rarity scores and rankings**, calculated directly from indexed NFT metadata.

Related pages:

* [NFT Metadata](/data-api/data-features/data-enrichment/nft-metadata)
* [NFT Image Previews (CDN)](/data-api/data-features/data-enrichment/nft-metadata/image-previews-cdn)
* [NFT API Overview](/data-api/evm/nft/overview)

***

## How rarity is calculated

Moralis computes rarity **per collection**, not globally.

The rarity calculation process consists of two layers:

### 1. Trait-level analysis

For every trait across the collection, we compute:

* `count`\
  Number of NFTs that contain this trait
* `percentage`\
  Percentage of the collection that contains this trait
* `rarity_label`\
  Human-readable label based on trait frequency\
  *(e.g. “Top 1% trait”, “Top 10% trait”)*

This makes rarity explainable, not just numeric.

***

### 2. NFT-level rarity scoring

For each NFT, we compute:

* `rarity_score`\
  Numerical score derived from the combined rarity of all its traits
* `rarity_rank`\
  Rank of the NFT within the collection (1 = rarest)
* `rarity_percentage`\
  Relative rarity compared to the entire collection
* `rarity_label`\
  Human-readable summary (e.g. “Top 1% rarity”)

These fields are returned directly in supported NFT endpoints.

***

## Supported collections

Rarity calculations are supported for:

* **ERC-721 collections**
* **ERC-1155 collections**

With the following constraints:

* Maximum collection size: **50,000 NFTs**
* All NFTs must be discoverable and indexed
* Metadata and traits must be available for the full collection

If these conditions are not met, rarity will not be calculated.

***

## Supported chains

NFT rarity is supported on **all EVM chains** where Moralis NFT metadata is available, including:

* Ethereum
* Polygon
* Base
* Arbitrum
* Optimism
* BNB Chain
* Other supported EVM chains

Rarity logic is chain-agnostic and applied consistently.

***

## Trait syncing & rarity processing

Rarity is computed **on demand**, per collection.

### Initial sync flow

1. A collection is queried using `getNFTTraitsByCollection`
2. The collection is added to a processing queue
3. Traits are synced for all NFTs
4. Rarity scores and rankings are calculated

While processing is in progress, trait endpoints return:

```
202 – Contract is being resynced at the moment. Please try again later.
```

***

### Processing times

Typical processing times:

* Small collections: **5–15 seconds**
* Medium collections: **15–60 seconds**
* Large collections (20,000+ NFTs): may take longer

If processing exceeds **5 minutes**, contact support.

Once queued, a collection **cannot be reprocessed again for 30 minutes**.

***

## Refreshing rarity scores

Rarity scores **can be refreshed** after:

* NFT reveals
* New mints
* Metadata or trait updates

Refreshing rarity is triggered by re-syncing traits, which automatically recalculates all rarity data.

See:

* [Metadata Resyncing](/data-api/evm/nft/utilities/resync-nft-metadata)
* [Rarity Resyncing](/data-api/evm/nft/utilities/resync-nft-traits)

***

## Why rarity matters

NFT rarity enables:

* Collection ranking & discovery
* Trait-based filtering
* Floor price and valuation analysis
* Wallet and portfolio insights
* Marketplace and analytics UIs

Without indexing internal trait distributions, rarity cannot be computed accurately - which is why many platforms approximate or omit this entirely.

***

## Best practices

* Don’t assume rarity exists until processing completes
* Handle `202` responses gracefully
* Cache rarity results when possible
* Re-sync after major collection events (e.g. reveals)

***

## Summary

Moralis NFT Rarity provides:

* Deterministic rarity scores
* Trait-level transparency
* Collection-wide rankings
* Multichain support (EVM)
* Refreshable, on-demand computation

This allows you to build **analytics, discovery, and marketplace experiences** without maintaining your own rarity infrastructure.
