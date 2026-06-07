> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Filters

> Control which on-chain events trigger Streams webhooks. Filtering primitives differ by chain — addresses + ABI events on EVM, addresses + xpubs on Bitcoin, addresses + program IDs + mint addresses on Solana.

## Overview

Filters let you **control exactly which events trigger webhooks**. Events that don't match your filters are ignored and don't consume usage.

Each chain exposes its own filtering primitives, because each chain models on-chain activity differently.

***

## Filtering by Chain

<Tabs>
  <Tab title="EVM">
    EVM streams support the most filtering options:

    * **Addresses** — match transactions where `from` or `to` is a watched address
    * **Contract events (ABI + `topic0`)** — match specific decoded events emitted by smart contracts
    * **Advanced JSON filter expressions** — value comparisons, AND/OR logic, special stream variables (see below)
    * **`filterPossibleSpamAddresses`** — exclude events involving contracts flagged as spam

    Filters are evaluated **before** webhook delivery and require a **valid ABI** for the event being filtered when used with decoded event data.

    For ergonomic primitives (templates) in the Admin Panel, see [Create Your First Stream](/streams/quickstart/create-your-first-stream).
  </Tab>

  <Tab title="Bitcoin">
    Bitcoin streams filter on what's natural for the UTXO model:

    * **Addresses** — P2PKH (`1...`), P2SH (`3...`), or Bech32 (`bc1q...`)
    * **Xpubs** — attach an extended public key and Moralis derives addresses for HD wallets automatically
    * **`allAddresses`** — firehose mode that delivers every Bitcoin transaction

    Bitcoin Streams does not use the EVM JSON filter expression language. Address matching happens at the `vout` recipient level.

    <Warning>
      Bitcoin reliably detects **inbound** transfers to watched addresses. Input-side detection is limited because `vin` entries do not include populated `address` or `value` fields. See [Bitcoin Streams](/streams/bitcoin-streams).
    </Warning>
  </Tab>

  <Tab title="Solana">
    Solana streams support filters that map to Solana's transaction model:

    | Filter          | What it matches                                                                     |
    | --------------- | ----------------------------------------------------------------------------------- |
    | `addresses`     | Transactions where any `accountKey` matches a watched address                       |
    | `programIds`    | Transactions invoking specific Solana programs (e.g. SPL Token Program)             |
    | `mintAddresses` | Transactions involving specific SPL tokens, matched via `pre` / `postTokenBalances` |
    | `allAddresses`  | Firehose mode — receive every Solana transaction                                    |

    A single Solana transaction can match multiple watched addresses because `accountKeys` lists every account it touches.

    Solana Streams does not use the EVM JSON filter expression language.

    <Warning>
      Solana addresses are base58 and **case-sensitive**. Submit them in their original case — unlike EVM, lowercased addresses will not match.
    </Warning>
  </Tab>
</Tabs>

***

## Advanced JSON Filter Expressions (EVM)

<Note>
  The JSON filter expression system below is an **EVM-only** feature. It applies to decoded event data and requires a valid ABI for the event being filtered. Bitcoin and Solana streams use the chain-specific primitives above.
</Note>

### How filters work

Filters are defined as a **JSON expression** using logical operators and comparison rules.

* Filters apply to **decoded event data**
* Filters require a **valid ABI** for the event being filtered
* All conditions must resolve to `true` for the event to trigger a webhook

### Supported Operators

#### Logical operators

| Operator | Description                              | Notes                   | Example                                     |
| :------- | :--------------------------------------- | ----------------------- | ------------------------------------------- |
| `and`    | All nested conditions must match         | Need at least 2 filters | `{ "or" : [ {..filter1}, {...filter2} ]}`   |
| `or`     | At least one nested condition must match | Need at least 2 filters | `{ "and" : [ {..filter1}, {...filter2} ]}	` |

#### Comparison operators

