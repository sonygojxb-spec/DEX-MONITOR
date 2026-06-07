> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Data API Pricing

> Detailed pricing information for our Data API.

For a detailed explanation of Compute Units (CUs) and how they work, check out our [Compute Units section](/get-started/pricing).

***

## Universal API Compute Units

These endpoints support both EVM and Solana chains.

### Token Discovery & Analytics

| Method                                                                                        | CU Cost |
| --------------------------------------------------------------------------------------------- | ------- |
| [searchTokens](/data-api/universal/token/search/token-search)                                 | 150     |
| [getTokenScore](/data-api/universal/token/score/token-score)                                  | 100     |
| [getHistoricalTokenScore](/data-api/universal/token/score/token-score-timeseries)             | 150     |
| [getTokenAnalytics](/data-api/universal/token/analytics/token-analytics)                      | 80      |
| [getMultipleTokenAnalytics](/data-api/universal/token/analytics/token-analytics-multi)        | 150     |
| [getTimeSeriesTokenAnalytics](/data-api/universal/token/analytics/token-analytics-timeseries) | 200     |
| [getFilteredTokens](/data-api/universal/token/filtered-tokens)                                | 250     |
| [getTopGainersTokens](/data-api/universal/token/top-gainers)                                  | 250     |
| [getTopLosersTokens](/data-api/universal/token/top-losers)                                    | 250     |
| [getTrendingTokens](/data-api/universal/token/trending-tokens)                                | 150     |

### Entity API

| Method                                                                           | CU Cost |
| -------------------------------------------------------------------------------- | ------- |
| [searchEntities](/data-api/universal/entity/endpoints/entity-search)             | 50      |
| [getEntity](/data-api/universal/entity/endpoints/entity-by-id)                   | 50      |
| [getEntitiesByCategory](/data-api/universal/entity/endpoints/entity-by-category) | 50      |
| [getEntityCategories](/data-api/universal/entity/endpoints/entity-categories)    | 10      |

### Volume & Market Data

| Method                                                                                                  | CU Cost |
| ------------------------------------------------------------------------------------------------------- | ------- |
| [getVolumeStatsByChain](/data-api/universal/global/endpoints/trading-stats)                             | 150     |
| [getVolumeStatsByCategory](/data-api/universal/global/endpoints/trading-stats-category)                 | 150     |
| [getTimeSeriesVolume](/data-api/universal/global/endpoints/trading-stats-timeseries)                    | 150     |
| [getTimeSeriesVolumeByCategory](/data-api/universal/global/endpoints/trading-stats-category-timeseries) | 150     |

***

## Bitcoin API Compute Units

Bitcoin endpoint costs mirror the closest Web3 API endpoint where applicable. Per-chain wallet endpoints are billed once for each requested chain.

### Bitcoin Blockchain API

| Method                                                           | CU Cost |
| ---------------------------------------------------------------- | ------- |
| [getBlockByNumberOrHash](/data-api/bitcoin/blockchain/block)     | 100     |
| [getTransactionByHash](/data-api/bitcoin/blockchain/transaction) | 10      |

### Bitcoin Price API

| Method                                                              | CU Cost |
| ------------------------------------------------------------------- | ------- |
| [getTokenPrice](/data-api/bitcoin/price/current-price)              | 50      |
| [getTokenPriceTimeSeries](/data-api/bitcoin/price/historical-price) | 50      |
| [getTokenPriceSparkline](/data-api/bitcoin/price/sparkline)         | 50      |

### Bitcoin Wallet API

| Method                                                            | CU Cost       |
| ----------------------------------------------------------------- | ------------- |
| [getWalletHistory](/data-api/bitcoin/wallet/address-transactions) | 150 per chain |
| [getTokenBalances](/data-api/bitcoin/wallet/address-balances)     | 50 per chain  |

### Bitcoin Xpub Utility

| Method                                                              | CU Cost |
| ------------------------------------------------------------------- | ------- |
| [getAddressesByXpub](/data-api/bitcoin/utility/addresses-from-xpub) | 50      |

***

## EVM API Compute Units

### EVM Wallet API

