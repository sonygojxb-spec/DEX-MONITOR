> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Search

> Token Search lets you discover tokens across multiple blockchains using names, symbols, token address or DEX pair addresses, with built-in ranking and verification signals to surface high-quality results.

Token Search indexes tokens across supported chains and returns ranked results based on relevance, activity, and verification signals.

It’s designed for building fast, reliable token discovery experiences in wallets, dashboards, and trading applications.

You can search by:

* Token name (e.g. `Pepe`)
* Token symbol (e.g. `PEPE`)
* Token address
* DEX pair address
* Partial matches (e.g. `PEP` → `PEPE`)

Search is:

* Case-insensitive
* Resilient to partial input
* Optimized to prioritize legitimate tokens

***

## Search Controls & Ranking

Token Search exposes several controls that affect how results are ranked and filtered.

### Verification Controls

* `isVerifiedContract`\
  When `true`, only [verified tokens](/data-api/data-features/safety-and-trust/verified-contracts) are returned.\
  Default: `false`
* `boostVerifiedContracts`\
  When `true`, [verified tokens](/data-api/data-features/safety-and-trust/verified-contracts) are ranked higher.\
  Default: `true`

***

### Sorting Options

You can sort results using:

* `volume1hDesc` *(default)*
* `volume24hDesc`
* `liquidityDesc`
* `marketCapDesc`

This allows you to tune search results for:

* Trading UIs
* Analytics dashboards
* Discovery vs relevance

***

## Multi-Chain Search

Token Search supports querying across multiple chains in a single request.

Blockchains currently supported:

* Ethereum
* Polygon
* BNB Chain
* Arbitrum
* Optimism
* Base
* Avalanche
* Fantom
* Linea
* Ronin
* PulseChain
* Solana

Support is continuously expanding.

***

## Verified Token Prioritisation

Token Search applies additional weighting to [verified tokens](/data-api/data-features/safety-and-trust/verified-contracts) to improve result quality.

### How verification affects results

* Tokens listed on **CoinGecko** are treated as verified
* Verified tokens are:
  * Ranked higher by default
  * Preferred over similarly named unverified tokens
* This reduces exposure to spam, clones, and misleading symbols

You can:

* **Boost** verified tokens (default behavior)
* **Filter** results to only verified tokens

***

## Response Data

Each search result may include:

```json theme={null}
{
    "tokenAddress": "0x6982508145454ce325ddbe47a25d4ec3d2311933",
    "chainId": "0x1",
    "name": "Pepe",
    "symbol": "PEPE",
    "blockNumber": 17046105,
    "blockTimestamp": 1681483895,
    "usdPrice": 0.00000660795798374201,
    "marketCap": 2779901844.180426,
    "experiencedNetBuyers": {
        "oneHour": -4,
        "oneDay": -6,
        "oneWeek": 50
    },
    "netVolumeUsd": {
        "oneHour": -109135.83610023865,
        "oneDay": 409602.78393524094
    },
    "liquidityChangeUSD": {
        "oneHour": -102512.48357243836,
        "oneDay": -334000.64153755084
    },
    "usdPricePercentChange": {
        "oneHour": -1.0458516076000621,
        "oneDay": 0.021417598614723917
    },
    "volumeUsd": {
        "oneHour": 190965.87173599334,
        "oneDay": 5241212.457093451
    },
    "securityScore": 96,
    "logo": "https://adds-token-info-29a861f.s3.eu-central-1.amazonaws.com/marketing/evm/0x6982508145454ce325ddbe47a25d4ec3d2311933_icon.png",
    "isVerifiedContract": true,
    "fullyDilutedValuation": 2779901181.0952516,
    "totalHolders": 503992,
    "totalLiquidityUsd": 24553340.56545042,
    "implementations": []
}
```

***

## Limits & Constraints

Current limitations to be aware of:

* Default limit: **10 results**
* Maximum limit: **1000 results**
* No pagination support
* Chain identifiers must be valid and correctly formatted

***

## Usage Guidelines

To get the best results:

* Use precise search queries where possible
* Limit searches to relevant chains
* Use verification filters for safer UX
* Choose appropriate sorting for your use case

***

## Availability & Access

Token Search is a **premium feature** and requires a **Pro plan** or higher.

Trial access can be activated to evaluate the feature before upgrading.
