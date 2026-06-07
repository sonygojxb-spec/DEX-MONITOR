> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Solana DeFi API

> Track DeFi positions, balances, and rewards across the most-used Solana protocols using the same Universal API endpoints as EVM.

## Overview

The **Solana DeFi API** provides a unified view of a wallet's DeFi positions across the most-used Solana protocols - lending, borrowing, staking, liquid staking, and liquidity pools.

The same three Universal API endpoints used for EVM DeFi positions now return Solana data, with no schema changes and no separate integration.

***

## What Is the Solana DeFi API?

The Solana DeFi API lets you query:

* **Protocol Summary** - Overview of all Solana DeFi protocols a wallet uses
* **Positions** - Detailed position data per protocol
* **Position Details** - Enhanced breakdown with underlying assets
* **Multi-Chain in One Call** - Query EVM and Solana wallets through the same endpoints

***

## Key Features

* **Protocol Detection** - Automatically identifies which Solana protocols a wallet uses
* **Position Breakdown** - Detailed view of deposits, borrows, staking, and rewards
* **USD Valuations** - Position values calculated in USD
* **Unified Schema** - Identical response shape across EVM and Solana
* **Single Integration** - Same filters and parameters as the EVM DeFi API

***

## Supported Protocols

The Solana DeFi API supports 10 of the most-used protocols on Solana - together covering roughly 90% of Solana DeFi TVL, including the top protocols by TVL (Jupiter, Kamino, Sanctum, and Raydium):

* Jito
* Save (formerly Solend)
* Jupiter Lend
* Jupiter Perpetual Exchange
* Kamino Lend
* Sanctum
* Raydium
* Orca
* Drift
* Marinade

More Solana protocols are being added on a rolling basis. If you need a specific protocol prioritized, [reach out to the team](https://moralis.com/contact-sales).

***

## Common Use Cases

The Solana DeFi API is commonly used for:

* **Portfolio Trackers**\
  (show Solana DeFi positions alongside SPL tokens and NFTs)
* **DeFi Dashboards**\
  (aggregate positions across Solana protocols)
* **Cross-Ecosystem Wallets**\
  (display EVM and Solana DeFi positions side by side)
* **Yield Tracking**\
  (monitor staking rewards and LP positions on Solana)
* **Tax Reporting**\
  (calculate DeFi gains and income across Solana)

***

## Popular Endpoints

| Endpoint                                                              | Description                                  |
| --------------------------------------------------------------------- | -------------------------------------------- |
| [Wallet Protocols](/data-api/solana/defi/wallet-protocols)            | Summary of Solana protocols used by a wallet |
| [Wallet Positions](/data-api/solana/defi/wallet-positions)            | Detailed Solana positions per protocol       |
| [Detailed Positions](/data-api/solana/defi/wallet-positions-detailed) | Enhanced Solana position breakdown           |

***

## Get Started

* [Get Wallet Protocols](/data-api/solana/defi/wallet-protocols)
* [Get Wallet Positions](/data-api/solana/defi/wallet-positions)
* [Get Detailed Positions](/data-api/solana/defi/wallet-positions-detailed)

***

## Get Solana DeFi Data in 1 API Call

<iframe src="https://www.youtube.com/embed/Q3W3RFj42bE" title="Get Solana DeFi Data in 1 API Call" width="100%" height="400" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
