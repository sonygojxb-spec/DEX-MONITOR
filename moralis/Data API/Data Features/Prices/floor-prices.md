> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# NFT Floor Prices

> Learn how Moralis provides NFT floor prices, including what a floor price represents, supported chains, data sources, refresh cadence, inactivity rules, and historical availability.

NFT Floor Prices provide a **collection-level snapshot** of the lowest-priced NFT currently listed for sale. This gives a fast, comparable baseline for what it would cost to acquire the cheapest item in a collection *right now*.

Floor prices are best suited for:

* Market overviews and dashboards
* Collection comparisons
* Entry-price signals and alerts

They are intentionally different from [NFT Sale Prices](/data-api/data-features/prices/sale-prices), which are based on completed onchain trades.

***

## What a Floor Price Represents

The floor price is the **lowest active listing price** for an NFT in a given collection.

Important characteristics:

* Based on **active listings**, not completed sales
* Represents seller intent, not executed market price
* Calculated at the **collection level**, not per token

Because listings can be added or removed at any time, floor prices are inherently volatile and should be treated as **indicative**, not authoritative trade prices.

***

## Supported Chains

NFT floor prices are currently supported on:

* Ethereum
* Base
* Monad
* Arbitrum
* Ronin
* Flow
* Sei

Coverage may expand over time. For trade-based pricing with broader chain support, see NFT Sale Prices.

***

## Data Sources

Floor prices are sourced from a combination of marketplace and aggregation APIs:

* **OpenSea API** (primary source)
* **Magic Eden API**\
  Magic Eden aggregates floor prices across multiple marketplaces, including OpenSea, Blur, X2Y2, and Magic Eden itself
* **CoinGecko** (fallback / enrichment)

These sources provide listing-level market data that cannot be derived purely from onchain events.

Important distinction:

* **NFT Sale Prices** → derived from onchain marketplace trades
* **NFT Floor Prices** → derived from offchain marketplace listing data

Related pages:

* [NFT Marketplaces](/data-api/data-features/integrations/nft-marketplaces)
* [NFT Sale Prices](/data-api/data-features/prices/sale-prices)

***

## Refresh Frequency

Floor prices are refreshed **every 60 minutes**.

This cadence balances:

* Marketplace rate limits
* Data freshness
* Platform-wide performance and stability

Floor prices are not real-time and should not be treated as tick-level market data.

***

## First-Time Requests (Warm-Up Behavior)

If a collection’s floor price has **never been requested before**, the first request will return:

* HTTP status: **202**
* Message:

  ```javascript theme={null}
  {
      "message": "This contract is currently being processed. Floor price data will be available shortly. Please try again later."
  }
  ```

During this warm-up period:

* The collection is registered for tracking
* Floor price data begins syncing

Once processing completes, subsequent requests return floor price data normally.

***

## Inactivity Handling

If a collection has **no trading activity for 7 days**:

* Floor price updates are paused
* No new floor price snapshots are recorded

Once trading activity resumes:

* Floor price updates automatically resume
* No manual action is required

This prevents stale or misleading prices from being continuously refreshed for inactive markets.

***

## Historical Floor Price Data

### Backfilling

Historical floor prices are **not backfilled**.

Reason:

* Marketplace APIs do not currently expose historical listing data
* Historical tracking can only begin after the first request

Moralis starts saving floor prices in **60-minute intervals** from the moment a collection is first requested.

***

### Supported Historical Intervals

When requesting time-series floor price data, the interval determines the data resolution:

* **1 day**\
  Data points every 60 minutes
* **7 days**\
  Hourly data points
* **30 days**\
  Hourly data points
* **Greater than 30 days**\
  Daily data points

This adaptive resolution keeps queries efficient while preserving meaningful trends.

***

## Inactive Collections and Historical Access

If a collection becomes inactive:

* Floor prices stop updating
* **Previously saved historical data remains accessible**

This allows you to:

* Analyze past market conditions
* Build long-term charts
* Compare historical floors even for dormant collections

***

## When to Use Floor Prices (and When Not To)

Use NFT Floor Prices when you need:

* A quick market baseline
* Collection-to-collection comparisons
* Entry price signals

Do not rely on floor prices for:

* Valuation of a specific NFT
* Profitability or realized value calculations
* Historical execution accuracy

For executed market prices and provenance, use [NFT Sale Prices](/data-api/data-features/prices/sale-prices).
