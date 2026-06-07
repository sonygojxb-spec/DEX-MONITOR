> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Triggers

> Run read-only smart contract calls as part of Streams processing and enrich webhook events with on-chain data in real time.

<Note>
  Triggers (read-only contract calls, ERC-20 / NFT transfer ABIs, `topic0`) are an **EVM-only** feature. Bitcoin and Solana streams use chain-native filtering instead — see [Filters](/streams/streams-concepts/filters).
</Note>

## Overview

Triggers allow you to **run read-only smart contract functions** as part of Streams processing and include the results directly in your webhook payloads.

This enables powerful real-time enrichment, such as:

* Fetching token balances during transfers
* Reading contract state when an event fires
* Attaching computed on-chain data to each streamed event

Triggers are evaluated **at stream time**, without requiring additional API calls from your backend.

***

## How Triggers Work

A trigger defines:

* **When** it should run (which event type)
* **Which contract function** to call
* **What inputs** to pass (static values or dynamic selectors)

When a matching event occurs:

1. Moralis executes the read-only contract call
2. The result is attached to the corresponding event object
3. The enriched event is delivered in the webhook

***

## Supported Trigger Types

Triggers can run against different parts of a webhook payload.

| Type            | Description                    |
| :-------------- | :----------------------------- |
| `tx`            | Run once per transaction       |
| `log`           | Run per decoded contract event |
| `erc20transfer` | Run per ERC-20 transfer        |
| `erc20approval` | Run per ERC-20 approval        |
| `nfttransfer`   | Run per NFT transfer           |

Additional trigger types may be added over time.

***

## Trigger Definition

A trigger is defined using the following structure:

```javascript theme={null}
interface Trigger {
  type: "tx" | "log" | "erc20transfer" | "erc20approval" | "nfttransfer";
  contractAddress: string;
  functionAbi: AbiItem;
  inputs?: (string | string[])[];
  topic0?: string;
  callFrom?: string;
}
```

***

## Trigger Fields Explained

### `type`

Specifies which event type the trigger runs against.

Example:

```javascript theme={null}
"type": "erc20transfer"
```

***

### `contractAddress`

The address of the contract containing the function to call.

* Must be a valid address **or a selector**
* Selectors allow dynamic resolution per event

***

### `functionAbi`

The ABI of a **single read-only function**.

Requirements:

* Must be a `view` or `pure` function
* Arrays of ABI items are not supported
* Selectors are **not** supported inside ABI definitions

You may rename output fields in the ABI to control how results appear in the webhook.

***

### `inputs` (optional)

Inputs passed to the function call.

* Order must match the function ABI
* Values can be static or selectors
* Structs are supported using arrays

Example:

```javascript theme={null}
"inputs": ["$from"]
```

***

### `topic0` (optional)

Restricts execution to a specific event signature.

* Only valid when `type` is `log`
* Requires the event ABI to be present in the stream
* Selectors are not allowed

***

### `callFrom` (optional)

Overrides `msg.sender` for the contract call.

* Must be a valid address or selector
* Useful for contracts with access-controlled view functions

***

## Selectors

Selectors dynamically reference values from the current webhook event.

* Begin with `$`
* Must be valid for the trigger type
* Validation ensures address selectors resolve to valid addresses

### Common selectors

| Selector    | Description                            |
| :---------- | :------------------------------------- |
| `$contract` | Contract address for the current event |
| `$from`     | Sender address                         |
| `$to`       | Recipient address                      |
| `$value`    | Transfer amount                        |

Invalid selectors will cause stream creation or updates to fail.

***

## Example: Fetch ERC-20 Balances During Transfers

This example enriches every ERC-20 transfer with the sender’s and receiver’s balances at the time of the transfer.

### Step 1: Define the ABI

```javascript theme={null}
const balanceOfSenderAbi = {
  name: "balanceOf",
  type: "function",
  stateMutability: "view",
  inputs: [{ name: "owner", type: "address" }],
  outputs: [{ name: "fromBalance", type: "uint256" }],
};
```

```javascript theme={null}
const balanceOfReceiverAbi = {
  name: "balanceOf",
  type: "function",
  stateMutability: "view",
  inputs: [{ name: "owner", type: "address" }],
  outputs: [{ name: "toBalance", type: "uint256" }],
};
```

***

### Step 2: Create Triggers

```javascript theme={null}
const triggers = [
  {
    type: "erc20transfer",
    contractAddress: "$contract",
    functionAbi: balanceOfSenderAbi,
    inputs: ["$from"],
  },
  {
    type: "erc20transfer",
    contractAddress: "$contract",
    functionAbi: balanceOfReceiverAbi,
    inputs: ["$to"],
  },
];
```

***

### Step 3: Resulting Webhook Enrichment

Each ERC-20 transfer will include trigger results:

```javascript theme={null}
"triggers": [
  { "name": "fromBalance", "value": "6967063534600021400000" },
  { "name": "toBalance", "value": "200000000000000000" }
]
```

Trigger results appear **in the same order** as defined.

***

## Error Handling

* Invalid triggers are rejected when creating or updating a stream
* Contract existence is not validated ahead of time
* If a contract call fails:
  * The webhook is still delivered
  * The trigger result includes an error message

This ensures Streams remain resilient under partial failures.

***

## Notes on Read-Only Functions

Triggers only support **read-only** contract calls:

* `stateMutability: view`
* `stateMutability: pure`

Functions that modify state or require gas are not supported.

***

## When to Use Triggers

Triggers are ideal when you want to:

* Enrich events with on-chain state
* Reduce API calls from your backend
* Attach contextual data at event time
* Keep webhook payloads self-contained