| Method                                                                      | CU Cost       |
| --------------------------------------------------------------------------- | ------------- |
| [getWalletHistory](/data-api/evm/wallet/wallet-history)                     | 150           |
| [getWalletStats](/data-api/evm/wallet/wallet-stats)                         | 50            |
| [getWalletActiveChains](/data-api/evm/wallet/chain-activity)                | 50 per chain  |
| [getWalletTokenBalancesPrice](/data-api/evm/wallet/token-balances)          | 100           |
| [getWalletTokenBalances](/data-api/evm/wallet/token-balances-legacy)        | 100           |
| [getNativeBalance](/data-api/evm/wallet/native-balance)                     | 10            |
| [getNativeBalancesForAddresses](/data-api/evm/wallet/native-balances-batch) | 10 per wallet |
| [getWalletNFTs](/data-api/evm/wallet/nft-balances)                          | 50            |
| [getWalletNFTCollections](/data-api/evm/wallet/nft-collections)             | 50            |
| [getWalletNFTTransfers](/data-api/evm/wallet/nft-transfers)                 | 50            |
| [getNFTTradesByWallet](/data-api/evm/wallet/nft-trades-by-wallet)           | 40            |
| [getWalletTokenTransfers](/data-api/evm/wallet/token-transfers)             | 50            |
| [getWalletTransactions](/data-api/evm/wallet/wallet-transactions)           | 30            |
| [getWalletTransactionsVerbose](/data-api/evm/wallet/decoded-transactions)   | 50            |
| [getWalletApprovals](/data-api/evm/wallet/approvals)                        | 100           |
| [getWalletNetWorth](/data-api/evm/wallet/net-worth)                         | 250 per chain |
| [getWalletProfitability](/data-api/evm/wallet/wallet-pnl)                   | 50            |
| [getWalletProfitabilitySummary](/data-api/evm/wallet/wallet-pnl-summary)    | 30            |
| [getDefiSummary](/data-api/evm/wallet/wallet-protocols)                     | 5000          |
| [getDefiPositionsSummary](/data-api/evm/wallet/wallet-positions)            | 5000          |
| [getDefiPositionsByProtocol](/data-api/evm/wallet/detailed-positions)       | 5000          |
| [getSwapsByWalletAddress](/data-api/evm/wallet/wallet-swaps)                | 50            |
| [resolveENSDomain](/data-api/evm/wallet/ens-lookup)                         | 10            |
| [resolveAddress](/data-api/evm/wallet/resolve-address)                      | 10            |
| [getWalletInsight](/data-api/evm/wallet/wallet-insights)                    | 100 per chain |

### EVM Token API

| Method                                                                            | CU Cost |
| --------------------------------------------------------------------------------- | ------- |
| [getTokenMetadata](/data-api/evm/token/metadata/token-metadata)                   | 10      |
| [getTokenPrice](/data-api/evm/token/prices/token-price)                           | 50      |
| [getMultipleTokenPrices](/data-api/evm/token/prices/token-prices-batch)           | 100     |
| [getPairCandlesticks](/data-api/evm/token/prices/ohlc)                            | 150     |
| [getTokenScore](/data-api/evm/token/metadata/token-score)                         | 100     |
| [getHistoricalTokenScore](/data-api/evm/token/metadata/token-score-timeseries)    | 150     |
| [getTokenHolders](/data-api/evm/token/holders/token-holders)                      | 50      |
| [getHistoricalTokenHolders](/data-api/evm/token/holders/historical-token-holders) | 50      |
| [getTokenStats](/data-api/evm/token/holders/token-holder-stats)                   | 50      |
| [getTokenTransfers](/data-api/evm/token/transfers/token-transfers)                | 50      |
| [getTokenPairs](/data-api/evm/token/swaps/token-pairs)                            | 50      |
| [getSwapsByTokenAddress](/data-api/evm/token/swaps/token-swaps)                   | 50      |
| [getSwapsByPairAddress](/data-api/evm/token/swaps/pair-swaps)                     | 50      |
| [getPairStats](/data-api/evm/token/swaps/pair-stats)                              | 100     |
| [getSnipersByPairAddress](/data-api/evm/token/signals/snipers)                    | 50      |
| [getTopProfitableWalletPerToken](/data-api/evm/token/signals/top-traders)         | 50      |
| [getTokenCategories](/data-api/evm/token/discovery/token-categories)              | 10      |
| [getFilteredTokens](/data-api/evm/token/discovery/filtered-tokens)                | 250     |
| [getTopGainersTokens](/data-api/evm/token/discovery/top-gainers)                  | 250     |
| [getTopLosersTokens](/data-api/evm/token/discovery/top-losers)                    | 250     |

