> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Onchain Skills

> Give your AI agent the ability to query blockchain data using Moralis APIs. Works with Claude Code, Cursor, Windsurf, GitHub Copilot, Cline, Codex, Gemini, and more.

<Frame>
  <img src="https://mintcdn.com/moralis/oDmu2DlHpqHBO5U7/images/onchain-skills-install.png?fit=max&auto=format&n=oDmu2DlHpqHBO5U7&q=85&s=841f5073bae8f45e67c86f9ad5280f5e" alt="Installing Moralis Onchain Skills via npx skills add novnski/onchain-skills" width="738" height="420" data-path="images/onchain-skills-install.png" />
</Frame>

## What are Onchain Skills?

Onchain Skills is an open-source package that lets AI agents call the [Moralis API](https://admin.moralis.com/register) directly — giving them the ability to query blockchain data from 40+ EVM chains and Solana in real time.

It works with any agent that supports the [Agent Skills](https://skills.sh/) standard, including **Claude Code, Cursor, Windsurf, GitHub Copilot, Cline, Codex, Gemini**, and 18+ others.

<iframe width="100%" height="400" src="https://www.youtube.com/embed/hq-SlxYji4w" title="Build Web3 Apps With AI Using Real Onchain Data | Moralis Onchain Skills" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />

***

## Quick Start

### 1. Install the Skills

```bash theme={null}
npx skills add novnski/onchain-skills
```

### 2. Set Your API Key

Get your key from [admin.moralis.com](https://admin.moralis.com/register), then add it to a `.env` file in your project root:

```bash theme={null}
echo "MORALIS_API_KEY=your_key_here" >> .env
```

That's it — your AI agent can now query blockchain data through Moralis.

***

## Skills Overview

Onchain Skills includes three skills:

| Skill                   | Description                                    | Endpoints |
| ----------------------- | ---------------------------------------------- | --------- |
| **moralis-data-api**    | EVM + Solana blockchain data                   | 136       |
| **moralis-streams-api** | Real-time event monitoring with webhooks       | 20        |
| **learn-moralis**       | Routing, FAQ, pricing, and capability guidance | —         |

### moralis-data-api

Unified skill for all blockchain data queries. Auto-detects EVM vs Solana from address format. For EVM addresses without a specified chain, defaults to Ethereum.

**136 endpoints** (102 EVM + 34 Solana) across these categories:

* **Wallet** (17) — balances, tokens, NFTs, history, profitability, net worth
* **Token** (22) — prices, metadata, pairs, DEX swaps, analytics, security scores, snipers
* **NFT** (22) — metadata, transfers, traits, rarity, floor prices, trades
* **DeFi** (3) — protocol positions, liquidity, exposure
* **Entity** (2) — labeled addresses (exchanges, funds, whales)
* **Price** (4) — OHLCV, token prices, pair prices
* **Blockchain** (5) — blocks, transactions, date-to-block
* **Discovery** (13) — trending tokens, market movers, top gainers/losers
* **Other** (14) — address resolution, token search, bonding, candlesticks, graduated tokens
* **Solana** (34) — native Solana endpoints + EVM endpoints with Solana support

**Example prompts:**

```
/moralis-data-api Get the balance of 0x1234...

/moralis-data-api Get the balance of 0x1234... on Polygon

/moralis-data-api Get the balance of Solana wallet ABC123...
```

### moralis-streams-api

Real-time blockchain event monitoring with webhooks. **20 endpoints** for creating, managing, and monitoring streams.

**Stream types:** `tx`, `log`, `erc20transfer`, `erc20approval`, `nfttransfer`, `internalTx`

**Example prompts:**

```
/moralis-streams-api Create a stream to monitor all ERC20 transfers on Ethereum

/moralis-streams-api Pause the stream with ID abc123
```

### learn-moralis

Knowledge-only skill for answering general questions about Moralis. Routes you to the correct technical skill after answering.

**Example prompts:**

```
/learn-moralis What is Moralis?

/learn-moralis Which Moralis API should I use for tracking wallet activity?
```

***

## Supported Chains

**EVM (40+):** Ethereum, Polygon, BNB Smart Chain, Arbitrum, Optimism, Avalanche, Fantom, Base, Sei, Monad, and more.

**Solana:** Mainnet and Devnet.

For the full list of supported chains, see [Supported Chains](/get-started/supported-chains).

***

## Architecture

* **Zero dependencies** — all API calls use curl
* **Works with 18+ agents** — any agent supporting the Agent Skills standard
* **Auto-detects chain** — determines EVM vs Solana from address format

***

## Resources

* [GitHub Repository](https://github.com/novnski/onchain-skills)
* [Get an API Key](https://admin.moralis.com/register)
* [Agent Skills Standard](https://skills.sh/)
* [Video Tutorial: Build Web3 Apps With AI Using Real Onchain Data](https://www.youtube.com/watch?v=hq-SlxYji4w)
