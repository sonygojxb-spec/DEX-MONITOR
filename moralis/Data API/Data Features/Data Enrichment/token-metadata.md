> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Metadata

> Understand how Moralis combines onchain and offchain token metadata - names, supply, logos, categories, links, safety signals, and cross-chain implementations into a single developer-friendly response.

Moralis token metadata combines **onchain facts** (what the contract reports) with **offchain enrichment** (logos, categories, descriptions, links, verification, and market fields) to give you a clean, consistent token object across chains.

This page explains what data comes from where, how to interpret key fields, and how to use related data features like token scores and spam filtering.

Related pages:

* [Token API Overview](/data-api/evm/token/overview)
* [Token Scores](/data-api/data-features/token-scores)
* [Verified Contracts](/data-api/data-features/safety-and-trust/verified-contracts)
* [Spam Filtering](/data-api/resources/spam-filtering)
* [Token Search](/data-api/data-features/search-and-discovery/token-search)

***

## Onchain vs Offchain metadata

### Onchain metadata (from the token contract)

These values are sourced directly from chain data and are generally deterministic:

* `address`
* `name`
* `symbol`
* `decimals`
* `total_supply`
* `block_number` (block created)
* `created_at` (when Moralis first observed/indexed the contract)

***

### Offchain metadata (curated/enriched)

These values are enriched using trusted external sources and Moralis internal systems:

* `logo`
* `description`
* `categories`
* `links` (website, twitter, telegram, etc.)
* `security_score`
* `possible_spam`
* `verified_contract`
* `circulating_supply` (sourced from CoinGecko where available)
* `market_cap`, `fully_diluted_valuation`
* `address_label` (human-readable label)

Offchain enrichment improves UX and trust signals, and is especially useful for:

* Wallet UIs
* Token discovery experiences
* Safety filtering
* Market analytics

See:

* [Token Scores](/data-api/data-features/token-scores)
* [Spam Filtering](/data-api/resources/spam-filtering)
* [Verified Contracts](/data-api/data-features/safety-and-trust/verified-contracts)

***

## Example response

```
[
  {
    "address": "0x6982508145454ce325ddbe47a25d4ec3d2311933",
    "address_label": "Pepe (PEPE)",
    "name": "Pepe",
    "symbol": "PEPE",
    "decimals": "18",
    "logo": "https://logo.moralis.io/0x1_0x6982508145454ce325ddbe47a25d4ec3d2311933_5c5ee6fce6d19f71c224cba025989229.jpeg",
    "total_supply": "420689899653542539491331875576506",
    "total_supply_formatted": "420689899653542.539491331875576506",
    "fully_diluted_valuation": "2095999648.29",
    "block_number": "17046105",
    "validated": 1,
    "created_at": "2023-04-14T14:51:35.000Z",
    "possible_spam": false,
    "verified_contract": true,
    "categories": ["Meme"],
    "links": {
      "reddit": "https://www.reddit.com",
      "telegram": "https://t.me/pepecoineth",
      "twitter": "https://twitter.com/pepecoineth",
      "website": "https://www.pepe.vip/"
    },
    "security_score": 96,
    "description": "Pepe ($PEPE) is a meme coin aiming to bring back the glory days of memecoins...",
    "circulating_supply": "420690000000000",
    "market_cap": "2096000148.24",
    "implementations": [
      {
        "chainId": "0xa86a",
        "chain": "avalanche",
        "chainName": "Avalanche",
        "address": "0xa659d083b677d6bffe1cb704e1473b896727be6d"
      },
      {
        "chainId": "0x38",
        "chain": "bsc",
        "chainName": "BNB Smart Chain",
        "address": "0x25d887ce7a35172c62febfd67a1856f20faebb00"
      },
      {
        "chainId": "0xa4b1",
        "chain": "arbitrum",
        "chainName": "Arbitrum One",
        "address": "0x25d887ce7a35172c62febfd67a1856f20faebb00"
      }
    ]
  }
]
```

***

## Key fields explained

### Identity

* `address_label`: Human-readable label (useful for UI)
* `name`, `symbol`, `decimals`: Standard ERC-20 fields
* `logo`: Offchain logo URL (may be missing for new/unknown tokens)

Related:

* [Token Search](/data-api/data-features/search-and-discovery/token-search)

***

### Supply & valuation

* `total_supply`/  `total_supply_formatted`: Onchain total supply
* `circulating_supply`: Offchain circulating supply (CoinGecko where available)
* `market_cap`: Typically `price × circulating_supply`
* `fully_diluted_valuation`**(FDV)** : Typically `price × total_supply`

#### Circulating supply fallback

If `circulating_supply` is not available, Moralis falls back to `total_supply`.\
In that case, **market cap effectively becomes FDV**.

This is important when building:

* token rankings
* market cap charts
* “top tokens” discovery feeds

Related:

* [Token Prices](/data-api/data-features/data-enrichment/token-prices)

***

### Safety & trust signals

* `possible_spam`: Flag for suspicious/spam tokens
* `verified_contract`: Verified by CoinGecko (not Etherscan)
* `security_score`: Moralis safety score (0-100)

Related:

* [Spam Filtering](/data-api/resources/spam-filtering)
* [Verified Contracts](/data-api/data-features/safety-and-trust/verified-contracts)
* [Token Scores](/data-api/data-features/token-scores)

***

### Classification & links

* `categories`: Token categories (e.g. Meme, DeFi)
* `links`: Offchain links (twitter, website, telegram, etc.)
* `description`: Offchain token description

***

### Cross-chain implementations

* `implementations` lists known linked deployments of the “same” token across multiple chains (e.g. bridged or multi-chain versions).

This enables:

* consistent UI labels/logos across chains
* unified token discovery experiences
* cross-chain token analytics

***

## Summary

Moralis Token Metadata provides a unified token object that combines:

* **Onchain** ERC-20 data (name, symbol, decimals, supply)
* **Offchain** enrichment (logos, links, categories, descriptions)
* **Trust signals** (spam flags, verification, security score)
* **Market fields** (circulating supply, market cap, FDV)
* **Cross-chain implementations** for linked tokens
