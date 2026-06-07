> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# NFT Sale Prices

> Understand how Moralis computes NFT sale prices from onchain marketplace trades, including last/lowest/highest/average sale, lookback windows, marketplace + chain coverage, and enriched trade metadata.

Moralis NFT Sale Prices summarize **real onchain sale and trade activity** for NFTs and collections, based on buys/sells from supported NFT marketplaces.

This feature is built on top of Moralis **NFT Trades** data and is designed for production use cases like:

* Sale price tracking and alerts
* Wallet and token-level trade analysis
* Portfolio valuation and historical provenance

***

## What “Sale Price” Means

A sale is recorded when an NFT is bought/sold on a supported marketplace. Moralis extracts and normalizes:

* The **payment token** used (native or ERC20)
* The **raw price** paid (base units) and **formatted price**
* The **USD price at time of sale**
* The **current USD value** using today’s token price

Important: these are **marketplace sales**, not arbitrary transfers. Simple NFT transfers (gift/send) are not considered sales.

***

## What You Get Back

Sale price summaries typically include:

### Last sale

The most recent recorded sale within the available trade history, including:

* `transaction_hash`
* `block_timestamp`
* `buyer_address` / `seller_address`
* `token_id`
* `price` (raw base units)
* `price_formatted` (decimal-adjusted)
* `usd_price_at_sale`
* `current_usd_value`
* `payment_token` metadata (name, symbol, decimals, address, logo)

### Lowest sale (within a lookback window)

The lowest recorded sale price within the specified lookback period (see “Lookback window” below).

### Highest sale

The highest recorded sale price (typically within the same scope as the response; depends on endpoint).

### Average sale

An average price across trades included in the response scope:

* `price` / `price_formatted`
* `current_usd_value`

### Total trades

A count of sales/trades included for that scope:

* `total_trades`

Notes on price fields:

* `price` is the raw integer amount in the payment token’s base units.
* `price_formatted` is the human-readable value using `token_decimals`.
* `usd_price_at_sale` is the USD valuation at the time the sale happened.
* `current_usd_value` is recalculated using the current price of the payment token (useful for mark-to-market comparisons).

***

## Lookback Window (`days`)

Some sale price summaries (notably **lowest sale**) support an optional `days` query parameter:

* Default: **7 days**
* Maximum: **365 days**

If you set `days=30`, “lowest sale” will be the lowest sale price found in the last 30 days. If you omit it, the system uses 7 days.

Practical guidance:

* Use smaller windows (7–30) for “recent floor” style features.
* Use larger windows (90–365) for long-term volatility and range analysis.

***

## Marketplace Coverage

Sale prices are derived from trades on supported marketplaces. Current coverage includes:

* OpenSea
* Blur
* LooksRare
* X2Y2
* 0xProtocol

Coverage can vary by chain and marketplace. For the authoritative matrix, use the [Marketplaces](/data-api/data-features/integrations/nft-marketplaces) page.

Related pages:

* [NFT Marketplaces](/data-api/data-features/integrations/nft-marketplaces)

***

## Chain Coverage

NFT Trades (and therefore NFT Sale Prices) are available on:

* Ethereum
* Polygon
* Binance
* Arbitrum
* Avalanche
* Optimism
* Base
* Monad

***

## Enriched Trade Metadata

All NFT Trade endpoints (including those powering sale price summaries) can include enriched metadata such as:

* Marketplace metadata (name + logo)
* Collection metadata (collection name + logo)
* Payment token metadata (name, symbol, logo, decimals, address)
* Current USD value for each trade (mark-to-market)
* Optional NFT metadata via `nft_metadata=true`

Use `nft_metadata=true` when you need token attributes/media in the same response. Leave it off for performance when you only need pricing and trade facts.

Related pages:

* [NFT Metadata](/data-api/data-features/data-enrichment/nft-metadata)
* [NFT Image Previews](/data-api/data-features/data-enrichment/nft-metadata/image-previews-cdn)

***

## Related Endpoints (Trade Feeds)

Sale price summaries are most useful when paired with raw trade feeds:

* [NFT Trades by Collection](/data-api/evm/nft/trades/collection-trades)\
  Fetch the full trade history for a collection (sales feed)
* [NFT Trades by Wallet](/data-api/evm/wallet/nft-trades-by-wallet)\
  Fetch all NFT trades associated with a wallet address
* [NFT Trades by Token ID](/data-api/evm/nft/trades/trades-by-token-id)\
  Fetch the trade history for a specific NFT (collection + token id)
