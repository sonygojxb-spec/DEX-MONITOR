> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Test Webhooks

> Learn how Moralis uses test webhooks to validate your endpoint when creating or updating a stream, and how to handle them correctly.

## Overview

Whenever you **create or update a stream**, Moralis sends a **test webhook** to your configured webhook URL.

This test verifies that:

* Your endpoint is reachable
* Your server responds correctly
* Webhook delivery can safely begin

If the test webhook is **not acknowledged successfully**, the stream will **not start**.

***

## When Test Webhooks Are Sent

A test webhook is sent when you:

* Create a new stream
* Update an existing stream (e.g. webhook URL, filters, addresses, chains)
* Reactivate a paused stream

This happens **before** any real on-chain events are delivered.

***

## Required Response

To pass the test webhook:

* Your server **must return a 2xx HTTP status code**
* Common examples: `200`, `201`, `202`

Any non-2xx response will cause the test to fail.

<Note>
  No response body is required - only the status code matters.
</Note>

***

## Test Webhook Payload

The test webhook uses the **same payload structure** as real webhooks for that chain, but contains **empty data**. The shape varies by chain — make sure your handler tolerates the right one.

<Tabs>
  <Tab title="EVM">
    ```javascript theme={null}
    {
      "confirmed": true,
      "chainId": "",
      "streamId": "",
      "tag": "",
      "retries": 0,
      "block": {
        "number": "",
        "hash": "",
        "timestamp": ""
      },
      "logs": [],
      "txs": [],
      "txsInternal": [],
      "erc20Transfers": [],
      "erc20Approvals": [],
      "nftTransfers": [],
      "nftApprovals": {
        "ERC721": [],
        "ERC1155": []
      },
      "abi": {}
    }
    ```
  </Tab>

  <Tab title="Bitcoin">
    ```javascript theme={null}
    {
      "confirmed": true,
      "chainId": "btc-mainnet",
      "streamId": "",
      "tag": "",
      "retries": 0,
      "block": {
        "hash": "",
        "height": 0,
        "timestamp": 0
      },
      "txs": []
    }
    ```
  </Tab>

  <Tab title="Solana">
    ```javascript theme={null}
    {
      "confirmed": true,
      "chainId": "solana_mainnet",
      "network": "mainnet",
      "streamId": "",
      "tag": "",
      "retries": 0,
      "block": {
        "slot": "",
        "blockHash": "",
        "blockHeight": "",
        "blockTime": 0
      },
      "transactions": []
    }
    ```
  </Tab>
</Tabs>

Important notes:

* No on-chain data is included
* No transactions or logs are present
* This payload **should not be persisted**

For full payload documentation, explore [Webhook Payload](/streams/webhooks/webhook-payloads).

***

## How to Handle Test Webhooks

Your webhook handler should:

1. Accept the request
2. Optionally log it
3. Return a 2xx response
4. Skip any application-specific processing

A simple approach is to:

* Detect empty payloads
* Short-circuit processing

***

## Security Considerations

Test webhooks:

* Include an `x-signature` header
* Should be verified the same way as real webhooks

For signature verification, explore [**Webhook Security**](/streams/security-and-reliability/webhook-security)**.**

***

## Common Pitfalls

### Stream does not start

Usually caused by:

* Webhook endpoint returning non-2xx
* Endpoint timing out
* Server not reachable from the internet

### Test webhook processed as real data

Avoid:

* Writing empty events to your database
* Triggering business logic on test payloads

***

## Relationship to Retries & Replays

Test webhooks:

* Are **not retried**
* Are **not stored in history**
* Cannot be replayed

[Retries and Replays](/streams/webhooks/retries-and-replays) apply only to **real event webhooks**.

***

## Next Steps

* Understand delivery guarantees → Explore [Webhook Delivery](/streams/webhooks/webhook-delivery)
* Inspect real payloads → Explore [Webhook Payload](/streams/webhooks/webhook-payloads)
* Secure your endpoint → Explore [Webhook Security](/streams/security-and-reliability/webhook-security)
* Handle failures and recovery →  Explore [Error Handling](/streams/streams-concepts/error-handling)