### EVM NFT API

| Method                                                                                      | CU Cost |
| ------------------------------------------------------------------------------------------- | ------- |
| [getNFTMetadata](/data-api/evm/nft/metadata/nft-metadata)                                   | 20      |
| [getMultipleNFTs](/data-api/evm/nft/metadata/nft-metadata-batch)                            | 150     |
| [getNFTContractMetadata](/data-api/evm/nft/metadata/collection-metadata)                    | 50      |
| [getNFTBulkContractMetadata](/data-api/evm/nft/metadata/collection-metadata-batch)          | 5       |
| [getNFTCollectionStats](/data-api/evm/nft/metadata/collection-stats)                        | 50      |
| [getNFTFloorPriceByToken](/data-api/evm/nft/prices/floor)                                   | 30      |
| [getNFTFloorPriceByContract](/data-api/evm/nft/prices/collection-floor-price)               | 30      |
| [getNFTHistoricalFloorPriceByContract](/data-api/evm/nft/prices/historical-floor-price)     | 50      |
| [getNFTSalePrices](/data-api/evm/nft/prices/sale-price-by-token-id)                         | 30      |
| [getNFTContractSalePrices](/data-api/evm/nft/prices/sale-price-by-contract)                 | 1       |
| [getNFTTrades](/data-api/evm/nft/trades/collection-trades)                                  | 40      |
| [getNFTTradesByToken](/data-api/evm/nft/trades/trades-by-token-id)                          | 40      |
| [getNFTOwners](/data-api/evm/nft/ownership/owners-by-contract)                              | 50      |
| [getNFTTokenIdOwners](/data-api/evm/nft/ownership/owners-by-token-id)                       | 50      |
| [getNFTContractTransfers](/data-api/evm/nft/transfers/collection-transfers)                 | 50      |
| [getNFTTransfers](/data-api/evm/nft/transfers/token-id-transfers)                           | 20      |
| [getNFTTraitsByCollection](/data-api/evm/nft/traits/traits-by-collection)                   | 50      |
| [getNFTTraitsByCollectionPaginate](/data-api/evm/nft/traits/traits-by-collection-paginated) | 10      |
| [getNFTByContractTraits](/data-api/evm/nft/traits/nfts-by-traits)                           | 50      |
| [getTopNFTCollectionsByMarketCap](/data-api/evm/nft/discovery/nfts-by-market-cap)           | 200     |
| [getHottestNFTCollectionsByTradingVolume](/data-api/evm/nft/discovery/nfts-by-volume)       | 200     |
| [reSyncMetadata](/data-api/evm/nft/utilities/resync-nft-metadata)                           | 50      |
| [resyncNFTRarity](/data-api/evm/nft/utilities/resync-nft-traits)                            | 10      |

### EVM Price API

| Method                                                                             | CU Cost |
| ---------------------------------------------------------------------------------- | ------- |
| [getTokenPrice](/data-api/evm/price/token-price)                                   | 50      |
| [getMultipleTokenPrices](/data-api/evm/price/token-prices-batch)                   | 100     |
| [getPairCandlesticks](/data-api/evm/price/ohlc)                                    | 150     |
| [getNFTFloorPriceByToken](/data-api/evm/price/token-id-floor-price)                | 30      |
| [getNFTFloorPriceByContract](/data-api/evm/price/collection-floor-price)           | 30      |
| [getNFTHistoricalFloorPriceByContract](/data-api/evm/price/timeseries-floor-price) | 50      |
| [getNFTSalePrices](/data-api/evm/price/sale-price-by-token-id)                     | 30      |
| [getNFTContractSalePrices](/data-api/evm/price/sale-prices-by-collection)          | 1       |

### EVM DeFi API

| Method                                                                     | CU Cost |
| -------------------------------------------------------------------------- | ------- |
| [getDefiSummary](/data-api/evm/defi/wallet-protocols)                      | 5000    |
| [getDefiPositionsSummary](/data-api/evm/defi/wallet-positions)             | 5000    |
| [getDefiPositionsByProtocol](/data-api/evm/defi/wallet-positions-detailed) | 5000    |

