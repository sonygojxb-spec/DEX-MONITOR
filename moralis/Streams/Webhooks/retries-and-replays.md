> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Retries & Replays

> Recover missed Streams events by replaying blocks and streams, and understand how Moralis handles retries, failures, and recovery scenarios.

## Overview

Streams is designed for **reliable, real-time delivery**, but there are situations where events may need to be replayed or recovered.

Moralis provides **manual replay mechanisms** to help you recover missed webhooks caused by configuration changes, reload timing, or temporary failures.

***

## When Replays Are Needed

You may need to replay events if:

* A stream was reloading when a block was produced
* Addresses were added shortly before on-chain activity
* A webhook endpoint was temporarily unavailable
* A stream was paused or in an error state
* You are recovering from an incident or deployment issue

Replays allow you to **reprocess past blocks** and receive the webhooks that would have been delivered.

***

## Replay Block

The **Replay Block** feature reprocesses a specific block for a given stream.

When replayed:

* The block is re-evaluated against the stream configuration
* Matching events trigger webhooks again
* Webhooks are delivered as if the block just occurred

This is the most precise way to recover missed events.

***

### When to Use Block Replay

Use block replay when:

* You know the exact block number that was missed
* Only a small time window was affected
* You want to avoid duplicate data outside that block

***

## Replay Best Practices

* Always confirm the stream configuration before replaying
* Replays respect the **current** stream configuration
* Ensure your webhook handler is **idempotent**
* Avoid replaying large numbers of blocks unnecessarily

***

## Webhook Retries vs Replays

It’s important to distinguish between **automatic retries** and **manual replays**.

### Automatic retries

* Triggered when your webhook endpoint returns an error or times out
* Handled automatically by Moralis
* Occur shortly after the initial delivery attempt
* Do **not** require manual intervention

### Manual replays

* Triggered by you
* Used to recover missed events
* Can replay historical blocks
* Useful after configuration changes or outages

***

## Recovery After Stream Reloads

When addresses are added to a stream, a reload is required.

If activity occurs before the reload completes:

* The event may not trigger a webhook
* The block can be recovered using replay

This is a normal and expected edge case for dynamic address management.

***

## Recovery After Errors or Termination

* Streams in the `error` state stop delivering events
* Streams in the `terminated` state stop permanently

In both cases:

* Events occurring during downtime are not queued
* Replays can be used to recover missed blocks
* Terminated streams require creating a new stream before replaying

***

## Designing for Recovery

To make recovery safe and predictable:

* Treat webhook processing as **idempotent**
* Use transaction hashes + log indexes as unique identifiers
* Log replayed events separately if needed
* Avoid assuming delivery order

Streams prioritises **correctness over ordering**.

***

## What Cannot Be Recovered

Replays cannot recover:

* Events that occurred before a stream existed
* Events filtered out by stream configuration
* Events dropped intentionally (e.g. spam filtering)

***

## Summary

* Streams delivers events in real time, with retries
* Reloads and failures can cause missed events
* Block replay allows precise recovery
* Recovery is explicit and controlled
* Idempotent webhook handling is essential
