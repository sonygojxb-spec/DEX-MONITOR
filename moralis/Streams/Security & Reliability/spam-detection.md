> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Spam Detection

> Learn how Moralis Streams identifies and flags potential spam contracts in webhook payloads, helping you filter or handle suspicious on-chain activity safely.

<Note>
  Spam detection is an **EVM-only** feature. Bitcoin and Solana streams do not include `possibleSpam` flags or spam-based filtering.
</Note>

<Warning>
  Streams currently uses a legacy spam detection system. This will be upgraded to align with the newer Moralis [API Spam Detection](/data-api/resources/spam-filtering) in a future release.
</Warning>

Spam detection in Moralis Streams provides an **additional safety signal** that helps you identify contracts associated with spam, phishing, or suspicious activity.

This feature allows you to:

* Detect potentially malicious contracts in real time
* Filter or suppress spam-related events
* Warn users about risky interactions

***

## How Spam Detection Works

When spam detection is enabled, Streams adds a boolean field called:

```javascript theme={null}
possibleSpam
```

This field is attached to the following webhook objects:

* `erc20Transfers`
* `erc20Approvals`
* `nftTransfers`
* `nftApprovals`

The value indicates whether the contract involved in the event is **potentially associated with spam or malicious behavior**.

Example:

```javascript theme={null}
{
  "contract": "0x...",
  "possibleSpam": true
}
```

***

## How to Use Spam Signals

The `possibleSpam` flag is designed as a **signal**, not a hard block.

Common usage patterns include:

* Hiding spam tokens or NFTs from user interfaces
* Suppressing notifications for spam-related activity
* Flagging risky activity for manual review
* Applying stricter filters to spam-flagged events

Filtering options:

* [**Filters**](/streams/streams-concepts/filters)

***

## Filtering Out Spam Events

You can configure Streams to **exclude spam-related events entirely**.

By enabling the `filterPossibleSpamAddresses` option:

* Events involving contracts flagged as spam will not trigger webhooks
* These events will not consume stream usage

This is useful if you want to:

* Reduce noise
* Avoid processing low-quality or malicious activity

Related configuration:

* [**Filters**](/streams/streams-concepts/filters)
* [**Advanced Options**](/streams/streams-concepts/advanced-options)

***

## How Contracts Are Classified

Contracts flagged as spam are evaluated against a set of internal criteria, including:

* Compliance with token and NFT standards
* Minting and transfer behavior (e.g. honeypot patterns)
* Copycat or impersonation signals
* Other proprietary heuristics

Classification is **continuously updated** as new data becomes available.

***

## Supported Chains

Spam detection in Streams is supported on **all EVM-compatible chains**, with the strongest initial coverage on:

* Ethereum Mainnet
* Polygon Mainnet
* BNB Chain

***

## Relationship to API Spam Detection

Streams spam detection is **separate from** the newer Moralis API [Spam Filtering](/data-api/resources/spam-filtering) and [Token Safety](/data-api/data-features/token-scores) features.

Key differences:

* Streams uses a legacy classification system
* API spam detection includes richer metadata and filtering
* The two systems will be unified in a future update

API spam features:

* [**Spam Filtering**](/data-api/resources/spam-filtering)
* [**Token Scores**](/data-api/data-features/token-scores)

***

## Best Practices

* Treat `possibleSpam` as a signal, not absolute truth
* Combine spam flags with confirmation state
* Avoid persisting spam events unless required
* Prefer filtering spam at the stream level when possible

***

## Related Pages

* [**Streams Filters**](/streams/streams-concepts/filters)
* [**Advanced Options**](/streams/streams-concepts/advanced-options)
* [**Webhook Payload**](/streams/webhooks/webhook-payloads)
* [**API Spam Filtering**](/data-api/resources/spam-filtering)
* [**Delivery Guarantees**](/streams/security-and-reliability/delivery-guarantees)
