> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Global API Reference

This is a single, consolidated quick-reference catalog of the Moralis Data API endpoints.

A unified API to fetch balances, transfers, DeFi positions, PnL, NFTs, and fully decoded wallet activity across multiple chains.

### EVM Wallet API

A comprehensive suite of wallet-focused endpoints: balances, history, DeFi positions, PnL, approvals, and identity resolution.

| Endpoint                                                              | Description                                    |
| :-------------------------------------------------------------------- | :--------------------------------------------- |
| [Wallet History](/data-api/evm/wallet/wallet-history)                 | Complete decoded activity feed for a wallet.   |
| [Wallet Transactions](/data-api/evm/wallet/wallet-transactions)       | Raw transaction list for a wallet.             |
| [Decoded Transactions](/data-api/evm/wallet/decoded-transactions)     | Human-readable transaction data and summaries. |
| [Token Balances](/data-api/evm/wallet/token-balances)                 | Current ERC-20 holdings for a wallet.          |
| [Token Balances (Legacy)](/data-api/evm/wallet/token-balances-legacy) | Legacy token balance endpoint.                 |
| [Token Transfers](/data-api/evm/wallet/token-transfers)               | ERC-20 transfer history for a wallet.          |
| [Native Balance](/data-api/evm/wallet/native-balance)                 | Native currency balance for a wallet.          |
| [Native Balances (Batch)](/data-api/evm/wallet/native-balances-batch) | Native balances for multiple wallets.          |
| [NFT Balances](/data-api/evm/wallet/nft-balances)                     | Current NFT holdings for a wallet.             |
| [NFT Collections](/data-api/evm/wallet/nft-collections)               | NFT collections held by a wallet.              |
| [NFT Transfers](/data-api/evm/wallet/nft-transfers)                   | NFT transfer history for a wallet.             |
| [NFT Trades](/data-api/evm/wallet/nft-trades-by-wallet)               | NFT trade history for a wallet.                |
| [Net Worth](/data-api/evm/wallet/net-worth)                           | Total wallet value in USD.                     |
| [Wallet P\&L](/data-api/evm/wallet/wallet-pnl)                        | Profit / loss calculated per token.            |
| [Wallet P\&L Summary](/data-api/evm/wallet/wallet-pnl-summary)        | Aggregated profit / loss summary.              |
| [Wallet Stats](/data-api/evm/wallet/wallet-stats)                     | General wallet statistics.                     |
| [Wallet Swaps](/data-api/evm/wallet/wallet-swaps)                     | DEX swap history for a wallet.                 |
| [Approvals](/data-api/evm/wallet/approvals)                           | Token approval / allowance data for a wallet.  |
| [Chain Activity](/data-api/evm/wallet/chain-activity)                 | Multi-chain activity summary for a wallet.     |
| [Wallet Protocols](/data-api/evm/wallet/wallet-protocols)             | Summary of DeFi protocols used by a wallet.    |
| [Wallet Positions](/data-api/evm/wallet/wallet-positions)             | DeFi positions per protocol.                   |
| [Detailed Positions](/data-api/evm/wallet/detailed-positions)         | Enhanced DeFi position breakdown.              |
| [ENS Lookup](/data-api/evm/wallet/ens-lookup)                         | Resolve an ENS name to an address.             |
| [Resolve Address](/data-api/evm/wallet/resolve-address)               | Reverse-resolve an address to an ENS name.     |

### EVM Token API

The most powerful Token API in Web3 — fetch, analyse, and monitor ERC-20 tokens across multiple chains, covering prices, balances, transfers, liquidity, holders, volume, profitability, and advanced safety signals.

#### Prices

| Endpoint                                                              | Description                                     |
| :-------------------------------------------------------------------- | :---------------------------------------------- |
| [Token Price](/data-api/evm/token/prices/token-price)                 | Get real-time and historical price for a token. |
| [Token Prices (Batch)](/data-api/evm/token/prices/token-prices-batch) | Get prices for multiple tokens in one call.     |
| [OHLC Candlesticks](/data-api/evm/token/prices/ohlc)                  | Get historical OHLC (Open-High-Low-Close) data. |

#### Transfers

| Endpoint                                                         | Description                                       |
| :--------------------------------------------------------------- | :------------------------------------------------ |
| [Token Transfers](/data-api/evm/token/transfers/token-transfers) | Get transfer history by wallet or token contract. |

