> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Advanced Options

> Configure advanced Streams options to control which transactions, logs, and events are included in webhook payloads.

<Note>
  Advanced options are an **EVM-only** feature. Bitcoin and Solana streams do not support these settings — see the [Bitcoin Streams](/streams/bitcoin-streams) and [Solana Streams](/streams/solana-streams) pages for their chain-native configuration.
</Note>

## Overview

Streams provides several advanced configuration options that allow you to **fine-tune which on-chain data is included in your webhook payloads**.

These options control:

* Which transaction types are included
* Whether contract logs and internal transactions are captured
* How specific events are filtered at a granular level

Used correctly, they help reduce noise while ensuring you receive all relevant data.

***

## Global Stream Options

These options apply at the **stream level** and affect the overall webhook payload.

***

### Include Contract Logs

```javascript theme={null}
includeContractLogs: true
```

When enabled:

* All contract logs are included in webhook payloads
* Required when monitoring **specific contracts**
* Useful when monitoring wallets that interact with contracts

If you are only monitoring wallet activity, this can be disabled unless contract interaction details are required.

***

### Include Internal Transactions

```javascript theme={null}
includeInternalTxs: true
```

When enabled:

* Includes internal transactions (contract-to-contract calls)
* Useful for tracing value movement inside smart contracts
* Particularly relevant for DeFi protocols and complex contract interactions

***

### Include Native Transactions

```javascript theme={null}
includeNativeTxs: true
```

When enabled:

* Includes native currency transfers (e.g. ETH, MATIC)
* Useful for tracking wallet balance changes or native payments

***

### Include All Transaction Logs

```javascript theme={null}
includeAllTxLogs: true
```

When enabled:

* Includes **all logs related to a transaction** if *any* log or transaction matches your stream configuration
* Expands the webhook payload to include full transaction context

**Requirements:**

* Must be used together with either:
  * `includeNativeTxs`, or
  * `includeContractLogs`

**Plan availability:**\
Available on **Pro plans and higher**.

***

## Advanced Options (Per-Event Configuration)

The `advancedOptions` field allows you to define **event-specific rules** that override or refine the global stream configuration.

Each entry targets a specific event signature and optionally applies filters.

***

### Advanced Option Structure

```javascript theme={null}
{
  "topic0": "string",
  "filter": { },
  "includeNativeTxs": boolean
}
```

***

### Fields Explained

#### `topic0`

The event signature to listen for (e.g. `Transfer(address,address,uint256)`).

* Required
* Determines which decoded event the option applies to

***

#### `filter`

A filter expression applied **only to this event**.

* Uses the same filter syntax described in **Filters**
* Allows precise inclusion logic per event

***

#### `includeNativeTxs`

Controls whether native transactions should be included **alongside this specific event**.

***

## Example: Filtered ERC-20 Transfers

```javascript theme={null}
{
  "topic0": "Transfer(address,address,uint256)",
  "filter": {
    "and": [
      { "eq": ["from", "0x283af0b28c62c092c9727f1ee09c02ca627eb7f5"] },
      { "gt": ["amount", "100000000000000000000"] }
    ]
  },
  "includeNativeTxs": false
}
```

This configuration:

* Listens only to ERC-20 `Transfer` events
* Filters transfers from a specific address
* Requires the transferred amount to exceed a threshold
* Excludes native transactions

<Info>
  Amounts must be expressed in the token’s base units (e.g. wei).
</Info>

***

## When to Use Advanced Options

Advanced options are useful when you want to:

* Apply **different rules per event type**
* Reduce webhook payload size
* Filter high-value or high-signal events
* Track contract activity with precision

For simpler use cases, global stream options are usually sufficient.

***

## Best Practices

* Start with global options, then refine with `advancedOptions`
* Avoid overlapping filters that can be hard to reason about
* Keep filters simple where possible
* Test changes in a non-production stream first

***

## Summary

* Global options control overall stream behaviour
* `advancedOptions` enable per-event customization
* Filters and advanced options work together
* Proper configuration reduces noise and improves reliability
