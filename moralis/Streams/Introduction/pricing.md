> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Pricing

> Understand how Streams API usage is calculated using records and compute units across EVM, Bitcoin, and Solana — and learn how to optimize your costs.

## Records

Records are the fundamental unit for calculating Streams API usage. **What counts as a record depends on the chain** — see the chain-specific sections below.

Each record costs **10 Compute Units (CUs)**. The `x-records-charged` header in webhook responses shows the exact record count for that delivery.

<Info>
  Only webhooks with `confirmed: true` incur charges. Unconfirmed webhooks (`confirmed: false`) have `x-records-charged: 0` and are free.
</Info>

For each match, you receive two webhooks:

1. **Unconfirmed** — sent when the transaction is included in a block (free).
2. **Confirmed** — sent once the block is considered final (charged).

<Note>
  Across all chains, the unconfirmed (`confirmed: false`) delivery is sent when the matching transaction is first included in a block (or slot, on Solana). The confirmed (`confirmed: true`) delivery is sent after the chain's reorg-safety threshold has passed — see [Supported Chains](/streams/supported-chains). Only the confirmed delivery is charged.
</Note>

***

## What Counts as a Record

<Tabs>
  <Tab title="EVM">
    A record on EVM is one of the following:

    * A native transaction (`txs`)
    * A log event (`logs`)
    * An internal transaction (`txsInternal`)

    The total record count for a webhook equals the sum of all three: **txs + logs + txsInternal**.

    ### Records by transaction type

    The number of records charged varies depending on transaction complexity:

    | Transaction Type              | Records Charged |
    | ----------------------------- | --------------- |
    | Native transfer               | 1 record        |
    | ERC-20 transfer               | 2 records       |
    | Single NFT transfer (ERC-721) | 11 records      |
    | Batch NFT transfer (ERC-1155) | 2 records       |
    | ERC-721 minting (100 tokens)  | 100 records     |

    ### Decoded logs are free

    Moralis automatically decodes standardized contract events at **no additional cost**. These do **not** count as records:

    * `erc20Transfers`
    * `erc20Approvals`
    * `nftTransfers`
    * `nftApprovals`
  </Tab>

  <Tab title="Bitcoin">
    A record on Bitcoin is a single matched **transaction** (`txs`). Bitcoin payloads do not contain logs or internal transactions, so:

    | Transaction Type        | Records Charged |
    | ----------------------- | --------------- |
    | Any matched transaction | 1 record        |

    Each confirmed delivery charges **1 record (10 CUs) per matched transaction**, regardless of how many `vout` entries match watched addresses.
  </Tab>

  <Tab title="Solana">
    A record on Solana is a single matched **transaction**. Solana payloads do not contain logs or internal transactions in the EVM sense, so:

    | Transaction Type        | Records Charged |
    | ----------------------- | --------------- |
    | Any matched transaction | 1 record        |

    Each confirmed delivery charges **1 record (10 CUs) per matched transaction**, regardless of how many `accountKeys`, instructions, or token balance changes are included.
  </Tab>
</Tabs>

***

## Monitoring Your Usage

Use the [Get Stats](/streams/api-reference/stats/get-stats) endpoint to track your consumption.

<Tabs>
  <Tab title="EVM">
    The stats endpoint returns:

    * `totalLogsProcessed`
    * `totalTxsProcessed`
    * `totalTxsInternalProcessed`

    Sum these values to determine total records consumed during your billing period.
  </Tab>

  <Tab title="Bitcoin">
    The stats endpoint returns `totalTxsProcessed` for Bitcoin streams. `totalLogsProcessed` and `totalTxsInternalProcessed` are EVM-only counters and are not populated for Bitcoin.
  </Tab>

  <Tab title="Solana">
    The stats endpoint returns `totalTxsProcessed` for Solana streams. `totalLogsProcessed` and `totalTxsInternalProcessed` are EVM-only counters and are not populated for Solana.
  </Tab>
</Tabs>

***

## Plan Limits

For details on CU allocations, throughput limits, and plan comparisons, visit the [Moralis Pricing Page](https://moralis.io/pricing).