#### Metadata

| Endpoint                                                                      | Description                                         |
| :---------------------------------------------------------------------------- | :-------------------------------------------------- |
| [Token Metadata](/data-api/evm/token/metadata/token-metadata)                 | Get token details including name, symbol, and logo. |
| [Token Score](/data-api/evm/token/metadata/token-score)                       | Get safety / quality score for a token.             |
| [Token Score Timeseries](/data-api/evm/token/metadata/token-score-timeseries) | Historical token score data over time.              |

#### Pairs & Swaps

| Endpoint                                             | Description                                          |
| :--------------------------------------------------- | :--------------------------------------------------- |
| [Token Pairs](/data-api/evm/token/swaps/token-pairs) | Get DEX trading pairs, reserves, and liquidity data. |
| [Pair Stats](/data-api/evm/token/swaps/pair-stats)   | Get stats for a specific DEX pair.                   |
| [Pair Swaps](/data-api/evm/token/swaps/pair-swaps)   | Get recent swaps for a specific pair.                |
| [Token Swaps](/data-api/evm/token/swaps/token-swaps) | Get swap history for a token.                        |

#### Holders

| Endpoint                                                                         | Description                             |
| :------------------------------------------------------------------------------- | :-------------------------------------- |
| [Token Holders](/data-api/evm/token/holders/token-holders)                       | Get current holders of a token.         |
| [Historical Token Holders](/data-api/evm/token/holders/historical-token-holders) | Get token holder counts over time.      |
| [Token Holder Stats](/data-api/evm/token/holders/token-holder-stats)             | Get holder distribution and statistics. |

#### Discovery

| Endpoint                                                           | Description                              |
| :----------------------------------------------------------------- | :--------------------------------------- |
| [Filtered Tokens](/data-api/evm/token/discovery/filtered-tokens)   | Search tokens with advanced filters.     |
| [Token Categories](/data-api/evm/token/discovery/token-categories) | Get available token categories.          |
| [Top Gainers](/data-api/evm/token/discovery/top-gainers)           | Get tokens with the highest price gains. |
| [Top Losers](/data-api/evm/token/discovery/top-losers)             | Get tokens with the largest price drops. |

#### Signals

| Endpoint                                               | Description                             |
| :----------------------------------------------------- | :-------------------------------------- |
| [Snipers](/data-api/evm/token/signals/snipers)         | Detect sniper activity on a token.      |
| [Top Traders](/data-api/evm/token/signals/top-traders) | Get top profitable traders for a token. |

### EVM NFT API

Everything needed to build NFT experiences: metadata, ownership, transfers, sales, rarity, floor prices, and marketplace activity.

#### Collections

| Endpoint                                                                             | Description                           |
| :----------------------------------------------------------------------------------- | :------------------------------------ |
| [NFT Collections by Wallet](/data-api/evm/nft/collections/nft-collections-by-wallet) | Get NFT collections held by a wallet. |
| [NFTs by Collection](/data-api/evm/nft/collections/nfts-by-collection)               | Get all NFTs in a collection.         |
| [NFTs by Wallet](/data-api/evm/nft/collections/nfts-by-wallet)                       | Get all NFTs owned by a wallet.       |

#### Metadata

| Endpoint                                                                            | Description                            |
| :---------------------------------------------------------------------------------- | :------------------------------------- |
| [NFT Metadata](/data-api/evm/nft/metadata/nft-metadata)                             | Get metadata for a specific NFT.       |
| [NFT Metadata (Batch)](/data-api/evm/nft/metadata/nft-metadata-batch)               | Get metadata for multiple NFTs.        |
| [Collection Metadata](/data-api/evm/nft/metadata/collection-metadata)               | Get collection-level metadata.         |
| [Collection Metadata (Batch)](/data-api/evm/nft/metadata/collection-metadata-batch) | Get metadata for multiple collections. |
| [Collection Stats](/data-api/evm/nft/metadata/collection-stats)                     | Get statistics for a collection.       |

#### Ownership

| Endpoint                                                             | Description                      |
| :------------------------------------------------------------------- | :------------------------------- |
| [Owners by Contract](/data-api/evm/nft/ownership/owners-by-contract) | List all owners of a collection. |
| [Owners by Token ID](/data-api/evm/nft/ownership/owners-by-token-id) | Get owner(s) of a specific NFT.  |

