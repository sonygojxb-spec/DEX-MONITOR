> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Ordering & Idempotency

> Learn how Moralis delivers events without strict ordering guarantees, and how to design idempotent consumers that handle retries, duplicates, and replays safely.

## Overview

Blockchain data is produced by distributed systems and delivered over networks that can fail, retry, and recover.

As a result, Moralis does **not** guarantee strict ordering or single delivery of events. Instead, it prioritizes **reliability and correctness**.

This page explains:

* Why events may arrive out of order
* Why duplicate deliveries are possible
* How to process events safely using idempotency

***

## Why Ordering Is Not Guaranteed

Events may arrive out of order due to:

* Network latency and retries
* Automatic retry behavior on delivery failure
* Manual replay of historical events
* Confirmed and unconfirmed events being delivered separately
* Regional delivery differences

This behavior is expected and intentional.

Delivery mechanics:

* [**Webhook Delivery**](/streams/webhooks/webhook-delivery)

***

## What You Can Rely On Instead

Every webhook payload includes stable identifiers that allow you to reason about order and uniqueness:

* Chain ID
* Block number
* Transaction hash
* Log index (for contract events)
* Confirmation state (`confirmed`)

Payload reference:

* [**Webhook Payload**](/streams/webhooks/webhook-payloads)

These fields let you:

* Deduplicate events
* Sort events deterministically
* Reconcile final state safely

***

## What Idempotency Means

Idempotent processing means:

> Handling the same event multiple times produces the same result as handling it once.

This is essential because:

* Webhooks may be retried automatically
* Replays intentionally resend historical events
* Network failures may cause duplicate deliveries

Retry and replay behavior:

* [**Retries & Replays**](/streams/webhooks/retries-and-replays)

***

## Recommended Idempotency Strategies

### Use deterministic event keys

Pick a key that's stable for the chain you're consuming:

* **EVM** — `transactionHash`, or `transactionHash + logIndex` for log-level events. `streamId + transactionHash` works when consuming multiple streams.
* **Bitcoin** — `txid` (each transaction is delivered twice, once at first block inclusion and once after the 2-block confirmation depth; upsert on the second delivery to flip `confirmed`).
* **Solana** — `signature` (the base58 transaction id).

Store processed keys and ignore duplicates.

***

### Treat unconfirmed events as provisional

* Use `confirmed: false` for real-time UX
* Persist state only on `confirmed: true`

Confirmation model:

* [**Confirmation & Finality**](/streams/webhooks/confirmation-and-finality)

***

### Design replays to be safe

Replays should:

* Reapply state deterministically
* Overwrite or reconcile existing records
* Never assume data is “new”

Recovery workflows:

* [**Retries & Replays**](/streams/webhooks/retries-and-replays)

***

## Common Mistakes to Avoid

* Assuming webhook arrival order equals block order
* Using arrival timestamps as a source of truth
* Mutating permanent state on unconfirmed events
* Failing or crashing on duplicate payloads

***

## Relationship to Delivery Guarantees

| Topic              | Page                                                                             |
| :----------------- | :------------------------------------------------------------------------------- |
| Reliable delivery  | [**Delivery Guarantees**](/streams/security-and-reliability/delivery-guarantees) |
| Retry behavior     | [**Retries & Replays**](/streams/webhooks/retries-and-replays)                   |
| Confirmation model | [**Confirmation & Finality**](/streams/webhooks/confirmation-and-finality)       |
| Re-org handling    | [**Re-org Handling**](/streams/streams-concepts/re-org-handling)                 |

***

## Best Practices Summary

* Expect duplicates
* Do not assume ordering
* Persist only confirmed state
* Make handlers idempotent by design

***

## Next Steps

* Understand delivery mechanics → Explore [Webhook Delivery](/streams/webhooks/webhook-delivery)
* Plan recovery flows → Explore [Retries & Replays](/streams/webhooks/retries-and-replays)
* Handle confirmations correctly → Explore [Confirmation & Finality](/streams/webhooks/confirmation-and-finality)
* Protect against re-orgs → Explore [Re-org Handling](/streams/streams-concepts/re-org-handling)
