> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# NFT Metadata

> Fetch and normalize NFT metadata into a clean, predictable format across ERC721 and ERC1155 collections.

## Overview

NFT metadata is notoriously inconsistent.

Different collections use different schemas, naming conventions, attribute formats, and storage locations - making it difficult to work with at scale.

Moralis solves this by **normalizing NFT metadata into a clean, predictable structure**, while still allowing access to the original source data when needed.

Related pages:

* [NFT API Overview](/data-api/evm/nft/overview)
* [NFT Traits & Rarity](/data-api/data-features/data-enrichment/nft-rarity)
* [NFT Image Previews](/data-api/data-features/data-enrichment/nft-metadata/image-previews-cdn)
* [Supported NFT Marketplaces](/data-api/data-features/integrations/nft-marketplaces)

***

## What is NFT metadata normalization?

When enabled, Moralis transforms raw NFT metadata into a **standardized JSON structure** that works consistently across:

* ERC721
* ERC1155
* OpenSea-style metadata
* Collection-specific formats (e.g. CryptoPunks, ENS)

This removes the need for custom parsing logic per collection.

### Why this matters

Without normalization:

* Attributes are inconsistently named
* Values change type across collections
* Metadata is often returned as a raw JSON string
* Frontends and analytics break easily

With normalization:

* Predictable fields
* Consistent attribute structure
* Easier UI rendering
* Easier indexing and analytics

***

## How to enable normalized metadata

Several NFT endpoints support metadata normalization via the `normalizeMetadata` query parameter.

When enabled:

* Raw metadata is preserved
* A new `normalized_metadata` object is added to the response

***

## Normalized metadata structure

The normalized metadata object provides a **stable schema** across collections.

### Core fields

```javascript theme={null}
{
  "name": "Moralis Mug",
  "description": "Moralis Coffee mug 3D asset",
  "image": "https://...",
  "external_link": "https://...",
  "animation_url": "https://...",
  "attributes": []
}
```

***

### Normalized attributes

Each attribute follows a consistent structure:

```javascript theme={null}
{
  "trait_type": "Eye Color",
  "value": "Hazel",
  "display_type": "string",
  "max_value": 100,
  "trait_count": 7,
  "order": 1
}
```

This makes it easy to:

* Render traits
* Sort attributes
* Calculate rarity
* Compare NFTs across collections

See also:

* [NFT Traits & Rarity](/data-api/data-features/data-enrichment/nft-rarity)

***

## Raw vs normalized metadata

Moralis always preserves the original metadata source.

### Normalized metadata

* Returned as structured JSON
* Easy to consume
* Consistent across collections

### Raw metadata

* Returned as a string
* Mirrors the original token URI response
* Useful for debugging or edge cases

Example (raw metadata string):

```text theme={null}
"{ \"name\": \"Dave Starbelly\", \"attributes\": [...] }"
```

***

## Collection-specific normalization

Moralis includes **custom normalization logic** for well-known collections and standards, including:

* CryptoPunks
* CryptoKitties
* ENS
* OpenSea-style metadata

If a collection does not match a known format:

* A default transformation is applied
* Based on ERC721 or ERC1155 conventions
* Most fields are still normalized successfully

This ensures broad compatibility without manual handling.

***

## Automatic metadata refresh

NFT metadata can change over time - especially when hosted on IPFS.

To keep data fresh, Moralis automatically refreshes metadata when NFTs are requested.

### How it works

* When an NFT is requested, it is queued for refresh
* If the metadata URI points to IPFS:
  * The token is eligible for periodic refresh
* Refreshing happens transparently in the background

### Cool-off period

Metadata refresh is resource-intensive, so a cool-off period applies:

* **IPFS-based metadata:**\
  Refresh allowed once every **10 minutes per token**

This balances freshness with performance.

***

## Collection offchain metadata

In addition to token-level metadata, Moralis also enriches NFT collections with **offchain metadata** sourced from trusted marketplaces such as **OpenSea**.

This includes collection-level information that is often **not available on-chain**, such as:

* Collection name
* Collection description
* Collection image and banner image
* External links (website, Twitter, Discord, etc.)
* Marketplace identifiers

This enrichment allows you to:

* Display richer collection pages
* Avoid making separate marketplace API calls
* Work with consistent collection metadata across chains

Collection offchain metadata is returned alongside on-chain data on supported NFT endpoints.

***

## Common use cases

* **NFT galleries**\
  Render attributes consistently across collections
* **Marketplaces**\
  Normalize metadata for search, filtering, and ranking
* **Analytics & rarity tools**\
  Work with structured traits at scale
* **Wallet & portfolio views**\
  Display NFTs reliably without custom parsing logic

***

## Supported chains

NFT metadata normalization is available on all supported **mainnet** networks only. Testnets are not supported.

***

## Summary

Moralis NFT Metadata normalization provides:

* Clean, predictable metadata
* Broad collection support
* Automatic refresh handling
* Reduced frontend and backend complexity

If you’re working with NFTs at scale, normalization isn’t optional — it’s foundational.