#### Prices

| Endpoint                                                                  | Description                           |
| :------------------------------------------------------------------------ | :------------------------------------ |
| [Collection Floor Price](/data-api/evm/nft/prices/collection-floor-price) | Current floor price for a collection. |
| [Floor Price by Token ID](/data-api/evm/nft/prices/floor)                 | Floor price for a specific token.     |
| [Historical Floor Price](/data-api/evm/nft/prices/historical-floor-price) | Floor price history for a collection. |
| [Sale Price by Contract](/data-api/evm/nft/prices/sale-price-by-contract) | Last sale prices for a collection.    |
| [Sale Price by Token ID](/data-api/evm/nft/prices/sale-price-by-token-id) | Last sale price for a specific NFT.   |

#### Trades

| Endpoint                                                          | Description                       |
| :---------------------------------------------------------------- | :-------------------------------- |
| [Collection Trades](/data-api/evm/nft/trades/collection-trades)   | Recent sales for a collection.    |
| [Trades by Token ID](/data-api/evm/nft/trades/trades-by-token-id) | Trade history for a specific NFT. |

#### Transfers

| Endpoint                                                                 | Description                          |
| :----------------------------------------------------------------------- | :----------------------------------- |
| [Collection Transfers](/data-api/evm/nft/transfers/collection-transfers) | Transfer history for a collection.   |
| [Token ID Transfers](/data-api/evm/nft/transfers/token-id-transfers)     | Transfer history for a specific NFT. |

#### Traits

| Endpoint                                                                                    | Description                            |
| :------------------------------------------------------------------------------------------ | :------------------------------------- |
| [NFTs by Traits](/data-api/evm/nft/traits/nfts-by-traits)                                   | Filter NFTs by trait values.           |
| [Traits by Collection](/data-api/evm/nft/traits/traits-by-collection)                       | Get all traits for a collection.       |
| [Traits by Collection (Paginated)](/data-api/evm/nft/traits/traits-by-collection-paginated) | Paginated trait data for a collection. |

#### Discovery

| Endpoint                                                             | Description                            |
| :------------------------------------------------------------------- | :------------------------------------- |
| [NFTs by Market Cap](/data-api/evm/nft/discovery/nfts-by-market-cap) | Top NFT collections by market cap.     |
| [NFTs by Volume](/data-api/evm/nft/discovery/nfts-by-volume)         | Top NFT collections by trading volume. |

#### Utilities

| Endpoint                                                               | Description                                |
| :--------------------------------------------------------------------- | :----------------------------------------- |
| [Resync NFT Metadata](/data-api/evm/nft/utilities/resync-nft-metadata) | Trigger a metadata refresh for an NFT.     |
| [Resync NFT Traits](/data-api/evm/nft/utilities/resync-nft-traits)     | Trigger a traits refresh for a collection. |

### EVM DeFi API

Track DeFi positions, balances, rewards, and protocol interactions with enriched, protocol-aware data.

| Endpoint                                                           | Description                            |
| :----------------------------------------------------------------- | :------------------------------------- |
| [Wallet Protocols](/data-api/evm/defi/wallet-protocols)            | Summary of protocols used by a wallet. |
| [Wallet Positions](/data-api/evm/defi/wallet-positions)            | Detailed positions per protocol.       |
| [Detailed Positions](/data-api/evm/defi/wallet-positions-detailed) | Enhanced position breakdown.           |

### EVM Price API

Dedicated APIs to fetch comprehensive historical and real-time token and NFT price data.

| Endpoint                                                                   | Description                                |
| :------------------------------------------------------------------------- | :----------------------------------------- |
| [Token Price](/data-api/evm/price/token-price)                             | Get real-time price for a token.           |
| [Token Prices (Batch)](/data-api/evm/price/token-prices-batch)             | Get prices for multiple tokens.            |
| [OHLC Candlesticks](/data-api/evm/price/ohlc)                              | Get historical OHLC data.                  |
| [Collection Floor Price](/data-api/evm/price/collection-floor-price)       | Current floor price for an NFT collection. |
| [Timeseries Floor Price](/data-api/evm/price/timeseries-floor-price)       | Historical floor price data.               |
| [Token ID Floor Price](/data-api/evm/price/token-id-floor-price)           | Floor price for a specific token ID.       |
| [Sale Prices by Collection](/data-api/evm/price/sale-prices-by-collection) | Sale prices for NFTs in a collection.      |
| [Sale Price by Token ID](/data-api/evm/price/sale-price-by-token-id)       | Last sale price for a specific NFT.        |

