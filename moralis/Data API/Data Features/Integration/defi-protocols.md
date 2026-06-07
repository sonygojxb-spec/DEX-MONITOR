> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# DeFi Protocols

> DeFi protocol coverage across EVM and Solana, how protocol decoding works, and how to fetch the full, always-current list of supported protocols from the API.

Moralis decodes DeFi activity - lending, borrowing, staking, liquid staking, and liquidity pools - across **thousands of protocols on EVM chains** and the **top protocols on Solana**, returning enriched, protocol-aware positions through the [DeFi API](/data-api/universal/defi/overview).

Coverage expands continuously, so the API itself is the source of truth for what is supported at any given moment.

<Note>
  This page covers **protocol availability**. To fetch a wallet's actual DeFi **balances and positions**, use the DeFi API endpoints — [Wallet Protocols](/data-api/universal/defi/wallet-protocols), [Wallet Positions](/data-api/universal/defi/wallet-positions), and [Detailed Positions](/data-api/universal/defi/wallet-positions-detailed) — each accepts the `chain` parameter for EVM or Solana.
</Note>

## Fetch the Full List of Supported Protocols

Use the [**Get Supported DeFi Protocols**](/data-api/universal/defi/supported-protocols) endpoint to retrieve the complete, current list of supported protocols with their chain coverage - ideal for keeping your own UI or coverage checks in sync:

```bash theme={null}
curl "https://api.moralis.com/v1/defi/protocols?chains=eth" \
  -H "X-Api-Key: YOUR_API_KEY"
```

Pass the optional `chains` filter (for example `eth`, `base`, `polygon`, or `solana`) to narrow results to specific chains.

<Info>
  By default, we track all forked Uniswap v2 protocols. If a particular protocol has not yet been decoded, it appears as `unknown` in API responses - [reach out to support](https://moralis.com/contact-sales) and we will prioritize decoding it.
</Info>

## EVM Coverage

DeFi protocol decoding is available across these EVM chains:

* Arbitrum
* Avalanche
* Base
* Binance
* Ethereum
* Linea
* Monad
* Optimism
* Polygon
* Sei

<Note>
  **Coverage is not uniform across chains.** Protocol availability depends on where each protocol is deployed and its adoption per chain. Query the endpoint above for exact per-chain support.
</Note>

We support thousands of EVM protocols, including all forked Uniswap v2 protocols. A few of the most widely used, with their query parameters:

| Protocol       | Query Parameter  | Example Chains                                                  |
| -------------- | ---------------- | --------------------------------------------------------------- |
| Aave v3        | `aave-v3`        | Base, Ethereum, Polygon                                         |
| Uniswap v3     | `uniswap-v3`     | Arbitrum, Avalanche, Base, Binance, Ethereum, Optimism, Polygon |
| Pancakeswap v3 | `pancakeswap-v3` | Arbitrum, Base, Binance, Ethereum, Linea, Monad                 |
| Lido           | `lido`           | Ethereum                                                        |
| Rocket Pool    | `rocketpool`     | Arbitrum, Base, Ethereum, Optimism, Polygon                     |
| Eigenlayer     | `eigenlayer`     | Ethereum                                                        |
| MakerDAO       | `makerdao`       | Ethereum                                                        |
| Pendle         | `pendle`         | Ethereum                                                        |

This is a curated highlight, not the full list - call the endpoint above for complete, up-to-date coverage.

## Solana Coverage

The Solana DeFi API supports **10 protocols**, together covering roughly **90% of Solana DeFi TVL** - including the top protocols by TVL (Jupiter, Kamino, Sanctum, and Raydium):

| Protocol                   | Category       |
| -------------------------- | -------------- |
| Jupiter Lend               | Lending        |
| Jupiter Perpetual Exchange | Perpetuals     |
| Kamino Lend                | Lending        |
| Sanctum                    | Liquid staking |
| Save (formerly Solend)     | Lending        |
| Raydium                    | DEX / AMM      |
| Orca                       | DEX / AMM      |
| Drift                      | Perpetuals     |
| Jito                       | Liquid staking |
| Marinade                   | Liquid staking |

See the [DeFi API](/data-api/universal/defi/overview) for endpoints and examples — the same cross-chain endpoints return Solana and EVM positions.

More protocols are added on a rolling basis. To request prioritization of a specific protocol, [reach out to the team](https://moralis.com/contact-sales).
