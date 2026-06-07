> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Error Handling

> Understand how Streams handles webhook failures, retries, error states, termination, and how to recover from delivery issues safely.

## Overview

Streams is designed for **reliable, at-least-once delivery** of webhook events.\
While Moralis handles retries and failure recovery automatically, errors can still occur—most commonly due to webhook endpoint availability or throughput constraints.

This page explains:

* How delivery failures are handled
* When streams enter error or terminated states
* How retries, replays, and recovery work
* What actions you should take in production

***

## Delivery Guarantees (Important Context)

Moralis guarantees **at-least-once delivery** of webhooks while a stream is active.

This means:

* Webhooks may be retried
* Duplicate deliveries are possible
* Your webhook handler **must be idempotent**

Correctness is prioritised over strict ordering.

***

## Automatic Webhook Retries

If a webhook delivery fails (timeout, network error, non-2xx response), Moralis automatically retries delivery using an exponential backoff strategy.

### Retry schedule

| Attempt | Interval   |
| :------ | :--------- |
| 0       | 1 minute   |
| 1       | 10 minutes |
| 2       | 1 hour     |
| 3       | 2 hours    |
| 4       | 6 hours    |
| 5       | 12 hours   |
| 6       | 24 hours   |

Retries apply only to **delivery failures**.\
They do not reprocess blocks or regenerate events.

***

## Error State

A stream may enter the `error` state under the following conditions:

### 1. Low webhook success rate

If the webhook success rate for a stream drops **below 70%**, the stream enters the error state.

### 2. Delivery backlog (queue saturation)

If your server cannot consume webhooks fast enough:

* A delivery queue builds up
* The queue reaches its maximum size (10,000 events)
* The stream is placed into the error state

You can monitor queue pressure using the `x-queue-size` response header.

***

### Behaviour in Error State

When a stream is in the `error` state:

* Webhook delivery is **paused**
* Events are **not delivered**
* Blocks are **still evaluated**
* Retry scheduling resumes once the stream is reactivated

An **email notification** is sent when a stream enters this state.

***

## Terminated State

If a stream remains in the `error` state for **24 hours**, it is automatically **terminated**.

### Behaviour in Terminated State

A terminated stream:

* Does **not** send webhooks
* Does **not** process new blocks
* Drops all subsequent events permanently
* Cannot be resumed

An **email notification** is sent when termination occurs.

To recover, a **new stream must be created**.

***

## Webhook Success Rate

Each stream tracks a webhook success rate per webhook URL:

* Starts at **100%**
* Each failed delivery reduces the rate by **1%**
* Each successful delivery increases the rate by **1%**
* Capped between **0% and 100%**

If the success rate falls below **70%**, the stream enters the error state.

***

## Viewing Failed Webhooks

Failed webhook deliveries are retained for a limited time (plan-dependent, up to 7 days).

### Retrieve failed deliveries

```javascript theme={null}
const history = await Moralis.Streams.getHistory({ limit: 100 });
```

Each failed delivery includes:

* Webhook payload
* Error message
* Stream ID
* Timestamp
* Unique history ID

***

## Replaying Failed Webhooks

Failed webhooks can be replayed manually.

### Replay a failed webhook

```javascript theme={null}
await Moralis.Streams.retry({
  id: "HISTORY_ID",
  streamId: "STREAM_ID",
});
```

Replayed webhooks are delivered with the same payload as the original attempt.

<Note>
  Replays do not regenerate events or reprocess blocks.
</Note>

For block-level recovery, use **Replay Block** (see *Retries & Replays*).

***

## Best Practices to Avoid Errors

* Ensure webhook endpoints respond quickly and consistently
* Treat webhook handling as **idempotent**
* Monitor `x-queue-size` headers
* Choose a stream region close to your backend
* Pause streams during planned outages
* Act promptly on error-state email notifications

***

## Summary

* Delivery failures trigger automatic retries
* Prolonged failures cause streams to enter `error`
* Error state pauses delivery but preserves configuration
* 24 hours in error results in termination
* Failed deliveries can be replayed
* Block-level recovery requires replay