### EVM Blockchain API

Core block-level data, logs, and internal transactions for EVM chains.

| Endpoint                                                                                | Description                                 |
| :-------------------------------------------------------------------------------------- | :------------------------------------------ |
| [Address Transactions](/data-api/evm/blockchain/address-transactions)                   | Get transactions for an address.            |
| [Address Transactions (Decoded)](/data-api/evm/blockchain/address-transactions-decoded) | Get decoded transactions for an address.    |
| [Block by Hash](/data-api/evm/blockchain/block-by-hash)                                 | Retrieve a block by its hash.               |
| [Block by Date](/data-api/evm/blockchain/block-by-date)                                 | Retrieve the closest block to a given date. |
| [Latest Block](/data-api/evm/blockchain/latest-block)                                   | Get the latest block number.                |
| [Transaction by Hash](/data-api/evm/blockchain/transaction-by-hash)                     | Get a transaction by its hash.              |
| [Transaction by Hash (Decoded)](/data-api/evm/blockchain/transaction-by-hash-decoded)   | Get a decoded transaction by its hash.      |

### Solana API

#### Solana Wallet API

| Endpoint                                                 | Description                                   |
| :------------------------------------------------------- | :-------------------------------------------- |
| [Native Balance](/data-api/solana/wallet/native-balance) | Get the native SOL balance for a wallet.      |
| [Token Balances](/data-api/solana/wallet/token-balances) | Get SPL token balances for a wallet.          |
| [Wallet Swaps](/data-api/solana/wallet/wallet-swaps)     | Get swap transactions for a wallet.           |
| [Wallet Portfolio](/data-api/solana/wallet/portfolio)    | Get complete portfolio overview for a wallet. |
| [NFT Balances](/data-api/solana/wallet/nft-balances)     | Get NFT balances for a wallet.                |

#### Solana Token API

**Metadata & Scores**

| Endpoint                                                                | Description                             |
| :---------------------------------------------------------------------- | :-------------------------------------- |
| [Token Metadata](/data-api/solana/token/token-metadata)                 | Get metadata for an SPL token.          |
| [Token Metadata (Batch)](/data-api/solana/token/token-metadata-batch)   | Get metadata for multiple SPL tokens.   |
| [Token Score](/data-api/solana/token/token-score)                       | Get safety / quality score for a token. |
| [Token Score Timeseries](/data-api/solana/token/token-score-timeseries) | Historical token score data.            |

**Prices**

| Endpoint                                                                 | Description                             |
| :----------------------------------------------------------------------- | :-------------------------------------- |
| [Token Price](/data-api/solana/token/prices/token-price)                 | Get real-time price for a Solana token. |
| [Token Prices (Batch)](/data-api/solana/token/prices/token-prices-batch) | Get prices for multiple Solana tokens.  |
| [OHLC Candlesticks](/data-api/solana/token/prices/ohlc)                  | Get OHLC price data for a Solana token. |

**Pairs & Swaps**

| Endpoint                                                  | Description                       |
| :-------------------------------------------------------- | :-------------------------------- |
| [Token Pairs](/data-api/solana/token/pairs/token-pairs)   | Get DEX pairs for a Solana token. |
| [Pair Stats](/data-api/solana/token/pairs/pair-stats)     | Get stats for a specific pair.    |
| [Pair Swaps](/data-api/solana/token/pairs/pair-swaps)     | Get recent swaps for a pair.      |
| [Token Swaps](/data-api/solana/token/swaps/token-swaps)   | Get swap history for a token.     |
| [Wallet Swaps](/data-api/solana/token/swaps/wallet-swaps) | Get swap history for a wallet.    |

**Holders**

| Endpoint                                                                | Description                      |
| :---------------------------------------------------------------------- | :------------------------------- |
| [Top Holders](/data-api/solana/token/holders/top-holders)               | Get top holders of a token.      |
| [Historical Holders](/data-api/solana/token/holders/historical-holders) | Get holder counts over time.     |
| [Holder Metrics](/data-api/solana/token/holders/holder-metrics)         | Get holder distribution metrics. |

**Market Metrics**

