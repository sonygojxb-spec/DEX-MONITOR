> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Data API

> The universal multichain Data API provides a single, consistent interface for accessing blockchain data across 30+ supported chains, including Ethereum, Solana, Bitcoin, Base, Binance Smart Chain, and more. It standardizes complex on-chain data into clean, developer-friendly formats.

### How it's structured

The Data API is made up of **four core components**, designed to balance **cross-chain consistency** with **chain-specific depth**:

#### Universal API

Our [Universal API](/data-api/universal/overview) supports cross-chain endpoints that work across **EVM, Solana, and Bitcoin**, using unified schemas wherever possible. Ideal for applications that need to support multiple chains without maintaining separate integrations.

#### EVM API

The [EVM API](/data-api/evm/overview) offers deep, EVM-specific APIs covering Ethereum and EVM-compatible chains, exposing rich transaction, token, NFT, DeFi, and contract-level data.

#### Solana API

Our [Solana API](/data-api/solana/overview) provides parsed, high-performance access to Solana transactions, programs, token accounts, and NFTs, designed around Solana’s unique architecture.

#### Bitcoin API

The [Bitcoin API](/data-api/bitcoin/overview) brings full Bitcoin coverage — raw blocks and transactions, BTC market data, address activity, and balances — through the same Universal endpoints used for EVM and Solana. Pass `bitcoin` as the chain, with native xpub support across every wallet endpoint.

### Explore Data APIs

<Columns cols={3}>
  <Card title="Wallet API" icon="wallet" href="/data-api/evm/wallet/overview">
    Wallet history, transfers balances, tokens and PnL.
  </Card>

  <Card title="Token API" icon="hexagon-plus" href="/data-api/evm/token/overview">
    Token search, balances, transfers, holders and swaps.
  </Card>

  <Card title="NFT API" icon="shield-cat" href="/data-api/evm/nft/overview">
    Metadata, floor prices, transfers and ownership.
  </Card>

  <Card title="Price API" icon="chart-candlestick" href="/data-api/evm/price/overview">
    Real-time crypto prices, OHLC, trading volume.
  </Card>

  <Card title="DeFi API" icon="chart-line-up" href="/data-api/evm/defi/overview">
    DeFi positions, liquidity, reserves and token pairs.
  </Card>

  <Card title="Blockchain API" icon="cubes" href="/data-api/evm/blockchain/overview">
    Raw blocks, transactions, internal transactions and logs.
  </Card>
</Columns>

### Types of use cases

* Building wallets and portfolio trackers
* Powering Web3 dashboards and analytics tools
* Supporting multi-chain dApps from a single backend
* Tracking wallet activity, balances, and history
* Token discovery, monitoring, and market analysis
* NFT marketplaces and NFT analytics platforms
* DeFi apps showing positions, liquidity, and protocol data
* Backend services that need low-latency blockchain reads

### Key features

* **Low-latency APIs** optimized for production workloads
* **Unified schemas** across EVM, Solana, and Bitcoin where possible
* **Decoded and enriched data** (tokens, NFTs, prices, metadata)
* **Multi-chain support** across 30+ blockchains
* **High throughput & reliability** at scale
* **Consistent developer experience** across chains
* **Enterprise-grade infrastructure**, SLAs, and security
* No RPC management or custom indexer maintenance

### For which teams

* **Product teams** building wallets, dashboards, and user-facing apps
* **Backend engineers** who need reliable blockchain data without infra overhead
* **Frontend teams** consuming clean, predictable APIs
* **Analytics teams** accessing structured on-chain data
* **Startups and enterprises** scaling multi-chain applications

***

## Data API Overview Video

<iframe src="https://www.youtube.com/embed/O8PXFkN71oo" title="Moralis Data API Overview – Fetch Onchain Data at Scale" width="100%" height="400" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
