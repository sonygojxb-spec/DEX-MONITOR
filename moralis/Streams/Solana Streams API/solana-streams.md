> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Solana Streams

> Stream real-time Solana transaction data directly to your application with webhooks, no node infrastructure, no polling, no missed slots.

## Overview

**Solana Streams** extends Moralis Streams to Solana mainnet, delivering real-time transaction data via webhooks. Moralis indexes Solana automatically and pushes structured payloads to your endpoint whenever transactions match your criteria.

If you've used Moralis Streams on EVM, the developer model is the same: define a stream, set filters, receive webhooks. The differences are in **what you filter on**, because Solana's transaction model is different from EVM's.

***

## Key Features

* **Real-time delivery:** webhooks arrive within seconds of a slot being produced
* **Flexible filtering:** match by address, program, SPL token mint, or stream every transaction on the network
* **Pre / post token balances:** every payload includes SPL balance snapshots so you can compute exact token deltas without replaying instructions
* **Inner instructions included:** trace nested behavior across Cross-Program Invocations (CPIs) directly from the payload
* **Automatic retries:** Moralis retries webhook delivery until it receives an HTTP 200 response

***

## How It Works

1. A new Solana slot is produced
2. Moralis evaluates every transaction in the resulting block against your registered filters
3. Matching transactions fire a webhook to your endpoint
4. Your service processes the payload, keyed on the transaction `signature`

***

## Available Filters

You can combine filters within a stream to narrow down to exactly the activity you care about.

| Filter          | What it does                                                                                      | EVM analog                                 |
| --------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `addresses`     | Match transactions where any `accountKey` in the transaction matches one of the watched addresses | Filtering on `from` / `to` addresses       |
| `programIds`    | Filter to transactions invoking specific Solana programs (e.g., the SPL Token Program)            | Filtering on contract address being called |
| `mintAddresses` | Filter to transactions involving specific SPL tokens, matched via `pre` / `postTokenBalances`     | Filtering on ERC-20 contract address       |
| `allAddresses`  | Receive every transaction on the network (firehose mode, no matching)                             | Same on EVM                                |

***

## How Solana Differs From EVM

Most developers come to Solana with an EVM mental model. The concepts below bridge the two so you can pick the right filter and parse the payload correctly.

### Account keys vs. from/to

On EVM, a transaction has a `from` and (usually) a single `to`. On Solana, a transaction lists **all accounts it touches** in `accountKeys` - signers, recipients, programs, and any account read or written. The `addresses` filter matches against this full list, so a single Solana transaction can match multiple watched addresses.

### Programs vs. smart contracts

Solana **programs** are the executable code on-chain - the equivalent of EVM smart contracts. Each program has a `programId` (an address). The most common one developers will care about is the **SPL Token Program** (`TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA`), which handles all standard token transfers - similar to how the ERC-20 standard governs token behavior on EVM, except it's a single shared program rather than per-token contracts.

### Mint addresses vs. token contracts

On EVM, every ERC-20 token is its own contract; the contract address **is** the token. On Solana, all SPL tokens are managed by the same Token Program, and each token is identified by its **mint address** (the account that defines that token's supply and metadata). To watch transfers of a specific Solana token, filter by its `mintAddress`.

### Slots, blocks, and signatures

* **Slot** - Solana's time unit. Most slots produce a block; some are skipped.
* **Block** - what you'd expect, with a `blockHash` and `blockTime`.
* **Signature** - Solana's transaction ID is its first signature (base58-encoded), not a hash. This is what you use to look up a transaction.

### Inner instructions

A Solana transaction contains top-level **instructions**, and each instruction can trigger **inner instructions** when one program calls another (Cross-Program Invocations, or CPIs). Conceptually similar to internal calls in EVM. The webhook payload includes both, so you can trace nested behavior.

### Pre / post token balances

Every Solana transaction webhook includes `preTokenBalances` and `postTokenBalances` - snapshots of SPL token balances for the affected accounts before and after the transaction. This makes it trivial to compute exact token deltas without replaying the instruction logic.

***

## Webhook Payload

Each Solana webhook payload contains block metadata, stream identifiers, and a list of matched transactions.

```json theme={null}
{
  "block": {
    "slot": "410060994",
    "blockHash": "7xJ9Km3V...",
    "blockHeight": "389230112",
    "blockTime": 1743436800,
    "parentSlot": "410060993",
    "previousBlockHash": "9aB2cD4e..."
  },
  "chainId": "solana_mainnet",
  "network": "mainnet",
  "retries": 0,
  "streamId": "3f6684f3-2ba4-44d7-af0e-26ee70cab245",
  "tag": "my-solana-stream",
  "confirmed": false,
  "transactions": [
    {
      "signature": "5KtP...signature_base58",
      "slot": "410060994",
      "blockTime": 1743436800,
      "fee": "5000",
      "err": null,
      "accountKeys": [
        "GoSBxCH19sMnZVEifsXeeMdEfkTv6Zh6MWvQFQF3e5m7",
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "11111111111111111111111111111111"
      ],
      "instructions": [],
      "innerInstructions": [],
      "preTokenBalances": [],
      "postTokenBalances": []
    }
  ]
}
```

The fields you'll reach for first:

* `signature` - transaction id, base58-encoded
* `accountKeys` - every account the transaction touches
* `instructions[].programId` - which programs were invoked
* `preTokenBalances` / `postTokenBalances` - SPL balance snapshots for delta calculation

***

## Common Use Cases

* **Wallet activity notifications** - alert users on inbound and outbound activity for a Solana address
* **DEX / DeFi position monitoring** - track interactions with specific protocols by `programId`
* **SPL token transfer tracking** - airdrops, payments, and compliance flows filtered by `mintAddress`
* **Bot monitoring & MEV detection** - watch high-frequency program activity in real time
* **AI agents** - react to on-chain events as they happen

If you've built on Streams for EVM, you can stand up a Solana equivalent in minutes. The developer model is identical - only the filters differ.

***

## Setup Checklist

1. Generate an API key from [admin.moralis.com](https://admin.moralis.com)
2. Deploy a publicly accessible HTTPS webhook endpoint
3. Create the stream via `PUT /streams/solana`
4. Register the addresses, program IDs, or mint addresses you want to watch
5. Implement the verification handler — respond to the empty-body test `POST` with HTTP `200`
6. Build dedupe logic keyed on `signature`
7. Always return HTTP `200` from your handler, even when your own processing errors — Moralis retries on non-200 responses

***

## Roadmap

More Solana-specific filters and decoded payload options are on the way. If you need a specific protocol or filter prioritized, [reach out to the team](https://moralis.com/contact-sales).