| Endpoint                                                                                       | Description                        |
| :--------------------------------------------------------------------------------------------- | :--------------------------------- |
| [Token Analytics](/data-api/solana/token/market-metrics/token-analytics)                       | Get market analytics for a token.  |
| [Token Analytics (Batch)](/data-api/solana/token/market-metrics/token-analytics-batch)         | Get analytics for multiple tokens. |
| [Token Analytics Timeseries](/data-api/solana/token/market-metrics/token-analytics-timeseries) | Historical analytics data.         |

**Discovery**

| Endpoint                                                                                           | Description                                 |
| :------------------------------------------------------------------------------------------------- | :------------------------------------------ |
| [Token Search](/data-api/solana/token/search-and-discovery/token-search)                           | Search for Solana tokens by name or symbol. |
| [Filtered Tokens](/data-api/solana/token/search-and-discovery/filtered-tokens)                     | Search tokens with advanced filters.        |
| [Top Gainers](/data-api/solana/token/search-and-discovery/top-gainers)                             | Get tokens with the highest price gains.    |
| [Top Losers](/data-api/solana/token/search-and-discovery/top-losers)                               | Get tokens with the largest price drops.    |
| [Pump.fun New Tokens](/data-api/solana/token/search-and-discovery/pump-fun-new-tokens)             | Get newly created Pump.fun tokens.          |
| [Pump.fun Bonding Tokens](/data-api/solana/token/search-and-discovery/pump-fun-bonding-tokens)     | Get Pump.fun tokens in bonding phase.       |
| [Pump.fun Bonding Status](/data-api/solana/token/search-and-discovery/pump-fun-bonding-status)     | Get bonding status for a Pump.fun token.    |
| [Pump.fun Graduated Tokens](/data-api/solana/token/search-and-discovery/pump-fun-graduated-tokens) | Get graduated Pump.fun tokens.              |

**Signals**

| Endpoint                                                   | Description                               |
| :--------------------------------------------------------- | :---------------------------------------- |
| [Snipers](/data-api/solana/token/advanced-signals/snipers) | Detect sniper activity on a Solana token. |

#### Solana NFT API

| Endpoint                                          | Description                    |
| :------------------------------------------------ | :----------------------------- |
| [NFT Metadata](/data-api/solana/nft/nft-metadata) | Get metadata for a Solana NFT. |

#### Solana Price API

| Endpoint                                                          | Description                             |
| :---------------------------------------------------------------- | :-------------------------------------- |
| [Token Price](/data-api/solana/price/token-price)                 | Get real-time price for a Solana token. |
| [Token Prices (Batch)](/data-api/solana/price/token-prices-batch) | Get prices for multiple Solana tokens.  |
| [OHLC Candlesticks](/data-api/solana/price/ohlc)                  | Get OHLC price data for a Solana token. |

### Universal API

Cross-chain data covering token analytics, entity data, and market metrics.

#### Token API

| Endpoint                                                                                     | Description                             |
| :------------------------------------------------------------------------------------------- | :-------------------------------------- |
| [Token Analytics](/data-api/universal/token/analytics/token-analytics)                       | Get cross-chain analytics for a token.  |
| [Token Analytics (Multi)](/data-api/universal/token/analytics/token-analytics-multi)         | Get analytics for multiple tokens.      |
| [Token Analytics Timeseries](/data-api/universal/token/analytics/token-analytics-timeseries) | Historical cross-chain analytics.       |
| [Token Score](/data-api/universal/token/score/token-score)                                   | Get cross-chain safety / quality score. |
| [Token Score Timeseries](/data-api/universal/token/score/token-score-timeseries)             | Historical token score data.            |
| [Token Search](/data-api/universal/token/search/token-search)                                | Search tokens across all chains.        |
| [Filtered Tokens](/data-api/universal/token/filtered-tokens)                                 | Search tokens with advanced filters.    |
| [Trending Tokens](/data-api/universal/token/trending-tokens)                                 | Get currently trending tokens.          |
| [Top Gainers](/data-api/universal/token/top-gainers)                                         | Get top gaining tokens across chains.   |
| [Top Losers](/data-api/universal/token/top-losers)                                           | Get top losing tokens across chains.    |

#### Entity API

