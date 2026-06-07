> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# NFT Image Previews (CDN)

> Generate and serve optimized NFT image previews via Moralis CDN for faster loading and better user experiences.

## Overview

Moralis provides optimized **NFT image previews** for both **EVM and Solana NFTs**, generated on demand and delivered via a global CDN.

Instead of loading large, slow, and inconsistent original NFT images directly from IPFS or third-party hosts, you can rely on Moralis to serve **low, medium, and high-resolution thumbnails** that are fast, cacheable, and reliable - ideal for wallets, marketplaces, dashboards, and feeds.

This removes the need to build and operate your own NFT media pipeline while significantly improving frontend performance and UX.

Related pages:

* [NFT Metadata](/data-api/data-features/data-enrichment/nft-metadata)
* [NFT API Overview](/data-api/evm/nft/overview)

***

## What are NFT image previews?

NFT image previews are **pre-generated thumbnails** of the original NFT media, optimized for common UI use cases such as:

* Wallet views
* Galleries
* Marketplaces
* Search results
* Collection pages

Moralis generates and caches these previews once, then serves them via CDN for subsequent requests.

***

## Supported image formats

Moralis currently supports common static image formats, including:

* JPG / JPEG
* PNG
* GIF
* TIFF
* WEBP
* SVG

### Not yet supported

* Video (planned)

***

## How to enable image previews

Image previews are returned when the `media_items` query parameter is set to `true`.

Once enabled, preview URLs are included directly in the API response.

***

## Does this cost extra?

No. Enabling `media_items=true` is **free** and does **not consume additional compute units (CUs)**.

***

## Preview generation lifecycle

Image previews are generated **on demand**.

### What happens on first request?

* If previews don’t yet exist:
  * Generation starts automatically
  * The original media URL is still returned
* Once generated:
  * Previews are cached
  * Subsequent requests return previews instantly

***

## Preview generation statuses

Each NFT media item includes a generation status:

| Status                    | Description                          |
| :------------------------ | :----------------------------------- |
| `success`                 | Preview generated and returned       |
| `processing`              | Preview is being generated           |
| `unsupported_media`       | Media type not supported             |
| `invalid_url`             | Metadata image URL is invalid        |
| `retry`                   | Generation failed and will retry     |
| `host_unavailable`        | Media host is unavailable            |
| `temporarily_unavailable` | Temporary failure (e.g. rate limits) |

Regardless of status, the API **always returns the original media URL** as a fallback.

***

## Retry behavior

If preview generation fails, Moralis automatically retries with **exponential backoff**.

* Up to **8 retry attempts**
* Increasing delay between attempts

### Retry schedule

| Attempt | Delay      |
| :------ | :--------- |
| 1       | 1 minute   |
| 2       | 5 minutes  |
| 3       | 10 minutes |
| 4       | 15 minutes |
| 5       | 30 minutes |
| 6       | 40 minutes |
| 7       | 50 minutes |
| 8       | 60 minutes |

This ensures resilience against:

* Temporary host issues
* Rate-limited IPFS gateways
* Intermittent CDN failures

***

## Why this matters

Without image previews:

* Large images slow down UIs
* IPFS gateways can be unreliable
* Frontends must handle resizing and caching manually

With Moralis image previews:

* Faster load times
* Predictable image sizes
* CDN-backed delivery
* No custom infrastructure required

***

## Common use cases

* **Wallet dashboards**\
  Fast-loading NFT grids
* **Marketplaces**\
  Consistent thumbnails for listings
* **Search & discovery**\
  Lightweight previews for large result sets
* **Mobile apps**\
  Reduced bandwidth and faster rendering

***

## Supported chains

NFT image previews are supported across both major NFT ecosystems:

* **EVM chains**\
  Ethereum, Polygon, Base, Arbitrum, Optimism, BNB Chain, and more
* **Solana**\
  Including SPL NFTs and Metaplex-based collections

Image previews behave consistently across supported chains, with the same:

* Generation logic
* Retry behavior
* CDN delivery
* API response structure

***

## Summary

Moralis NFT Image Previews provide:

* On-demand thumbnail generation
* CDN-backed delivery
* Multi-resolution previews
* Zero additional CU cost
* Automatic retries and fallbacks

This allows you to ship fast, reliable NFT experiences without worrying about media hosting or processing.
