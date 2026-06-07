> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Rate Limits

> Understand Streams rate limits, address management constraints, and how stream reloads impact webhook delivery.

## Rate Limits & Address Management

Streams rate limits primarily apply to **stream configuration changes**, not event delivery.

The most important limits to understand relate to **adding addresses to a stream**, as these operations trigger internal reloads that affect when monitoring becomes active.

***

## Address Management & Stream Reloads

When you add new addresses to a stream, Moralis must **reload the stream configuration** to include those addresses in monitoring.

This reload:

* Is asynchronous
* Takes longer as the number of addresses increases
* Must complete before new blocks are processed for the added addresses

During a reload, the stream may temporarily be unable to detect events for newly added addresses.

***

## Rate Limits for Adding Addresses

### Address add rate limit

* **Maximum:** 5 requests per 5 minutes
* Each request may include **multiple addresses**

If you need to add many addresses, always batch them into as few requests as possible.

The same rate limit applies on every chain — but what counts as an "address" depends on the chain:

* **EVM** — hex-encoded `0x...` addresses, case-insensitive
* **Bitcoin** — P2PKH (`1...`), P2SH (`3...`), or Bech32 (`bc1q...`). Adding an [xpub](/streams/api-reference/bitcoin/xpub/add-xpub) is a separate operation that auto-derives addresses for HD wallets and is **not** counted as an address-add against this limit.
* **Solana** — base58 addresses, **case-sensitive** (unlike EVM). Programs IDs and mint addresses count toward the same address-add limit when added through the address endpoints.

<Warning>
  Solana addresses must be submitted in their original case. Lowercased addresses will not match.
</Warning>

***

## Impact on Webhook Delivery

### Reload timing

If an address is added shortly before a block is produced:

* The stream may not finish reloading in time
* Events involving the new address in that block may be missed
* No webhook will be sent for those events

This is more likely when:

* The stream already contains many addresses
* Multiple address updates are submitted close together

***

### Reload loops

Submitting many small address-addition requests can:

* Trigger repeated reloads
* Slow down activation of new addresses
* Cause you to hit the rate limit
* Delay effective monitoring

***

## Best Practices

### Batch address updates

Always batch addresses into a single request when possible.\
This reduces reloads and speeds up activation.

***

### Plan address additions ahead of time

If you expect activity on a new address:

* Add it **well before** the expected transaction
* Avoid last-second updates near block times

Streams are not designed for ultra-last-second address registration.

***

## Handling Missed Events

If you believe events were missed due to reload timing:

### 1. Verify address addition

Confirm the address was successfully added using the **Get Stream Info** endpoint.

### 2. Replay affected blocks

Use the **Replay Block** endpoint with:

* The affected block number
* The relevant stream ID

This allows Moralis to reprocess the block and resend applicable webhooks.

***

## What Rate Limits Do *Not* Apply To

* Event delivery volume
* Number of webhooks received
* Number of monitored events per block

These are governed by stream configuration and pricing, not per-request rate limits.

***

## Summary

* Address additions trigger stream reloads
* Reloads are not instantaneous
* Address add requests are rate limited
* Batch updates and planning ahead are essential
* Missed events can be recovered using block replay
