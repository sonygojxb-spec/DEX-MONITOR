> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Confirmation & Finality

> Understand how blockchain confirmations work, how Moralis defines finality, and how confirmed and unconfirmed webhooks should be handled.

### Overview

Blockchains are probabilistic systems. A transaction may appear in a block and later be removed due to a chain reorganization (re-org).

To handle this safely, Moralis Streams distinguishes between **unconfirmed** and **confirmed** events and delivers both to your backend.

This page explains **what confirmation and finality mean**, and how they are exposed through Streams.

***

### What Is Confirmation?

When a transaction is included in a newly mined block, it is considered **unconfirmed**.

At this stage:

* The block may still be replaced
* Transactions may be reordered or dropped
* State changes are *not final*

Streams delivers these events with:

```javascript theme={null}
"confirmed": false
```

This enables **low-latency, real-time reactions**.

See also:

* [**Webhook Delivery**](/streams/webhooks/webhook-delivery)
* [**Webhook Payload**](/streams/webhooks/webhook-payloads)

***

### What Is Finality?

A transaction becomes **confirmed** once enough blocks have been mined on top of it.

At this point:

* The risk of re-org is extremely low
* State can be safely persisted
* Balances and ownership can be finalized

Streams delivers a second webhook with:

```javascript theme={null}
"confirmed": true
```

Confirmation thresholds vary by chain. See [**Supported Chains**](/streams/supported-chains)**.**

***

### Finality by Chain

Each chain has its own finality model, which determines how long it takes for a `confirmed: true` webhook to arrive after the initial unconfirmed delivery:

<Tabs>
  <Tab title="EVM">
    EVM finality is **probabilistic** and varies per chain. Confirmation thresholds are expressed as a number of blocks that must be mined on top of the block containing the transaction. Ethereum and other EVM chains can experience reorgs up to a chain-specific depth, after which the transaction is treated as final.

    See [Supported Chains](/streams/supported-chains) for the per-chain confirmation block counts.
  </Tab>

  <Tab title="Bitcoin">
    Bitcoin finality is **proof-of-work based**. Once a transaction is included in a mined block, each subsequent block adds another confirmation. Streams sends up to three deliveries per matching transaction:

    * A **mempool** delivery when the transaction is first broadcast — `confirmed: false`, with sentinel `block.height: "0"` and `block.hash: "mempool"`. Delivered at most once and not guaranteed for every tx
    * `confirmed: false` when the transaction is first included in a block — the block is close to the chain tip and could still be reorged
    * `confirmed: true` once 2 additional blocks have been mined on top, at which point Moralis re-fetches the block and treats the transaction as reorg-safe

    Bitcoin reorgs follow the longest-valid-chain rule and become exponentially less likely with each additional confirmation. See [Supported Chains](/streams/supported-chains) for the threshold Streams uses, and [Mempool Notifications](/streams/bitcoin-streams#mempool-notifications) for the unconfirmed-delivery behavior.
  </Tab>

  <Tab title="Solana">
    Solana finality is **slot-based** and typically reached very quickly compared to other chains. The unconfirmed delivery is sent when the slot is produced; the confirmed delivery follows once the slot is finalized. Reorgs are rare and bounded by the network's finality model.

    See [Supported Chains](/streams/supported-chains) for the exact threshold Streams uses.
  </Tab>
</Tabs>

***

### Why Streams Sends Two Webhooks

Streams intentionally sends **both states** so you can:

* React instantly (unconfirmed)
* Persist safely (confirmed)

This avoids the need to:

* Poll block explorers
* Manually track confirmations
* Reconcile state after re-orgs

For how Streams handles re-orgs internally:

* [**Re-org Handling**](/streams/streams-concepts/re-org-handling)

***

### Ordering & Edge Cases

In rare cases:

* A `confirmed: true` webhook may arrive before `confirmed: false`

This can occur due to:

* Network latency
* Retry behavior
* Regional delivery differences

Your system should:

* Treat each webhook independently
* Use transaction hash + confirmation flag
* Be idempotent

***

### Common Patterns

**Real-time UX**

* Act on `confirmed: false`
* Update UI optimistically

**Accounting / Persistence**

* Only persist on `confirmed: true`

**Analytics**

* Use both, but deduplicate by transaction hash

***

### Next Steps

* How re-orgs are handled internally → Explore [Re-org Handling](/streams/streams-concepts/re-org-handling)
* How delivery works end-to-end →  Explore [Webhook Delivery](/streams/webhooks/webhook-delivery)
* How to replay affected blocks → Explore [Retries & Replays](/streams/webhooks/retries-and-replays)
