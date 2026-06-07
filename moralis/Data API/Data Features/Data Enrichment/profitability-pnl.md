> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Profitability (PnL)

> Analyze realized wallet and token profitability using Moralis PnL endpoints. Learn how realized PnL is calculated, supported swaps, pricing logic, chain coverage, and known limitations. 

## Overview

Moralis provides **realized profit and loss (PnL)** analytics for wallets and tokens, calculated directly from **on-chain swap activity**.

PnL data is designed for:

* Wallet analytics
* Trading performance dashboards
* Portfolio tools
* Token-level profitability analysis
* Leaderboards and rankings

***

## Supported PnL endpoints

PnL data is exposed through the following endpoints:

* [Wallet PnL Summary](/data-api/evm/wallet/wallet-pnl-summary)\
  High-level profitability metrics for a wallet
* [Wallet PnL Breakdown](/data-api/evm/wallet/wallet-pnl)\
  Token-by-token profitability details
* [Top Traders by Token](/data-api/evm/token/signals/top-traders)\
  Rankings of wallets by realized profit for a given token

***

## What type of PnL is supported?

Moralis currently supports **realized PnL only**.

* **Realized PnL** is calculated from completed on-chain swaps (buys and sells).
* **Unrealized PnL** (open positions based on current market prices) is **not calculated directly** by the PnL endpoints.

#### Calculating Unrealized PnL

You can calculate unrealized PnL yourself by combining:

* **Cost basis / realized trade data** from the [PnL endpoints](/data-api/evm/wallet/wallet-pnl)
* **Real-time token balances + real-time prices** from the [Token Balances](/data-api/evm/wallet/token-balances) endpoint

A common approach is:

```
(currentPrice − averageCost) × currentTokenBalance
```

This approach gives you full flexibility to build portfolio views that include:

* Realized PnL
* Unrealized PnL
* Total PnL (realized + unrealized)

***

## How PnL is calculated

Moralis uses a method closely aligned with a **weighted average cost basis**.

### Core formula

```
(avgSellPriceUsd − avgCostOfQuantitySold) × totalTokensSold
```

Where:

* **avgSellPriceUsd**\
  Continuously updated average sell price in USD
* **avgCostOfQuantitySold**\
  Calculated as:\
  `totalUsdInvested / totalTokensBought`

This ensures profits are calculated based on **actual cost basis**, not FIFO or speculative pricing.

***

## How trades are matched

PnL is calculated **per trading pair**, not per token globally.

Examples:

* Buy `UNI` with `WETH` → tracked as `UNI/WETH`
* Sell `UNI` for `WETH` → updates the same trade
* Sell `UNI` for `PEPE` → tracked as a **new trade** (`UNI/PEPE`)

This avoids mixing unrelated price contexts.

***

## Token pricing & trade history

Moralis determines token prices by:

1. Indexing on-chain **DEX swap events**
2. Extracting price directly from swap logs
3. Converting swap prices to USD
4. Applying those prices to PnL calculations

No off-chain price feeds are used for PnL.

***

## Supported swap events

Currently supported swap topics:

* **Uniswap V2**

```
0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822
```

* **Uniswap V3**

```
0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67
```

Only swaps emitting these events are included in PnL.

***

## Transaction fees

**Gas fees and transaction fees are not included** in PnL calculations.

PnL strictly reflects **token-level trading performance**, not net wallet balance changes.

***

## Update latency

PnL data updates in **near real-time**.

* Average update time: **\~10 seconds**
* Triggered after swap settlement on-chain

This makes PnL suitable for:

* Live dashboards
* Trading analytics
* Near real-time alerts

***

## Token Support

### ERC20 Tokens

PnL is supported for **all ERC20 tokens** that:

* Have participated in a **supported DEX swap**
* Emit **supported swap events**
* Are **paired with either**:
  * a **stablecoin** (e.g. USDC, USDT, DAI), or
  * a **native or wrapped native token** (e.g. ETH, WETH)

This covers the vast majority of actively traded ERC20 tokens.

***

### Native Tokens (e.g. ETH)

* ***Native tokens are supported for PnL***, **but only when traded against stablecoins**.
* Trades between native tokens and stablecoins are used to establish realized PnL.

Examples:

* ✅ ETH ↔ USDC → ETH PnL supported
* ❌ ETH ↔ WETH → not tracked (native ↔ wrapped native)

Native tokens are treated similarly to ERC20s **only when a stablecoin price anchor exists**.

***

### Wrapped Native Tokens (e.g. WETH)

* **Wrapped native tokens are supported**, **but only when traded against stablecoins**.
* They are **not tracked when traded against native tokens or other wrapped natives**.

Examples:

* ✅ WETH ↔ USDC → WETH PnL supported
* ❌ WETH ↔ ETH → not tracked
* ❌ WETH ↔ WBTC → not tracked unless a stablecoin leg exists

***

### Stablecoins

* **Wallet PnL is not calculated for stablecoins themselves** (e.g. USDC, USDT, DAI).
* However, **ERC20, native, and wrapped native tokens that are paired with stablecoins are fully supported**.

Examples:

* ✅ UNI ↔ USDC → UNI PnL supported
* ✅ ETH ↔ USDT → ETH PnL supported
* ❌ USDC ↔ DAI → no wallet PnL (stablecoin-only trade)

Stablecoins act as **pricing anchors**, not PnL assets.

***

### Summary

| Asset                              | PnL tracked? | Conditions                                  |
| :--------------------------------- | :----------- | :------------------------------------------ |
| ERC20 tokens                       | ✅ Yes        | Paired with stable or native/wrapped native |
| Native tokens (ETH, etc.)          | ✅ Yes        | **Only when paired with stablecoins**       |
| Wrapped native tokens (WETH, etc.) | ✅ Yes        | **Only when paired with stablecoins**       |
| Stablecoins                        | ❌ No         | Used for pricing only                       |
| ERC20 ↔ Stablecoin                 | ✅ Yes        | Fully supported                             |
| ERC20 ↔ WETH                       | ✅ Yes        | Fully supported                             |
| ETH ↔ USDC                         | ✅ Yes        | Supported                                   |
| ETH ↔ WETH                         | ❌ No         | Not supported                               |

***

## Supported chains

Profitability is currently live on:

* **Ethereum Mainnet**
* **Polygon Mainnet**
* **Base Mainnet**

More chains are planned.

***

## Known limitations

* Unrealized gains are not included
* Gas costs are excluded
* Only supported DEX events are tracked
* PnL is per trading pair, not global per token

These trade-offs are intentional to ensure **accuracy and determinism**.

***

## Summary

Moralis Profitability (PnL) provides:

* Realized, on-chain PnL
* Weighted average cost basis
* Near real-time updates
* Token- and wallet-level views
* Deterministic, explainable calculations

It’s built for **analytics accuracy**, not speculative valuation.