| Operator | Description           | Notes               | Example                                |
| :------- | :-------------------- | :------------------ | -------------------------------------- |
| `eq`     | Equal to              |                     | `{ "eq": ["value", "1000"] }`          |
| `ne`     | Not equal to          |                     | `{ "ne": ["address", "0x...325"] }`    |
| `lt`     | Less than             | Numeric values only | `{ "lt": ["amount", "50"] }`           |
| `gt`     | Greater than          | Numeric values only | `{ "gt": ["price", "500000"] }`        |
| `lte`    | Less than or equal    | Numeric values only | `{ "lte": ["amount", "100"] }`         |
| `gte`    | Greater than or equal | Numeric values only | `{ "gte": ["amount", "100"] }`         |
| `in`     | Value exists in array | Array required      | `{ "in": ["name": ["alice", "bob"]]}`  |
| `nin`    | Value not in array    | Array required      | `{ "nin": ["name": ["bob", "alice"]]}` |

***

### Special Stream Variables (EVM)

Moralis provides special variables that can be used in filters to access stream-level metadata. These are EVM-specific.

| Variable                           | Description                               |
| :--------------------------------- | :---------------------------------------- |
| `moralis_streams_contract_address` | Contract emitting the event (lowercase)   |
| `moralis_streams_chain_id`         | Chain ID for the event                    |
| `moralis_streams_possibleSpam`     | Indicates if the event is flagged as spam |

#### Example: filter by contract address

```javascript theme={null}
{
  "eq": ["moralis_streams_contract_address", "0x0000000000000000000000000000000000000000"]
}
```

<Info>
  Note: contract addresses must be lowercase. EVM addresses are case-insensitive, so always `toLowerCase()` for comparison.
</Info>

***

### Filtering Possible Spam Events (EVM)

Some EVM contract addresses are associated with spam, phishing attempts, or other suspicious activity. Moralis identifies these and flags them with `possibleSpam = true`.

You can exclude these events entirely by enabling:

```javascript theme={null}
"filterPossibleSpamAddresses": true
```

When enabled:

* Events involving contracts flagged as possible spam are excluded
* No webhook is sent
* No usage is consumed

By default, `filterPossibleSpamAddresses` is set to `false`. Spam detection is currently EVM-only — see [Spam Detection](/streams/security-and-reliability/spam-detection).

***

### Example: Different Rules per Contract (EVM)

You can apply different thresholds depending on which contract emitted the event.

```javascript theme={null}
{
  "or": [
    {
      "and": [
        { "eq": ["moralis_streams_contract_address", "0x1"] },
        { "gte": ["value", 1000000000] }
      ]
    },
    {
      "and": [
        { "eq": ["moralis_streams_contract_address", "0x2"] },
        { "gte": ["value", 1000000000000000000000] }
      ]
    }
  ]
}
```

This is useful when monitoring multiple tokens with different decimals or value semantics.

***

### Example: Filtering by Value Range (EVM)

Filter transfers where the amount is between two values:

```javascript theme={null}
{
  "and": [
    { "gt": ["value", 5000000000] },
    { "lt": ["value", 50000000000] }
  ]
}
```

> Example assumes a token with 6 decimals (e.g. USDC).

***

### Example: Mint and Burn Detection (EVM)

A zero address indicates:

* **Mint** when used as `from`
* **Burn** when used as `to`

```javascript theme={null}
{
  "or": [
    {
      "and": [
        { "eq": ["from", "0x0000000000000000000000000000000000000000"] },
        { "gte": ["value", 10000000000] }
      ]
    },
    {
      "and": [
        { "eq": ["to", "0x0000000000000000000000000000000000000000"] },
        { "gte": ["value", 10000000000] }
      ]
    }
  ]
}
```

***

### Important Notes (EVM JSON filters)

* Filters require a **valid ABI** for the event being filtered
* Filters are evaluated **before webhook delivery**
* Invalid filters will prevent the stream from working
* Filters use **AND / OR logic only** (no implicit precedence)

***

## When to Use Filters

Use filters to:

* Reduce webhook volume
* Exclude spam or low-value events (EVM)
* Trigger alerts only for meaningful activity
* Apply different logic per contract or chain
