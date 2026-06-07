> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Liquidity Filtering

> Understand how Moralis uses liquidity filtering to protect price accuracy, including default thresholds, how pair-side liquidity is evaluated for both tokens in a pool, endpoint behavior, and custom liquidity controls.

## Liquidity Filtering

Liquidity Filtering is a safety mechanism used across Moralis price-dependent features to avoid returning unreliable or easily manipulated prices.

It ensures that prices are only derived from pools with sufficient onchain liquidity, making downstream data (net worth, PnL, analytics) safer and more predictable.

Liquidity filtering is applied across:

* [Token Prices](/data-api/evm/token/prices/token-prices-batch)
* [Wallet Token Balances](/data-api/evm/wallet/token-balances) (with prices)
* [Wallet Net Worth](/data-api/evm/wallet/net-worth)
* Other price-dependent features

***

## Why Liquidity Filtering Exists

Onchain markets often include:

* Thin or inactive pools
* Short-lived pools created for manipulation
* Pools where one side has meaningful liquidity but the other side is effectively empty

Without liquidity filtering, these pools can:

* Produce unstable or misleading prices
* Inflate portfolio values
* Distort rankings and analytics

Liquidity filtering acts as a minimum quality bar for any price Moralis returns.

***

## Default Liquidity Thresholds

Moralis enforces minimum liquidity requirements per chain.

Default thresholds:

* **EVM chains:** \$50 minimum liquidity per side (each token in the pair)
* **Solana:** no enforced liquidity threshold

This threshold applies at the pool level and is evaluated for both assets in the pair.

***

## What “pair-side liquidity” means

“Pair-side liquidity” means the USD liquidity of **each token in the pool**, evaluated independently.

For a TOKEN / USDC pool, Moralis checks:

* TOKEN-side liquidity (in USD)
* USDC-side liquidity (in USD)

The pool is considered eligible only if **both sides** meet the minimum threshold.

### Why this approach

This prevents pools where one side is effectively illiquid, even if the other side looks healthy.

Example:

* TOKEN liquidity: \$100,000
* USDC liquidity: \$10

Even though the TOKEN side is deep, the USDC side is too small for the pool to be a reliable pricing venue, so Moralis excludes it.

This is especially important for:

* Long-tail tokens
* Manipulation-resistant pricing
* Stable portfolio and net worth calculations

***

## Liquidity Skew

Get Token Pairs ([EVM](/data-api/evm/token/swaps/token-pairs), [Solana](/data-api/solana/token/pairs/token-pairs)) exposes a property that measures how balanced a pair's reserves are across both sides of the pool. It is named `liquidity_skew` on EVM and `liquiditySkew` on Solana.

* `1` = perfectly balanced reserves
* `0` = fully imbalanced (liquidity concentrated on one side)

When this value is below `0.005`, the pair's liquidity is treated as `0`. This prevents heavily one-sided pools, where one side is effectively empty, from being used as a reliable pricing venue.

***

## Low Liquidity Behavior

When a pool fails liquidity filtering, behavior depends on the endpoint.

* [Get Token Price](/data-api/evm/token/prices/token-price)\
  Returns a `404` error indicating insufficient liquidity
* [Get Multiple Token Prices](/data-api/evm/token/prices/token-prices-batch)\
  The token is omitted from the response
* [Wallet Token Balances](/data-api/evm/wallet/token-balances) (with prices)\
  Token price is returned as `null`
* [Wallet Net Worth](/data-api/evm/wallet/net-worth)\
  Token is excluded from the net worth calculation

This behavior is intentional and consistent across price-dependent features.

***

## Consistency Across Features

Liquidity filtering is applied uniformly so that:

* A pool excluded from Token Prices\
  will not silently be used to value assets in Wallet Net Worth
* A token with `null` price in balances\
  will not inflate portfolio values unexpectedly

This consistency is critical for building reliable dashboards, analytics, and valuation logic.

***

## Custom Liquidity Thresholds

You can override the default threshold using the `min_pair_side_liquidity_usd` query parameter.

Example:\
`min_pair_side_liquidity_usd=5000`

This ensures that only pools where **both sides** have at least \$5,000 USD liquidity are considered.

***

### Common Use Cases for Custom Thresholds

* Risk-averse or institutional reporting
* Cleaner portfolio and net worth calculations
* Excluding long-tail or thinly traded tokens
* Reducing exposure to short-lived or manipulated pools

***

## What Liquidity Filtering Does Not Do

Liquidity filtering:

* Does not guarantee market fairness
* Does not detect scams by itself
* Does not replace deeper risk analysis

It is one component of Moralis’ broader Safety & Trust model and should be used alongside:

* [Token Scores](/data-api/data-features/token-scores)
* [Spam Filtering](/data-api/resources/spam-filtering)
* [Verified Contracts](/data-api/data-features/safety-and-trust/verified-contracts)
