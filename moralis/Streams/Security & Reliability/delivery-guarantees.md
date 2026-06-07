> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Delivery Guarantees

> Learn how Moralis reliably delivers blockchain data, including retry behavior, durability, and how events are protected from data loss.

## Overview

Moralis is built to deliver blockchain data **reliably**, even in the presence of network issues, server downtime, or blockchain reorganizations.

This page explains:

* What Moralis guarantees
* How delivery failures are handled
* What you should expect when consuming events at scale

***

## Reliable Event Delivery

Moralis ensures that **eligible blockchain events are not silently lost**.

If a webhook delivery fails (for example, due to a timeout or server error), Moralis will **automatically retry delivery** until the event is acknowledged or the retry window expires.

As a result:

* Events are delivered reliably
* Temporary failures do not cause data loss
* Duplicate deliveries are possible and expected in failure scenarios

Delivery mechanics:

* [**Webhook Delivery**](/streams/webhooks/webhook-delivery)
* [**Retries & Replays**](/streams/webhooks/retries-and-replays)

***

## What This Means in Practice

Under normal operation:

* Each event is delivered once

If delivery fails:

* The event is retried automatically
* The same payload may be sent again
* Your system should handle duplicates safely

This design favors **correctness and completeness** over strict delivery assumptions.

Guidance on safe handling:

* [**Ordering & Idempotency**](/streams/security-and-reliability/ordering-and-idempotency)

***

## Durable Storage & Recovery

When delivery issues occur:

* Failed webhook deliveries are retained (plan-dependent)
* Events can be replayed manually if needed
* Delivery resumes automatically once issues are resolved

Recovery options:

* [**Retries & Replays**](/streams/webhooks/retries-and-replays)
* [**Error Handling**](/streams/streams-concepts/error-handling)

***

## Blockchain Reorganization Safety

Blockchains are probabilistic systems. Transactions may appear in a block and later be removed due to reorganization.

Moralis handles this by:

* Delivering provisional events (`confirmed: false`)
* Finalizing only confirmed events (`confirmed: true`)
* Preventing invalidated data from being treated as final

More details:

* [**Confirmation & Finality**](/streams/webhooks/confirmation-and-finality)
* [**Re-org Handling**](/streams/streams-concepts/re-org-handling)

***

## What Moralis Does *Not* Guarantee

### Strict ordering

Events may arrive:

* Out of order
* With retries interleaved
* With confirmed events preceding unconfirmed ones (rare)

Ordering is intentionally relaxed to ensure reliability.

Ordering strategies:

* [**Ordering & Idempotency**](/streams/security-and-reliability/ordering-and-idempotency)

***

### Reliable Delivery with Retries

Moralis does not attempt to deliver each event *exactly once*.

Exactly-once delivery is not realistically achievable across network boundaries and webhook-based systems. Instead, Moralis guarantees **reliable delivery with retries**, and expects consumers to be idempotent.

***

## Operational Safeguards

To protect delivery reliability, Moralis includes:

* Automatic retry schedules
* Delivery queue limits and backpressure
* Stream health monitoring
* Error and termination states
* Email notifications on critical failures

Operational details:

* [**Error Handling**](/streams/streams-concepts/error-handling)
* [**Stream Lifecycle**](/streams/streams-concepts/stream-lifecycle-and-management)

***

## Best Practices

To fully benefit from Moralis’ delivery guarantees:

* Make webhook handlers idempotent
* Persist state only for confirmed events
* Monitor queue size headers
* Use replays for recovery, not polling

***

## Related Pages

* [**Ordering & Idempotency**](/streams/security-and-reliability/ordering-and-idempotency)
* [**Webhook Delivery**](/streams/webhooks/webhook-delivery)
* [**Retries & Replays**](/streams/webhooks/retries-and-replays)
* [**Error Handling**](/streams/streams-concepts/error-handling)
* [**Confirmation & Finality**](/streams/webhooks/confirmation-and-finality)