### EVM Blockchain API

| Method                                                                                | CU Cost |
| ------------------------------------------------------------------------------------- | ------- |
| [getWalletTransactions](/data-api/evm/blockchain/address-transactions)                | 30      |
| [getWalletTransactionsVerbose](/data-api/evm/blockchain/address-transactions-decoded) | 50      |
| [getDateToBlock](/data-api/evm/blockchain/block-by-date)                              | 1       |
| [getBlock](/data-api/evm/blockchain/block-by-hash)                                    | 100     |
| [getLatestBlockNumber](/data-api/evm/blockchain/latest-block)                         | 10      |
| [getTransaction](/data-api/evm/blockchain/transaction-by-hash)                        | 10      |
| [getTransactionVerbose](/data-api/evm/blockchain/transaction-by-hash-decoded)         | 20      |

***

## Solana API Compute Units

### Solana Wallet API

| Method                                                          | CU Cost |
| --------------------------------------------------------------- | ------- |
| [balance](/data-api/solana/wallet/native-balance)               | 10      |
| [getSPL](/data-api/solana/wallet/token-balances)                | 10      |
| [getNFTs](/data-api/solana/wallet/nft-balances)                 | 10      |
| [getPortfolio](/data-api/solana/wallet/portfolio)               | 10      |
| [getSwapsByWalletAddress](/data-api/solana/wallet/wallet-swaps) | 50      |

### Solana Token API

| Method                                                                                                | CU Cost |
| ----------------------------------------------------------------------------------------------------- | ------- |
| [getTokenMetadata](/data-api/solana/token/token-metadata)                                             | 10      |
| [getMultipleTokenMetadata](/data-api/solana/token/token-metadata-batch)                               | 100     |
| [getTokenScore](/data-api/solana/token/token-score)                                                   | 100     |
| [getHistoricalTokenScore](/data-api/solana/token/token-score-timeseries)                              | 150     |
| [getTokenPrice](/data-api/solana/token/prices/token-price)                                            | 10      |
| [getMultipleTokenPrices](/data-api/solana/token/prices/token-prices-batch)                            | 100     |
| [getCandleSticks](/data-api/solana/token/prices/ohlc)                                                 | 150     |
| [getTopHolders](/data-api/solana/token/holders/top-holders)                                           | 50      |
| [getHistoricalTokenHolders](/data-api/solana/token/holders/historical-holders)                        | 50      |
| [getTokenHolders](/data-api/solana/token/holders/holder-metrics)                                      | 50      |
| [getTokenPairs](/data-api/solana/token/pairs/token-pairs)                                             | 50      |
| [getSwapsByTokenAddress](/data-api/solana/token/swaps/token-swaps)                                    | 50      |
| [getSwapsByPairAddress](/data-api/solana/token/pairs/pair-swaps)                                      | 50      |
| [getPairStats](/data-api/solana/token/pairs/pair-stats)                                               | 100     |
| [getAggregatedTokenPairStats](/data-api/solana/token/market-metrics/token-analytics)                  | 80      |
| [getSnipersByPairAddress](/data-api/solana/token/advanced-signals/snipers)                            | 50      |
| [getNewTokensByExchange](/data-api/solana/token/search-and-discovery/pump-fun-new-tokens)             | 50      |
| [getGraduatedTokensByExchange](/data-api/solana/token/search-and-discovery/pump-fun-graduated-tokens) | 50      |
| [getBondingTokensByExchange](/data-api/solana/token/search-and-discovery/pump-fun-bonding-tokens)     | 50      |
| [getTokenBondingStatus](/data-api/solana/token/search-and-discovery/pump-fun-bonding-status)          | 20      |

### Solana NFT API

| Method                                              | CU Cost |
| --------------------------------------------------- | ------- |
| [getNFTMetadata](/data-api/solana/nft/nft-metadata) | 10      |

### Solana Price API

| Method                                                              | CU Cost |
| ------------------------------------------------------------------- | ------- |
| [getTokenPrice](/data-api/solana/price/token-price)                 | 10      |
| [getMultipleTokenPrices](/data-api/solana/price/token-prices-batch) | 100     |
| [getCandleSticks](/data-api/solana/price/ohlc)                      | 150     |
