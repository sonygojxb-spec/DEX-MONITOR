> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Re-org Handling

> Learn how Moralis Streams detects and handles blockchain reorganizations to ensure reliable and consistent event delivery.

### Overview

A blockchain reorganization (re-org) occurs when a previously accepted block is replaced by another block at the same height.

Re-orgs are a normal part of blockchain operation, especially on:

* High-throughput chains
* L2s
* Testnets

Moralis Streams is designed to **handle re-orgs safely and transparently**.

***

### How Streams Handles Re-orgs

When a re-org occurs:

1. Streams detects the replaced block
2. Events from the dropped block are invalidated
3. Replacement block events are processed
4. Confirmation logic is recalculated

You do **not** need to manually detect or resolve re-orgs.

***

### Impact on Webhooks

Re-org handling is reflected through:

* `confirmed: false` events that may not be finalized
* `confirmed: true` events only sent after finality

If a transaction is removed due to a re-org:

* It will **not** receive a confirmed webhook
* Replacement transactions will be delivered instead

See also:

* [**Confirmation & Finality**](/streams/webhooks/confirmation-and-finality)
* [**Webhook Delivery**](/streams/webhooks/webhook-delivery)

***

### Why This Matters

Without re-org handling, applications risk:

* Double-counting transactions
* Incorrect balances
* Invalid ownership state

Streams ensures:

* Only finalized state is confirmed
* Re-orgs do not corrupt downstream systems

***

### Re-org Behavior by Chain

* **EVM** — re-orgs are most common on high-throughput chains, L2s, and testnets. Confirmation thresholds vary per chain (see [Supported Chains](/streams/supported-chains)).
* **Bitcoin** — re-orgs follow the longest-valid-chain rule and are exponentially less likely with each additional confirmation.
* **Solana** — re-orgs are rare and bounded by the network's slot-based finality model.

In all cases, the same Streams handling applies: dropped transactions never receive a `confirmed: true` webhook, and replacement transactions are delivered in their place.

***

### Replays & Recovery

If your system was offline during a re-org:

* You can replay affected blocks
* You can replay failed webhooks

See also:

* [**Retries & Replays**](/streams/webhooks/retries-and-replays)

***

### Best Practices

* Treat `confirmed: false` as provisional
* Persist only confirmed state
* Make handlers idempotent
* Use replays for recovery, not polling