| Endpoint                                                                      | Description                                             |
| :---------------------------------------------------------------------------- | :------------------------------------------------------ |
| [Entity Search](/data-api/universal/entity/endpoints/entity-search)           | Search for known entities (exchanges, protocols, etc.). |
| [Entity by ID](/data-api/universal/entity/endpoints/entity-by-id)             | Get entity details by ID.                               |
| [Entity by Category](/data-api/universal/entity/endpoints/entity-by-category) | Get entities filtered by category.                      |
| [Entity Categories](/data-api/universal/entity/endpoints/entity-categories)   | List all entity categories.                             |

#### Trading Stats API

| Endpoint                                                                                                    | Description                             |
| :---------------------------------------------------------------------------------------------------------- | :-------------------------------------- |
| [Trading Stats](/data-api/universal/global/endpoints/trading-stats)                                         | Get global trading statistics.          |
| [Trading Stats by Category](/data-api/universal/global/endpoints/trading-stats-category)                    | Get trading stats filtered by category. |
| [Trading Stats Timeseries](/data-api/universal/global/endpoints/trading-stats-timeseries)                   | Historical global trading data.         |
| [Trading Stats Category Timeseries](/data-api/universal/global/endpoints/trading-stats-category-timeseries) | Historical trading data by category.    |

### Streams API

Real-time blockchain event streaming via webhooks. Create and manage streams that push decoded blockchain data to your backend.

#### Stream Management

| Endpoint                                                                    | Description                  |
| :-------------------------------------------------------------------------- | :--------------------------- |
| [Create Stream](/streams/api-reference/streams/create-streams)              | Create a new stream.         |
| [Get Streams](/streams/api-reference/streams/get-streams)                   | List all streams.            |
| [Get Stream by ID](/streams/api-reference/streams/get-stream-by-id)         | Get a specific stream.       |
| [Update Stream](/streams/api-reference/streams/update-stream)               | Update stream configuration. |
| [Update Stream Status](/streams/api-reference/streams/update-stream-status) | Pause or resume a stream.    |
| [Delete Stream](/streams/api-reference/streams/delete-stream)               | Delete a stream.             |
| [Duplicate Stream](/streams/api-reference/streams/duplicate-stream)         | Clone an existing stream.    |

#### Address Management

| Endpoint                                                                    | Description                      |
| :-------------------------------------------------------------------------- | :------------------------------- |
| [Add Address](/streams/api-reference/streams/add-address-to-stream)         | Add an address to a stream.      |
| [Get Addresses](/streams/api-reference/streams/get-addresses-by-stream)     | List addresses on a stream.      |
| [Replace Address](/streams/api-reference/streams/replace-address-on-stream) | Replace an address on a stream.  |
| [Delete Address](/streams/api-reference/streams/delete-address-from-stream) | Remove an address from a stream. |

#### History & Replay

| Endpoint                                                        | Description                       |
| :-------------------------------------------------------------- | :-------------------------------- |
| [Get History](/streams/api-reference/history/get-history)       | Get webhook delivery history.     |
| [Get Logs](/streams/api-reference/history/get-logs)             | Get stream processing logs.       |
| [Replay History](/streams/api-reference/history/replay-history) | Replay missed webhook deliveries. |

#### Project Settings

| Endpoint                                                                    | Description                   |
| :-------------------------------------------------------------------------- | :---------------------------- |
| [Get Project Settings](/streams/api-reference/project/get-project-settings) | Get current project settings. |
| [Set Project Settings](/streams/api-reference/project/set-project-settings) | Update project settings.      |

#### Statistics

| Endpoint                                                                | Description                           |
| :---------------------------------------------------------------------- | :------------------------------------ |
| [Get Stats](/streams/api-reference/stats/get-stats)                     | Get global stream statistics.         |
| [Get Stats by Stream](/streams/api-reference/stats/get-stats-by-stream) | Get statistics for a specific stream. |

#### Webhook Data

| Endpoint                                                                                       | Description                               |
| :--------------------------------------------------------------------------------------------- | :---------------------------------------- |
| [Get Webhook Data by Block](/streams/api-reference/streams/get-webhook-data-by-block-number)   | Get webhook payload for a specific block. |
| [Send Webhook Data by Block](/streams/api-reference/streams/send-webhook-data-by-block-number) | Manually trigger webhook for a block.     |

### Cortex API

AI-powered blockchain data query engine.

| Endpoint                          | Description                                   |
| :-------------------------------- | :-------------------------------------------- |
| [Chat](/data-api/cortex-api/chat) | Query blockchain data using natural language. |
