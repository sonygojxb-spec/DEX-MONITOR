> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Prices

> Learn how Moralis token prices are derived from onchain DEX activity, including pool selection, pair-based pricing, liquidity filtering, inactivity rules, and mainnet-only behavior.

## Token Prices

Moralis token prices are derived directly from **onchain DEX activity**, not from aggregated offchain price feeds.

Prices are based on real swaps, making them:

* Trust-minimized (no centralized oracle dependency)
* Chain-specific
* Deterministic and reproducible

Prices can be fetched:

* **By token address** (Moralis selects the best pool automatically), or
* **Directly by pair address**, when you want full control over which pool is used

Related concepts:

* [Supported DEXes](/data-api/data-features/integrations/supported-dexs)
* [Liquidity Filtering](/data-api/data-features/safety-and-trust/liquidity-filtering)

***

## How Token Prices Work

Moralis calculates token prices using the **last traded price** observed on supported decentralized exchanges.

Key characteristics:

* Prices come from real onchain swap events
* No volume-weighted averaging across exchanges
* Prices are returned in USD
* Pricing can be **pool-selected automatically** or **explicitly defined by pair**

This makes token prices safe to use in downstream features such as [Token Balances](/data-api/evm/wallet/token-balances), [Wallet Net Worth](/data-api/evm/wallet/net-worth), [PnL](/data-api/evm/wallet/wallet-pnl) and many more.

***

## Fetching Prices by Token vs Pair

Moralis supports two pricing models:

### Token-Based Pricing (Default)

When querying by token address:

* Moralis automatically selects the most appropriate pool
* Pool selection follows liquidity and activity rules
* Best suited for portfolio, net worth, and analytics use cases

This is the recommended approach for most applications.

Related pages:

* [Token price by token address](/data-api/evm/token/prices/token-price)
* [Token price by pair address](/data-api/evm/token/swaps/pair-stats)

***

### Pair-Based Pricing (Explicit Pool)

You can also fetch prices **directly by pair address**.

When querying by pair:

* The specified pool is always used
* No pool ranking or substitution occurs
* The price reflects swaps in that exact pair

This is useful when:

* You need deterministic pricing from a known pool
* You want to inspect or monitor a specific market
* You are building trading, monitoring, or analytics tools around a single pair

Liquidity and inactivity checks still apply to ensure price safety.

***

## Supported Pair Types

Moralis supports **all DEX pair types**, including:

* **Stablecoin pairs** (e.g. USDC / USDT / DAI)
* **Wrapped native token pairs** (e.g. WETH, WBNB, SOL)
* **Token / Token pairs** (e.g. REPPO / VIRTUAL)

This applies to both **token-based** and **pair-based** price queries, as long as sufficient onchain liquidity exists.

***

## Mainnet-Only Support

Token prices are **mainnet-only**.

Why:

* Prices depend on active onchain DEX liquidity
* Testnets generally lack sustained or meaningful trading activity

Any feature that depends on token prices is therefore also mainnet-only, including:

* Token price
* Wallet net worth
* Portfolio percentages
* PnL calculations

***

## What “Price” Means

A token’s price represents:

* The most recent swap price
* Extracted from the DEX swap log
* Converted to USD

For Token / Token pairs, the price is resolved from the selected pair and converted to USD using the best available onchain reference.

When querying by pair address, this conversion is based strictly on that pool’s swap activity.

***

### Multiple Swaps in the Same Block

If multiple swaps occur within a single block:

* The **final swap price in that block** is used
* Intra-block price movements are not tracked

This keeps pricing deterministic and avoids block-level noise.

***

## Pool Selection Logic (Token-Based Pricing)

When querying prices by token address:

### Real-Time Prices

1. Pools that fail [liquidity filtering](/data-api/data-features/safety-and-trust/liquidity-filtering) are excluded
2. Remaining pools are ranked by swap activity over the last 24 hours
3. The most active pool is selected

### Historical Prices

1. The top two pools by lifetime usage are selected
2. The most recent record from each pool is compared
3. The pool with higher liquidity is chosen

Pair-based queries bypass this logic and always use the specified pool.

***

## Liquidity Thresholds

Moralis enforces minimum liquidity requirements per chain.

Default thresholds:

* **EVM chains:** \$50 minimum liquidity per side (each token in the pair)
* **Solana:** no enforced liquidity threshold

This threshold applies at the pool level and is evaluated for both assets in the pair. The pool is considered eligible only if **both sides** meet the minimum threshold.

Read more about [Liquidity Thresholds](/data-api/data-features/safety-and-trust/liquidity-filtering).

***

## Inactivity Handling

Tokens or pairs with no recent trading activity can be excluded.

Use the `max_token_inactivity` query parameter to filter out inactive markets.

This applies to:

* Token-based pricing
* Pair-based pricing
* Token balances

***

## Common Error Scenarios

You may encounter the following:

* **No liquidity pool found**\
  No qualifying pool exists for the token or pair
* **Insufficient liquidity**\
  Pool fails liquidity filtering
* **Inactive market**\
  Token or pair fails inactivity filtering
* **Testnet request**\
  Token prices are not supported on testnets

***

## When to Use Token Prices (and When Not To)

Token prices are well-suited for:

* Wallet net worth calculations
* Portfolio tracking
* PnL and trading analytics
* Token discovery and filtering

Pair-based pricing is best suited for:

* Market monitoring
* Trading analytics
* Pool-specific dashboards

They are not intended to replace:

* High-frequency trading price feeds
* Offchain oracle systems
* Tick-level or order-book pricing data
