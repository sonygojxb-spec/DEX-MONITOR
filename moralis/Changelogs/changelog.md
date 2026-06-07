> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Product updates

> New releases and improvements

<Update label="June 4, 2026" tags={["Deprecation"]}>
  ## Cortex API and legacy Data API Endpoints Removed

  As [announced on May 5](#cortex-api-and-legacy-data-api-endpoints-sunsetting), the following endpoints and APIs have now been **removed** as of June 4, 2026. Requests to these endpoints will return an error. If you are still calling any of them, migrate to the replacements below.

  **Cortex API:**

  * `POST /chat` — migrate to [Onchain Skills](/data-api/onchain-skills/overview), which replaces Cortex as our AI interface for Moralis data.

  **Discovery endpoints (`/discovery/*`):**

  * `POST /discovery/tokens`
  * `GET /discovery/token` — migrate to the [Token Search API](/data-api/universal/token/search/token-search).
  * `GET /discovery/tokens/rising-liquidity`
  * `GET /discovery/tokens/buying-pressure`
  * `GET /discovery/tokens/solid-performers`
  * `GET /discovery/tokens/experienced-buyers`
  * `GET /discovery/tokens/risky-bets`
  * `GET /discovery/tokens/blue-chip`
  * `GET /discovery/tokens/top-gainers`
  * `GET /discovery/tokens/top-losers`
  * `GET /discovery/tokens/trending`

  **Volume endpoints (`/volume/*`):**

  * `GET /volume/chains`
  * `GET /volume/categories`
  * `GET /volume/timeseries`
  * `GET /volume/timeseries/{categoryId}`

  **Sniper endpoints (EVM and Solana):**

  * `GET /pairs/{address}/snipers` (EVM)
  * `GET /token/{network}/pairs/{pairAddress}/snipers` (Solana)

  **ERC20 endpoints (EVM):**

  * `GET /erc20/exchange/{exchangeName}/new`
  * `GET /erc20/exchange/{exchangeName}/bonding`
  * `GET /erc20/exchange/{exchangeName}/graduated`
  * `GET /erc20/{tokenAddress}/bondingStatus`
  * `GET /erc20/{address}/stats`
  * `GET /erc20/{token_address}/pairs/stats` — migrate to [`GET /tokens/{tokenAddress}/analytics`](/data-api/universal/token/analytics/token-analytics)
  * `GET /erc20/metadata/symbols` — migrate to [`GET /tokens/search`](/data-api/universal/token/search/token-search)

  **Market data endpoints (`/market-data/*`):**

  * `GET /market-data/erc20s/top-tokens`
  * `GET /market-data/erc20s/top-movers`
  * `GET /market-data/nfts/top-collections`
  * `GET /market-data/nfts/hottest-collections`
  * `GET /market-data/global/market-cap`
  * `GET /market-data/global/volume`

  If you need help identifying the right replacement for a removed endpoint, [reach out to the team](https://admin.moralis.com/) (via chat widget).
</Update>

<Update label="June 1, 2026" tags={["New Feature"]}>
  ## 11 New Solana DEXes

  We've expanded Solana DEX coverage with **11 newly indexed DEX programs**, powering token pairs, swaps, prices, OHLC, and other DEX-derived features across the Data API.

  **Newly supported:**

  * **BisonFi**
  * **HumidiFi**
  * **Phoenix**
  * **Manifest**
  * **Tessera V**
  * **SolFi**
  * **ZeroFi**
  * **GoonFi V1** (dormant) and **GoonFi V2** (active)
  * **Saber**
  * **PancakeSwap**

  For these protocols, swap data (and therefore prices) is available from **June 1, 2026** onwards. Full historical coverage is coming soon. All other Solana DEXes have full history.

  See the full list of program IDs on the [Supported DEXes](/data-api/data-features/integrations/supported-dexs#solana-dex-support) page.
</Update>

<Update label="June 1, 2026" tags={["Deprecation"]}>
  ## Sunsetting Zeta Chain RPC

  As of June 1, 2026, Moralis is sunsetting RPC node support for Zeta Chain. The Zetachain and Zetachain Testnet RPC endpoints are no longer available, and their documentation has been removed.

  If you rely on Zeta Chain RPC, please migrate to an alternative provider. All other supported chains are unaffected.
</Update>

<Update label="May 29, 2026" tags={["Deprecation"]}>
  ## Fantom Chain Sunsetting

  Fantom mainnet support is being removed across all Moralis APIs on **May 29, 2026**. Fantom Opera testnet has already been removed. The Fantom Opera network is winding down as a legacy chain, and we're retiring our integration in line with the broader ecosystem shift.

  **What's changing:**

  * **Data API** — wallet, token, NFT, DeFi, and price endpoints no longer return Fantom (`0xfa`) data. Requests passing `fantom` or chain id `0xfa` will return an error.
  * **RPC Nodes** — Fantom RPC node endpoints are no longer available, and their documentation has been removed.
  * **Streams** — existing Fantom streams will stop emitting webhook notifications and should be deleted from your workspace.
  * **Testnet** — Fantom Opera testnet was removed ahead of mainnet as part of this wind-down.

  **Why:** Fantom Opera has transitioned into a legacy chain with declining activity following the broader migration to Sonic. Maintaining a dedicated integration is no longer justified by usage, so we're consolidating support onto actively maintained networks.

  **What to do:**

  * Remove any `fantom` / `0xfa` references from your API requests, SDK calls, and stream configurations before May 29 to avoid errored responses.
  * If you still rely on Fantom data, migrate to an alternative provider, or move your workloads to one of the [supported chains](/data-api/supported-chains).

  All other supported chains are unaffected.
</Update>

<Update label="May 27, 2026" tags={["New Feature"]}>
  ## Bitcoin Data API

  Full Bitcoin coverage now lands on the Moralis Universal API — raw blocks and transactions, market prices with sparklines, address history and balances, plus native xpub tooling. Every endpoint is the same Universal endpoint EVM and Solana developers already use; just pass `bitcoin` as the chain.

  **What's new:**

  * **Raw data** — raw blocks and raw transactions for teams working directly with onchain data
  * **Market data** — current BTC price, full historical time series, and chart-ready price sparklines for chart UIs
  * **Address-level data** — transaction history and token balances for any Bitcoin address
  * [**Xpub tooling**](/data-api/bitcoin/utility/overview) — pass a Bitcoin address **or** an xpub to the wallet endpoints, plus a new [utility endpoint](/data-api/bitcoin/utility/addresses-from-xpub) to enumerate every derived address from a given xpub

  **Address or xpub inputs:** the wallet endpoints accept either a Bitcoin address or an xpub directly, so the API slots into whatever shape your wallet or backend already uses.

  ```bash theme={null}
  # Address input
  GET /v1/wallets/bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq/tokens?chains=bitcoin

  # Xpub input — same endpoint, derives addresses server-side
  GET /v1/wallets/{xpub}/tokens?chains=bitcoin
  ```

  This brings the full Bitcoin data lifecycle under one consistent surface — replacing the block explorer, price feed, custom indexer, xpub derivation library, and chart caching layer teams used to stitch together — with the same auth, SDKs, pricing, and rate limits as the rest of Moralis.

  **Use cases:** Bitcoin wallets, custody platforms, block explorers, BTC analytics, and multi-chain platforms extending their Bitcoin coverage.

  See the [Bitcoin Data API overview](/data-api/bitcoin/overview) for the full endpoint list and schemas, or start with the [Bitcoin Quickstart](/get-started/tutorials/data-api/bitcoin/bitcoin-quickstart).

  [Explore the Bitcoin Data API →](/data-api/bitcoin/overview)
</Update>

<Update label="May 26, 2026" tags={["New Feature"]}>
  ## Three New Solana DeFi Protocols

  Three top-tier Solana DeFi protocols are now supported through our existing DeFi endpoints, taking total Solana DeFi coverage to **10 protocols** - roughly 90% of Solana DeFi TVL, including all of the top protocols by TVL (Jupiter, Kamino, Sanctum, and Raydium).

  **Newly supported:**

  * **Jupiter Perpetual Exchange** - derivatives on the dominant Solana DEX aggregator (Jupiter Lend was already supported)
  * **Kamino Lend** - the second-largest protocol on Solana by TVL
  * **Sanctum** - validator liquid staking; the third-largest protocol on Solana by TVL

  These plug into the existing [Solana DeFi endpoints](/data-api/solana/defi/overview), so anyone already pulling Solana DeFi data picks them up automatically - no code changes required.

  **New utility endpoint:** `GET /v1/defi/protocols` returns the full list of supported DeFi protocols for a given chain, so you can query coverage programmatically and keep your integration in sync. See [DeFi Protocols](/data-api/data-features/integrations/defi-protocols).

  [Explore the Solana DeFi API →](/data-api/solana/defi/overview)
</Update>

<Update label="May 14, 2026" tags={["New Feature"]}>
  ## Mempool Notifications for Bitcoin Streams

  Bitcoin Streams now emit webhook notifications for **unconfirmed transactions** as soon as they hit the mempool — no need to wait for block inclusion.

  **What's new:**

  * **Pre-confirmation delivery** — matching transactions fire a webhook the moment they are broadcast to the mempool
  * **Same payload shape** as a confirmed-block webhook, with sentinel fields on the `block` object marking the delivery as mempool:
    * `block.height` → `"0"`
    * `block.hash` → `"mempool"`
    * `confirmed` → `false`
  * **`vin` and `vout` addresses both populated** in mempool payloads, so a watched address triggers a match whether it is sending or receiving
  * **Xpub-derived addresses fully supported**

  **Behavior to plan around:**

  * Each mempool transaction is delivered **at most once per stream**
  * The mempool delivery has **no follow-up** — the regular confirmed-block stream (`confirmed: false` then `confirmed: true`) handles in-block and reorg-safe deliveries for the same `txid`
  * Mempool transactions are **not guaranteed to confirm** — they can be replaced (RBF), evicted, or expire on low fee. Treat them as pending, not settled

  **Use cases:** show users a pending balance the instant a tx is broadcast, trigger UX flows on payment broadcast instead of confirmation, mempool monitoring, RBF detection, fee analytics, and MEV / arbitrage signals.

  No new endpoint, parameter, or schema. Existing Bitcoin streams pick this up automatically — branch on `block.hash === "mempool"` in your webhook handler to separate mempool events from confirmed-block events. See the [Mempool Notifications](/streams/bitcoin-streams#mempool-notifications) section for the full payload and handler patterns.

  [Explore Bitcoin Streams →](/streams/bitcoin-streams)
</Update>

<Update label="May 7, 2026" tags={["New Feature"]}>
  ## Bitcoin Streams

  Moralis Streams now extends to Bitcoin mainnet. Define a stream, attach the addresses or xpubs you want to watch, and receive real-time webhook deliveries within seconds of a block being mined - no node, no polling, no missed blocks.

  **What's new:**

  * **Bitcoin mainnet support** on the same Streams developer model used for EVM and Solana
  * **Dual-phase notifications** - matched transactions fire a webhook in the mempool (unconfirmed) and again on block confirmation, so you can mark deposits `pending` then `confirmed` from the same stream
  * **All address formats supported** - P2PKH (legacy `1...`), P2SH (SegWit-wrapped `3...`), and Bech32 native SegWit (`bc1q...`)
  * **Xpub support** - attach an extended public key and Moralis derives and monitors its addresses automatically, ideal for HD wallets
  * **Automatic retries** until your endpoint returns HTTP 200

  **Monitoring modes available at launch:**

  * `addresses` — watch specific Bitcoin addresses
  * `xpub` — derive and monitor addresses from an extended public key
  * `allAddresses` — firehose mode: receive every Bitcoin transaction

  **Use cases:** exchange deposit detection (mempool → confirmed lifecycle), cold wallet surveillance, mining pool payout tracking, and real-time treasury monitoring for corporate or DAO-held BTC.

  A few Bitcoin-specific behaviors to plan around: input `address` and `value` fields are not populated (inbound detection only), output values are BTC decimals rather than satoshis, and `isCoinbase` should be detected via heuristic. See the [Bitcoin Streams docs](/streams/bitcoin-streams) for the full payload structure and processing patterns.

  [Explore Bitcoin Streams →](/streams/bitcoin-streams)
</Update>

<Update label="May 5, 2026" tags={["New Feature"]}>
  ## Solana Streams

  Moralis Streams now extends to Solana mainnet. Define a stream, set filters, and receive real-time webhook deliveries the moment matching transactions land in a slot - no node, no polling, no missed slots.

  **What's new:**

  * **Solana mainnet support** on the same Streams developer model used for EVM
  * **Pre / post token balances** included in every payload, so you can compute exact SPL token deltas without replaying instructions
  * **Inner instructions included**, so you can trace nested behavior across Cross-Program Invocations (CPIs) directly from the payload
  * **Automatic retries** until your endpoint returns HTTP 200

  **Filters available at launch:**

  * `addresses` — match transactions where any `accountKey` in the transaction matches a watched address
  * `programIds` — filter to transactions invoking specific Solana programs (e.g., the SPL Token Program)
  * `mintAddresses` — filter to transactions involving specific SPL tokens, matched via `pre` / `postTokenBalances`
  * `allAddresses` — firehose mode: receive every Solana transaction

  **Use cases:** wallet activity notifications, DEX / DeFi position monitoring by `programId`, SPL token transfer tracking, bot and MEV monitoring, and AI agents reacting to on-chain events as they happen.

  If you've used Streams on EVM, the developer model is identical — only the filters differ.

  [Explore Solana Streams →](/streams/solana-streams)
</Update>

<Update label="May 5, 2026" tags={["Deprecation"]}>
  ## Cortex API and legacy Data API Endpoints Sunsetting

  The following endpoints and APIs are now deprecated and will be removed on **June 4, 2026** (30 days from today):

  **Cortex API:**

  * `POST /chat` — migrate to [Onchain Skills](/data-api/onchain-skills/overview), which replaces Cortex as our AI interface for Moralis data.

  **Discovery endpoints (`/discovery/*`):**

  * `POST /discovery/tokens`
  * `GET /discovery/token` — migrate to the [Token Search API](/data-api/universal/token/search/token-search).
  * `GET /discovery/tokens/rising-liquidity`
  * `GET /discovery/tokens/buying-pressure`
  * `GET /discovery/tokens/solid-performers`
  * `GET /discovery/tokens/experienced-buyers`
  * `GET /discovery/tokens/risky-bets`
  * `GET /discovery/tokens/blue-chip`
  * `GET /discovery/tokens/top-gainers`
  * `GET /discovery/tokens/top-losers`
  * `GET /discovery/tokens/trending`

  **Volume endpoints (`/volume/*`):**

  * `GET /volume/chains`
  * `GET /volume/categories`
  * `GET /volume/timeseries`
  * `GET /volume/timeseries/{categoryId}`

  **Sniper endpoints (EVM and Solana):**

  * `GET /pairs/{address}/snipers` (EVM)
  * `GET /token/{network}/pairs/{pairAddress}/snipers` (Solana)

  **ERC20 endpoints (EVM):**

  * `GET /erc20/exchange/{exchangeName}/new`
  * `GET /erc20/exchange/{exchangeName}/bonding`
  * `GET /erc20/exchange/{exchangeName}/graduated`
  * `GET /erc20/{tokenAddress}/bondingStatus`
  * `GET /erc20/{address}/stats`
  * `GET /erc20/{token_address}/pairs/stats` — migrate to [`GET /tokens/{tokenAddress}/analytics`](/data-api/universal/token/analytics/token-analytics)
  * `GET /erc20/metadata/symbols` — migrate to [`GET /tokens/search`](/data-api/universal/token/search/token-search)

  **Market data endpoints (`/market-data/*`):**

  * `GET /market-data/erc20s/top-tokens`
  * `GET /market-data/erc20s/top-movers`
  * `GET /market-data/nfts/top-collections`
  * `GET /market-data/nfts/hottest-collections`
  * `GET /market-data/global/market-cap`
  * `GET /market-data/global/volume`

  If you rely on any of these endpoints, please migrate before June 4, 2026. [Reach out to the team](https://admin.moralis.com/) (via chat widget) if you need help identifying replacements.
</Update>

<Update label="Apr 30, 2026" tags={["Deprecation"]}>
  ## Fantom Chain Sunsetting

  Fantom mainnet support will be removed across all Moralis APIs on **May 29, 2026**. Fantom Opera testnet has already been removed as of today. The Fantom Opera network is winding down as a legacy chain, and we're retiring our integration in line with the broader ecosystem shift.
</Update>

<Update label="April 29, 2026" tags={["New Feature"]}>
  ## DeFi API: Now on Solana

  The same three Universal DeFi API endpoints that returned EVM positions last week now return Solana positions too. No new endpoints, no schema changes - the existing calls now cover the most-used Solana protocols alongside EVM.

  **What's new:**

  * **Solana support** on the same Universal DeFi endpoints used for EVM
  * **7 of the most-used Solana protocols** supported at launch:
    * Jito
    * Save (formerly Solend)
    * Jupiter Lending
    * Raydium
    * Orca
    * Drift
    * Marinade
  * **Unified schema:** identical response shape across EVM and Solana - no client-side stitching
  * **Single call:** query EVM and Solana wallets through the same endpoints with the same filters

  **Main endpoints:**

  * [`getDefiSummary`](/data-api/solana/defi/wallet-protocols) — every protocol a wallet holds positions in, total USD value, and unclaimed rewards
  * [`getDefiPositionsSummary`](/data-api/solana/defi/wallet-positions) — all positions with token types, values, and reward tokens
  * [`getDefiPositionsByProtocol`](/data-api/solana/defi/wallet-positions-detailed) — detailed per-protocol breakdown with position-level detail

  **Usecases:** portfolio trackers, exchanges, tax tools, DeFi dashboards, and AI agents that need a unified DeFi position view across EVM and Solana in a single, consistent response.

  More Solana protocols are being added on a rolling basis. If you need a specific Solana protocol prioritized, [reach out to the team](https://moralis.com/contact-sales).

  [Explore the Solana DeFi API →](/data-api/solana/defi/overview)
</Update>

<Update label="April 22, 2026" tags={["Improvement"]}>
  ## DeFi API: 5,000+ Protocols, Now Multichain

  We've significantly expanded the DeFi API (EVM) with broader protocol coverage and simpler multichain queries in a single call.

  **What's new:**

  * **5,000+ DeFi protocols** supported, covering 96% of the entire EVM DeFi market
  * **Multichain queries:** fetch positions from a single chain, multiple chains, or all EVM chains in one API call
  * **Protocols include:** Uniswap V2/V3, Aave V2/V3, Lido, Curve, Compound, MakerDAO, Pendle, Convex, Yearn, GMX, Aerodrome, Velodrome, SushiSwap, PancakeSwap, Eigenlayer, Etherfi, Rocket Pool, Spark, Morpho, and thousands more

  **Main endpoints:**

  * [`getDefiSummary`](/data-api/evm/defi/wallet-protocols) — every protocol a wallet holds positions in, total USD value, and unclaimed rewards
  * [`getDefiPositionsSummary`](/data-api/evm/defi/wallet-positions) — all positions with token types, values, and reward tokens
  * [`getDefiPositionsByProtocol`](/data-api/evm/defi/wallet-positions-detailed) — detailed per-protocol breakdown with position-level detail

  **Usecases:** portfolio trackers, DeFi dashboards, tax and accounting tools, and risk monitoring. Anywhere you need a unified view of a wallet's DeFi exposure without wiring each protocol in manually.

  Solana DeFi support is coming soon.

  [Explore the DeFi API →](/data-api/evm/defi/overview)

  <iframe src="https://www.youtube.com/embed/yc-THd5xH5s" title="Moralis DeFi API Overview" width="100%" height="400" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
</Update>

<Update label="April 2, 2026" tags={["New Feature"]}>
  ## Wallet Insights

  We've launched the Wallet Insights endpoint - a single API call that returns a comprehensive behavioral profile for any EVM wallet address.

  Get wallet age, activity timelines, transaction counts, transfer breakdowns (native, ERC-20, NFT), swap volume, gas spend, net flow, unique counterparties, contracts created, and more - all in one response. Each metric is also available per-chain via the `includeChainBreakdown` array, so you can see exactly how a wallet behaves across different networks.

  [Explore Wallet Insights →](/data-api/evm/wallet/wallet-insights)
</Update>

<Update label="Feburary 4, 2026" tags={["New Feature"]}>
  ## Historical Token Scores

  We've added the ability to track Token Scores over time with a new Historical Token Score endpoint.

  The Historical Token Score endpoint lets you retrieve a token's score history across different timeframes, so you can see how a token's onchain quality has changed over time.

  [Explore Historical Token Scores →](/data-api/universal/token/score/token-score-timeseries)
</Update>

<Update label="December 16, 2025" tags={["New Feature"]}>
  ## Token Scores

  We've launched the Moralis Token Score - a unified 0–100 rating that summarizes a token's onchain quality in a single, easy-to-use metric.

  [Explore Token Scores →](/data-api/universal/token/score/token-score)
</Update>

<Update label="November 24, 2025" tags={["New Chains"]}>
  ## Monad EVM Live

  We've added Monad EVM support to both the Data APIs and the Streams API, giving you access to this next-generation, EVM-compatible Layer-1 that delivers 10,000 TPS, 0.4-second block times, 800 ms finality, and near-zero gas fees.
</Update>

<Update label="October 16, 2025" tags={["New Chains"]}>
  ## Sei EVM Live

  We’ve added Sei EVM support to both the Data APIs and the Streams API, expanding your access to this high-performance Layer 1 chain built for speed and scalability.
</Update>

<Update label="September 30, 2025" tags={["New Chains"]}>
  ## HyperEVM Live

  We've added HyperEVM mainnet to the Moralis Streams API. You can now listen to real-time blockchain activity on HyperEVM - perfect for notifications, indexing, and on-chain automation.
</Update>
