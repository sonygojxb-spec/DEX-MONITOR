> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Internal Transactions

> Understand and access internal transactions to get a complete view of wallet activity, contract execution, and native value transfers on EVM chains.

## Overview

Internal transactions are a critical part of many EVM-based interactions - and without them, **your data is incomplete**.

Moralis provides **full historical and real-time support for internal transactions**, allowing you to capture value transfers and contract interactions that do **not** appear as standalone blockchain transactions.

This is a key differentiator versus many APIs that only index external (user-initiated) transactions.

Related pages:

* [Wallet History](/data-api/evm/wallet/wallet-history)
* [Raw Transactions](/data-api/evm/wallet/wallet-transactions)
* [Transaction Decoding](/data-api/data-features/data-enrichment/transaction-decoding)

***

## What are internal transactions?

Internal transactions are **value transfers and contract calls that occur during the execution of a transaction**, rather than being initiated directly by an externally owned account (EOA).

They typically occur when:

* A smart contract calls another contract
* A contract transfers native currency (ETH, BNB, etc.)
* A single transaction triggers multiple downstream actions

> Internal transactions are **not separate blockchain transactions** - they are derived from EVM execution traces.

***

## Why internal transactions matter

Without internal transactions, you miss:

* Native transfers triggered by smart contracts
* Airdrops distributed within a single transaction
* Protocol rewards, fees, and payouts
* Full wallet balance movements
* Complete contract execution paths

### Example

A user interacts with a DeFi protocol:

1. User sends **one** transaction
2. Contract distributes ETH to multiple addresses internally
3. Only internal transactions show where value actually moved

Without internal transactions:

* Wallet history is incomplete
* Net worth calculations are wrong
* Important events appear to be missing

***

## What Moralis provides

Moralis indexes **full EVM execution traces**, enabling:

* Historical internal transactions
* Real-time internal transaction detection
* Native value transfers inside contract calls
* Consistent internal transaction data across APIs

This ensures:

* Complete wallet activity
* Accurate portfolio and PnL calculations
* Better protocol analytics

***

## Supported chains

Internal transactions are supported across all major EVM **mainnet** networks, with **full historical coverage**. Testnets are not supported.

| Chain            | Real-time | Historical |
| :--------------- | :-------- | :--------- |
| Ethereum Mainnet | ✅         | ✅          |
| Polygon Mainnet  | ✅         | ✅          |
| BNB Chain        | ✅         | ✅          |
| Arbitrum         | ✅         | ✅          |
| Avalanche        | ✅         | ✅          |
| Base             | ✅         | ✅          |
| Optimism         | ✅         | ✅          |
| Fantom           | ✅         | ✅          |
| Linea            | ✅         | ✅          |
| Chiliz           | ✅         | ✅          |
| Monad Mainnet    | ✅         | ✅          |

***

## Internal transactions vs external transactions

| Feature                               | External | Internal |
| :------------------------------------ | :------- | :------- |
| Initiated by user                     | ✅        | ❌        |
| Has its own tx hash                   | ✅        | ❌        |
| Appears on block explorers by default | ✅        | ❌        |
| Transfers native value                | ✅        | ✅        |
| Required for full wallet history      | ✅        | ✅        |

***

## Streams support

Internal transactions are also available in **Streams**, enabling:

* Real-time detection of internal value transfers
* Monitoring protocol payouts and rewards
* Capturing native transfers triggered by contracts

See:

* [Streams Overview](/streams/overview)
* [Webhook Payload](/streams/webhooks/webhook-payloads)

***

## Summary

Internal transactions are essential for **accurate, production-grade blockchain data**.

Moralis provides:

* Full historical and real-time internal transactions
* Broad EVM chain coverage
* Simple access via existing and dedicated endpoints

If you care about **completeness**, internal transactions are not optional.
