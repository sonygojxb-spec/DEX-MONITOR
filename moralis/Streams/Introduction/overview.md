> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Streams

> Real-time blockchain webhooks across EVM, Bitcoin, and Solana — with guaranteed delivery and flexible filtering.

## Overview

Moralis **Streams** lets you receive **real-time blockchain events** directly in your backend via webhooks.

Instead of polling APIs or indexing chains yourself, Streams pushes on-chain activity to you the moment it happens — based on rules you define.

Streams is available on **EVM**, **Bitcoin**, and **Solana**.

***

## What Is Moralis Streams?

Moralis Streams allows you to **listen to blockchain activity in real time**. The product model is the same on every chain — define a stream, set filters, receive webhooks — but each chain exposes activity in its own native shape.

What you can listen to depends on the chain:

<Tabs>
  <Tab title="EVM">
    * Wallet activity (transfers, swaps, contract interactions)
    * Contract events via ABI decoding
    * ERC-20 / ERC-721 / ERC-1155 transfers and approvals (decoded for free)
    * Native and internal transactions
    * Custom on-chain conditions using [advanced filters](/streams/streams-concepts/advanced-options)
    * Read-only contract calls at match time using [Triggers](/streams/streams-concepts/triggers)

    See [EVM Streams](/streams/evm-streams) for details.
  </Tab>

  <Tab title="Bitcoin">
    * Inbound transfers to watched addresses (P2PKH, P2SH, Bech32)
    * HD wallet monitoring via xpub — Moralis derives addresses automatically
    * Two-phase delivery for every matched transaction (`confirmed: false` at first block inclusion, then `confirmed: true` once the block is reorg-safe)
    * Firehose mode (`allAddresses`) to receive every Bitcoin transaction

    See [Bitcoin Streams](/streams/bitcoin-streams) for details.
  </Tab>

  <Tab title="Solana">
    * Wallet activity matched against `accountKeys`
    * Program activity (e.g. SPL Token Program) via `programIds`
    * SPL token transfers via `mintAddresses`
    * Pre / post token balances for instant delta calculation
    * Inner instructions for Cross-Program Invocations (CPIs)
    * Firehose mode (`allAddresses`) to receive every Solana transaction

    See [Solana Streams](/streams/solana-streams) for details.
  </Tab>
</Tabs>

When a matching event occurs, Moralis delivers a **webhook** to your server with a structured data payload.

***

## How Streams Works

At a high level:

1. A new block is produced on-chain (or a slot, on Solana)
2. Moralis processes and evaluates the block
3. Your stream rules are applied
4. Matching events are detected
5. A webhook is delivered to your endpoint

All delivery is handled by Moralis — no nodes, polling, or infrastructure required.

***

## Common Use Cases

Streams is commonly used for:

* **Real-time wallet notifications** (send, receive, swap, stake, burn)
* **Asset monitoring** (token or NFT movement, price-sensitive events)
* **Exchange & custody flows** (deposit detection, hot/cold wallet surveillance)
* **Games & apps** (in-game actions, state changes, achievements)
* **Token sales & launches** (participation tracking, contribution thresholds)
* **Protocol monitoring** (liquidity events, contract / program interactions)
* **AI agents** that react to on-chain events as they happen

***

## Working With Webhooks

Streams delivers events via **HTTP webhooks**:

* Webhooks are sent using `POST` requests
* Payloads include decoded, structured event data ([EVM](/streams/webhooks/webhook-payloads), [Bitcoin](/streams/bitcoin-streams), [Solana](/streams/solana-streams))
* Delivery is retried automatically on failure
* Events can be replayed manually if needed

To ensure correctness, Moralis sends a **mandatory test webhook** whenever a stream is created or updated.

***

## Reliability & Guarantees

Streams is built for production workloads:

* Guaranteed webhook delivery with retries
* Automatic backoff if your service is unavailable
* Manual replay support
* Spam detection and filtering (EVM only)
* Secure webhook signing on every chain

***

## When to Use Streams

Use Streams if you need:

* Real-time blockchain events
* Push-based architecture
* Low-latency notifications
* Reliable delivery without running infrastructure

If you only need historical data, use the [**Data APIs**](/data-api/overview) instead.

***

## Get Started

* **Quickstart**
* **Stream Configuration**
* **Webhooks**
* **Tutorials**

***

## Streams API Overview Video

<iframe src="https://www.youtube.com/embed/k_hk9Pchjc8" title="Monitor Onchain Events" width="100%" height="400" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
