> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Webhook Delivery

> Understand how Moralis reliably delivers blockchain events to your backend, including confirmation behavior, retries, ordering guarantees, and failure handling.

## Overview

Webhook Delivery explains **how Streams sends events to your backend**, from the moment an on-chain event occurs to when your server successfully processes it.

Moralis Streams is designed for **high reliability at scale**, handling retries, reorgs, confirmation logic, and backpressure automatically - so you can focus on building application logic.

This page covers *delivery behavior*. For payload structure, configuration, or retries, see the linked pages below.

***

## How Webhook Delivery Works

At a high level:

1. A block is produced on-chain
2. Streams detects matching events
3. Moralis sends a webhook to your endpoint
4. Delivery is retried automatically if it fails
5. Events are finalized once the block is confirmed

You do **not** need to poll or manage state manually.

To get started with creating streams, see:

* [**Create Your First Stream**](/streams/quickstart/create-your-first-stream)

***

## Confirmed vs Unconfirmed Webhooks

For most blockchain events, Streams delivers **two webhooks**:

### 1. Unconfirmed (`confirmed: false`)

* Sent as soon as the block is mined
* Low latency
* Block may still be reorganized

### 2. Confirmed (`confirmed: true`)

* Sent after sufficient confirmations
* Safe to persist as final state

This approach gives you **real-time responsiveness** without sacrificing correctness.

<Danger>
  Edge case: In rare scenarios, a confirmed webhook may arrive before the unconfirmed one. Your system should handle both cases gracefully.
</Danger>

For chain-specific confirmation thresholds, see:

* [**Supported Chains**](/streams/supported-chains)

For how reorgs are handled internally:

* [**Re-org Handling**](/streams/streams-concepts/re-org-handling)

***

## Delivery Guarantees

Moralis provides **at-least-once delivery** for all webhooks.

This means:

* A webhook will be delivered **until your server acknowledges it**
* Failed deliveries are retried automatically
* Duplicate deliveries are possible (and expected)

Your webhook handler **must be idempotent**.

Read more about [Delivery Guarantees](/streams/security-and-reliability/delivery-guarantees).

***

## Automatic Retries

If your server fails to respond successfully:

* Streams retries delivery using an exponential backoff schedule
* Retries continue for up to **24 hours**
* Retry count is included in the payload

Retry behavior is automatic and requires no configuration.

Detailed retry schedules and replay options:

* [**Retries & Replays**](/streams/webhooks/retries-and-replays)

***

## Queueing & Backpressure

To protect system stability, Streams maintains an internal delivery queue per webhook URL.

Key points:

* If your server processes webhooks too slowly, events queue up
* The current queue size is sent in the `x-queue-size` response header
* If the queue reaches its limit, the stream may enter an error state

To avoid this:

* Ensure your webhook endpoint responds quickly
* Offload heavy processing to background workers
* Deploy streams in a region close to your backend

Read more about [Error Handling](/streams/streams-concepts/error-handling).

***

## Ordering Guarantees

Webhook delivery is **not strictly ordered**.

This can happen due to:

* Network retries
* Regional failover
* Confirmed vs unconfirmed delivery timing

You should **not assume ordering** and should always rely on:

* Transaction hash
* Log index
* Block number
* Confirmation state

Explore [Webhook Payload](/streams/webhooks/webhook-payloads) structure details.

***

## Failure States

Streams have multiple operational states:

| Status       | Description                                                      |
| :----------- | :--------------------------------------------------------------- |
| `active`     | Stream is live and delivering webhooks                           |
| `paused`     | Stream is temporarily disabled                                   |
| `error`      | Stream encountered a configuration or delivery error             |
| `terminated` | Stream was automatically stopped after 24 hours in `error` state |

Email notifications are sent when:

* A stream enters error state
* A stream is terminated

Read more about [Stream Lifecycle](/streams/streams-concepts/stream-lifecycle-and-management) details.

***

## Security & Verification

Every webhook includes an `x-signature` header.

You **must verify this signature** to ensure the payload originated from Moralis.

Signature verification is covered here [**Webhook Security**](/streams/security-and-reliability/webhook-security)**.**

***

## When to Use Replays

If your system was down or missed events:

* You can replay individual failed webhooks
* You can replay entire blocks for a stream

Replay tools are covered in [**Retries & Replays**](/streams/webhooks/retries-and-replays)**.**

***

## Common Next Steps

Depending on what you’re building:

* Want to understand the payload structure? Explore [Webhook Payload](/streams/webhooks/webhook-payloads)
* Need to handle retries or replays? Explore [Retries & Replays](/streams/webhooks/retries-and-replays)
* Debugging stream failures? Explore [Error Handling](/streams/streams-concepts/error-handling)
* Hardening security? Explore [Webhook Security](/streams/security-and-reliability/webhook-security)
