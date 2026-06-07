> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Premium Endpoints

> Endpoints that require a paid plan to access.

## Overview

Premium endpoints provide access to advanced analytics, market metrics, token discovery, and DeFi features. These endpoints require an API key on the plan listed for each endpoint or above.

***

## DeFi API

| Endpoint                                                                                                                            | Method | Path                                                    | Required Plan | CUs  |
| ----------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------- | ------------- | ---- |
| Wallet Protocols ([EVM](/data-api/evm/defi/wallet-protocols), [Solana](/data-api/solana/defi/wallet-protocols))                     | GET    | `/v1/wallets/{walletAddress}/defi/summary`              | Starter       | 5000 |
| Wallet Positions ([EVM](/data-api/evm/defi/wallet-positions), [Solana](/data-api/solana/defi/wallet-positions))                     | GET    | `/v1/wallets/{walletAddress}/defi/positions`            | Starter       | 5000 |
| Detailed Positions ([EVM](/data-api/evm/defi/wallet-positions-detailed), [Solana](/data-api/solana/defi/wallet-positions-detailed)) | GET    | `/v1/wallets/{walletAddress}/defi/{protocol}/positions` | Starter       | 5000 |

***

## Wallet

| Endpoint                                                | Method | Path                         | Required Plan | CUs |
| ------------------------------------------------------- | ------ | ---------------------------- | ------------- | --- |
| [Wallet Insights](/data-api/evm/wallet/wallet-insights) | GET    | `/wallets/{address}/insight` | Pro           | 100 |

***

## Token Analytics

| Endpoint                                                                                       | Method | Path                                      | Required Plan | CUs |
| ---------------------------------------------------------------------------------------------- | ------ | ----------------------------------------- | ------------- | --- |
| [Token Score](/data-api/evm/token/metadata/token-score)                                        | GET    | `/tokens/{tokenAddress}/score`            | Pro           | 100 |
| [Token Score - Timeseries](/data-api/evm/token/metadata/token-score-timeseries)                | GET    | `/tokens/{tokenAddress}/score/historical` | Pro           | 150 |
| [Token Analytics (Batch)](/data-api/universal/token/analytics/token-analytics-multi)           | POST   | `/tokens/analytics`                       | Pro           | 150 |
| [Token Analytics - Timeseries](/data-api/universal/token/analytics/token-analytics-timeseries) | POST   | `/tokens/analytics/timeseries`            | Pro           | 200 |

***

## Token Discovery

| Endpoint                                                           | Method | Path                            | Required Plan | CUs |
| ------------------------------------------------------------------ | ------ | ------------------------------- | ------------- | --- |
| [Token Search](/data-api/universal/token/search/token-search)      | GET    | `/tokens/search`                | Pro           | 150 |
| [Filtered Tokens](/data-api/universal/token/filtered-tokens)       | POST   | `/discovery/tokens`             | Pro           | 250 |
| [Top Gainers](/data-api/universal/token/top-gainers)               | GET    | `/discovery/tokens/top-gainers` | Pro           | 250 |
| [Top Losers](/data-api/universal/token/top-losers)                 | GET    | `/discovery/tokens/top-losers`  | Pro           | 250 |
| [Token Categories](/data-api/evm/token/discovery/token-categories) | GET    | `/tokens/categories`            | Pro           | 10  |
| [Trending Tokens](/data-api/universal/token/trending-tokens)       | GET    | `/tokens/trending`              | Pro           | 150 |

***

## Volume & Market Metrics

| Endpoint                                                                                                | Method | Path                              | Required Plan | CUs |
| ------------------------------------------------------------------------------------------------------- | ------ | --------------------------------- | ------------- | --- |
| [Chain Metrics](/data-api/universal/global/endpoints/trading-stats)                                     | GET    | `/volume/chains`                  | Pro           | 150 |
| [Chain Metrics - Timeseries](/data-api/universal/global/endpoints/trading-stats-timeseries)             | GET    | `/volume/timeseries`              | Pro           | 150 |
| [Category Metrics](/data-api/universal/global/endpoints/trading-stats-category)                         | GET    | `/volume/categories`              | Pro           | 150 |
| [Category Metrics - Timeseries](/data-api/universal/global/endpoints/trading-stats-category-timeseries) | GET    | `/volume/timeseries/{categoryId}` | Pro           | 150 |

***

## Upgrade Your Plan

To access premium endpoints, upgrade your plan at [admin.moralis.io](https://admin.moralis.io).
