> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Filtering

> Filtered Tokens enables powerful, multi-chain token discovery using advanced metrics, filters, and time-based analysis.

Instead of relying on simple search or static lists, this feature allows you to **query the token universe dynamically**, using real market, holder, liquidity, and security signals.

It’s designed for:

* Token discovery platforms
* Market analytics tools
* Trading and research dashboards

***

## What Filtered Tokens Does

Filtered Tokens lets you:

* Query tokens across multiple chains in a single request
* Combine multiple filters using comparison operators
* Analyze short-term and long-term trends
* Sort tokens by any supported metric
* Include or exclude token categories
* Apply safety and quality thresholds

To start using these capabilities, see the [Filtered Tokens endpoint](/data-api/universal/token/filtered-tokens).

This makes it possible to express questions like:

> “Which high-liquidity tokens gained buyers in the last hour?”\
> “Which new tokens launched this week already have strong volume?”\
> “Which tokens meet my safety and maturity criteria?”

***

## Supported Blockchains

Filtered Tokens supports major networks, including:

* Ethereum
* Solana
* Base
* Arbitrum
* Polygon
* BNB Chain
* Avalanche
* Optimism
* Ronin
* Linea
* Fantom
* PulseChain

Coverage continues to expand.

***

## Available Metrics

### Market Metrics

* `marketCap` – Current market capitalization
* `fullyDilutedValuation` – FDV
* `totalLiquidityUsd` – Total liquidity (USD)

***

### Trading Metrics *(time-based)*

* `volumeUsd` – Trading volume
* `usdPricePercentChange` – Price change (%)
* `liquidityChange` – Liquidity change
* `liquidityChangeUSD` – Liquidity change (USD)

***

### Holder & Flow Metrics *(time-based)*

* `totalHolders` – Current holder count
* `holders` – Holder growth
* `buyers` / `sellers` – Active traders
* `netBuyers` – Net buyer flow
* `experiencedBuyers` / `experiencedSellers` – Experienced trader activity

***

### Acquisition Metrics

* `holdersBySwap` – % acquired via DEX
* `holdersByTransfer` – % acquired via transfers
* `holdersByAirdrop` – % acquired via airdrops

***

### Security & Age

* `securityScore` – Token security rating (0–100)
* `tokenAge` – Days since token creation

***

## Time Frames

Time-based metrics support the following windows:

* `tenMinutes`
* `thirtyMinutes`
* `oneHour`
* `fourHours`
* `twelveHours`
* `oneDay`
* `oneWeek`
* `oneMonth`

This allows both **real-time momentum tracking** and **longer-term trend analysis**.

***

## Common Use Cases

### Discover Trending Tokens

```json theme={null}
{
  "chains": ["eth", "base"],
  "filters": [
    { "metric": "volumeUsd", "timeFrame": "oneDay", "gt": 1000000 },
    { "metric": "buyers", "timeFrame": "oneHour", "gt": 50 },
    { "metric": "usdPricePercentChange", "timeFrame": "oneDay", "gt": 10 }
  ],
  "sortBy": {
    "metric": "volumeUsd",
    "timeFrame": "oneDay",
    "type": "DESC"
  }
}
```

***

### Identify Newly Launched Tokens

```json theme={null}
{
  "filters": [
    { "metric": "tokenAge", "gt": 1767325000 }, // Unix Timestamp
    { "metric": "marketCap", "gt": 500000 },
    { "metric": "totalHolders", "gt": 100 }
  ],
  "sortBy": {
    "metric": "volumeUsd",
    "timeFrame": "oneDay",
    "type": "DESC"
  }
}
```

***

## Category Filtering

You can include or exclude token categories to fine-tune discovery:

```json theme={null}
{
  "categories": {
    "include": ["meme-token", "gaming"],
    "exclude": ["stablecoins", "wrapped-tokens"]
  }
}
```

Use [Token Categories](/data-api/evm/token/discovery/token-categories) to identify all supported categories.

***

## How Filters Work

* Filters are combined using **AND logic**
* All filter conditions must be met
* Snapshot metrics must **not** use a `timeFrame`
* Time-based metrics **require** a `timeFrame`

Example:

```json theme={null}
{
  "filters": [
    { "metric": "marketCap", "gt": 1000000, "lt": 100000000 },
    { "metric": "volumeUsd", "timeFrame": "oneDay", "gt": 500000 },
    { "metric": "holders", "timeFrame": "oneWeek", "gt": 1000 },
    { "metric": "securityScore", "gt": 80 }
  ]
}
```

***

## Best Practices

Recommended baseline filters for most use cases:

* `marketCap` > \$100K
* `totalLiquidityUsd` > \$500
* `volumeUsd` (1d) > \$1,000
* `securityScore` > 70

Additional tips:

* Narrow chains to improve result relevance
* Choose time frames aligned with your UX
* Sort by the metric that best reflects intent

***

## Limits & Constraints

* Maximum of **100 tokens per request**
* No pagination support
* Highly restrictive filters may return fewer results
* Some tokens may lack specific metrics

***

## Data Freshness

* Most metrics update every **\~10 seconds**
* Acquisition metrics may lag by up to **5 minutes** for highly active tokens
* Price and volume data are near real-time
