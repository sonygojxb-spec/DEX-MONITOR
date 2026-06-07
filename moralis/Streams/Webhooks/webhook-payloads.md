> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Webhook Payload

> Understand the structure of Streams webhook payloads across EVM, Bitcoin, and Solana — including transactions, transfers, logs, confirmations, retries, and signature verification.

## Overview

Every Streams webhook delivers a **JSON payload** containing the on-chain events that match your stream configuration.

Payload shape depends on the chain:

* **EVM** payloads include native transactions, internal transactions, contract logs, and free decoded ERC-20 / NFT transfers and approvals.
* **Bitcoin** payloads include block metadata and matched transactions with output (`vout`) and input (`vin`) details.
* **Solana** payloads include slot/block metadata and matched transactions with `accountKeys`, instructions, inner instructions, and pre/post token balances.

The exact contents within each chain depend on the options enabled when the stream was created.

***

## Top-Level Payload Structure

<Tabs>
  <Tab title="EVM">
    ```javascript theme={null}
    {
      "confirmed": false,
      "chainId": "0x1",
      "streamId": "uuid",
      "tag": "string",
      "retries": 0,
      "block": { },
      "logs": [],
      "txs": [],
      "txsInternal": [],
      "erc20Transfers": [],
      "erc20Approvals": [],
      "nftTransfers": [],
      "nftApprovals": { "ERC721": [], "ERC1155": [] }
    }
    ```

    | Field         | Description                      |
    | :------------ | :------------------------------- |
    | `confirmed`   | Whether the block is finalized   |
    | `chainId`     | Hex-encoded EVM chain ID         |
    | `streamId`    | Unique stream identifier         |
    | `tag`         | Optional stream tag              |
    | `retries`     | Number of delivery attempts      |
    | `block`       | Block metadata                   |
    | `logs`        | Raw smart contract logs          |
    | `txs`         | Native transactions              |
    | `txsInternal` | Internal (contract) transactions |
  </Tab>

  <Tab title="Bitcoin">
    ```javascript theme={null}
    {
      "confirmed": false,
      "chainId": "btc-mainnet",
      "streamId": "uuid",
      "tag": "string",
      "retries": 0,
      "block": {
        "hash": "00000000000000000003c4...",
        "height": 832150,
        "timestamp": 1709120448,
        "difficulty": "...",
        "merkleRoot": "...",
        "txCount": 3214
      },
      "txs": [
        {
          "txid": "abc...",
          "version": 2,
          "locktime": 0,
          "vin": [
            { "txid": "prev...", "vout": 0, "address": null, "value": null }
          ],
          "vout": [
            {
              "n": 0,
              "value": 3.13258866,
              "scriptPubKey": {
                "address": "bc1q...",
                "type": "witness_v0_keyhash"
              }
            }
          ]
        }
      ]
    }
    ```

    | Field       | Description                                                                                                                 |
    | :---------- | :-------------------------------------------------------------------------------------------------------------------------- |
    | `confirmed` | `false` for the near-tip delivery (block could still be reorged), `true` once it has cleared the 2-block confirmation depth |
    | `chainId`   | `btc-mainnet`                                                                                                               |
    | `streamId`  | Unique stream identifier                                                                                                    |
    | `tag`       | Optional stream tag                                                                                                         |
    | `retries`   | Number of delivery attempts                                                                                                 |
    | `block`     | Block metadata: hash, height, timestamp, difficulty, merkle root, tx count                                                  |
    | `txs`       | Matched transactions with `txid`, `vin`, `vout`                                                                             |

    <Note>
      Output values are represented as **BTC decimals** (e.g. `3.13258866`), not satoshis. Convert with `Math.round(btc * 1e8)` for integer ledgers.
    </Note>

    <Note>
      **Mempool deliveries** use the same payload shape with sentinel values: `block.height: "0"` and `block.hash: "mempool"`. Branch on `block.hash === "mempool"` to separate pre-confirmation events from in-block events. See [Mempool Notifications](/streams/bitcoin-streams#mempool-notifications).
    </Note>

    <Warning>
      For confirmed-block deliveries, input `address` and `value` fields return `null` even with `includeInputs: true` — Bitcoin Streams reliably detects **inbound** transfers to watched addresses, not outflows. Mempool deliveries populate both `vin` and `vout` addresses, so sends and receives both match. See [Bitcoin Streams](/streams/bitcoin-streams) for the full list of behaviors.
    </Warning>
  </Tab>

  <Tab title="Solana">
    ```javascript theme={null}
    {
      "block": {
        "slot": "410060994",
        "blockHash": "7xJ9Km3V...",
        "blockHeight": "389230112",
        "blockTime": 1743436800,
        "parentSlot": "410060993",
        "previousBlockHash": "9aB2cD4e..."
      },
      "chainId": "solana_mainnet",
      "network": "mainnet",
      "retries": 0,
      "streamId": "3f6684f3-2ba4-44d7-af0e-26ee70cab245",
      "tag": "my-solana-stream",
      "confirmed": false,
      "transactions": [
        {
          "signature": "5KtP...signature_base58",
          "slot": "410060994",
          "blockTime": 1743436800,
          "fee": "5000",
          "err": null,
          "accountKeys": [
            "GoSBxCH19sMnZVEifsXeeMdEfkTv6Zh6MWvQFQF3e5m7",
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "11111111111111111111111111111111"
          ],
          "instructions": [],
          "innerInstructions": [],
          "preTokenBalances": [],
          "postTokenBalances": []
        }
      ]
    }
    ```

    | Field          | Description                                                              |
    | :------------- | :----------------------------------------------------------------------- |
    | `confirmed`    | Whether the block is finalized                                           |
    | `chainId`      | `solana_mainnet`                                                         |
    | `network`      | `mainnet`                                                                |
    | `streamId`     | Unique stream identifier                                                 |
    | `tag`          | Optional stream tag                                                      |
    | `retries`      | Number of delivery attempts                                              |
    | `block`        | Slot, block hash, block height, block time, parent slot                  |
    | `transactions` | Matched transactions with `signature`, `accountKeys`, instructions, etc. |

    <Warning>
      Solana addresses are base58 and **case-sensitive**. Submit them in their original case — unlike EVM, lowercased addresses will not match.
    </Warning>

    The Solana fields you'll reach for first: `signature` (transaction id), `accountKeys` (every account the transaction touches), `instructions[].programId` (which programs were invoked), `preTokenBalances` / `postTokenBalances` (SPL balance snapshots for delta calculation). For background on how Solana differs from EVM, see [Solana Streams](/streams/solana-streams).
  </Tab>
</Tabs>

If you're unfamiliar with any of these fields, see [Parsed Data](/streams/streams-concepts/parsed-data) and [Advanced Options](/streams/streams-concepts/advanced-options) (EVM-only).

***

## Confirmed vs Unconfirmed Events

Streams sends **two webhook payloads per match**:

1. **Unconfirmed (`confirmed: false`)** — sent as soon as the matching transaction is included in a block (or slot, on Solana). The block is close to the chain tip and could still be reorged.
2. **Confirmed (`confirmed: true`)** — sent after the chain's reorg-safety threshold has passed and the same block has been re-fetched.

This design lets you react instantly to on-chain activity, then safely update state once finality is guaranteed.

<Note>
  For chain-specific confirmation rules and finality models, see [Supported Chains](/streams/supported-chains) and [Confirmation & Finality](/streams/webhooks/confirmation-and-finality).

  For how reorgs are handled, see [Re-org Handling](/streams/streams-concepts/re-org-handling).
</Note>

***

## Verifying Webhook Authenticity

Every webhook includes an `x-signature` header. You **must verify this signature** to ensure the payload originated from Moralis. Verification is identical for EVM, Bitcoin, and Solana payloads.

Basic flow:

1. Read the raw request body
2. Hash it together with your Streams secret
3. Compare against `x-signature`

See [Webhook Security](/streams/security-and-reliability/webhook-security) for full details.

***

## Detailed Payload Contents

<Tabs>
  <Tab title="EVM">
    ### Native Transactions (`txs`)

    Included when `includeNativeTxs` is enabled. Native transactions include sender and recipient, value transferred, gas usage, and receipt fields.

    ```javascript expandable theme={null}
    {
      "confirmed": false,
      "chainId": "0x1",
      "abi": [],
      "streamId": "c28d9e2e-ae9d-4fe6-9fc0-5fcde2dcdd17",
      "tag": "native_transactions",
      "retries": 0,
      "block": {
        "number": "15988759",
        "hash": "0x3aa07bd98e328db97ec273ce06b3a15fc645931fbd26337fe20c48b274277f76",
        "timestamp": "1668676247"
      },
      "logs": [],
      "txs": [
        {
          "hash": "0xd68700a0e2abd9c041eb236812e4194bf91c8182a2b03065887ab0f33d5c2958",
          "gas": "149200",
          "gasPrice": "13670412399",
          "nonce": "57995",
          "input": "0xf78dc253...",
          "transactionIndex": "52",
          "fromAddress": "0x839d4641f97153b0ff26ab837860c479e2bd0242",
          "toAddress": "0x1111111254eeb25477b68fb85ed929f73a960582",
          "value": "0",
          "type": "2",
          "v": "1",
          "r": "...",
          "s": "...",
          "receiptCumulativeGasUsed": "3131649",
          "receiptGasUsed": "113816",
          "receiptContractAddress": null,
          "receiptRoot": null,
          "receiptStatus": "1"
        }
      ],
      "txsInternal": [],
      "erc20Transfers": [],
      "erc20Approvals": [],
      "nftApprovals": { "ERC1155": [], "ERC721": [] },
      "nftTransfers": []
    }
    ```

    ### Contract Logs (`logs`)

    Included when `includeContractLogs` is enabled. Logs contain raw topics and data, the emitting contract address, the transaction hash, and a log index. Logs are automatically decoded into higher-level objects when applicable (see below).

    ```javascript expandable theme={null}
    {
      "confirmed": false,
      "chainId": "0x1",
      "abi": [
        {
          "anonymous": false,
          "inputs": [
            { "indexed": false, "name": "reserve0", "type": "uint112" },
            { "indexed": false, "name": "reserve1", "type": "uint112" }
          ],
          "name": "Sync",
          "type": "event"
        }
      ],
      "streamId": "6378fe38-54c7-4816-8d61-fca8e128e260",
      "tag": "test_events",
      "retries": 1,
      "block": {
        "number": "15984246",
        "hash": "0x7f8d8285b572a60f6a14d5f1dcbd40e487ccffd9ec78f8dfbccb49aa191fbb95",
        "timestamp": "1668621827"
      },
      "logs": [
        {
          "logIndex": "320",
          "transactionHash": "0xf1682fa49b83689093b467ac6937785102895fc3ba418624c28d04f9af6e5e2b",
          "address": "0x4cd36d6f32586177e36179a810595a33163a20bf",
          "data": "0x00000000000000000000000000000000000000000000944ad388817e590ab607...",
          "topic0": "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1",
          "topic1": null,
          "topic2": null,
          "topic3": null
        }
      ],
      "txs": [],
      "txsInternal": [],
      "erc20Transfers": [],
      "erc20Approvals": [],
      "nftApprovals": { "ERC1155": [], "ERC721": [] },
      "nftTransfers": []
    }
    ```

    ### ERC-20 Transfers

    ERC-20 transfers are **automatically decoded** from logs and included at no additional cost. Each transfer includes `from`, `to`, `value`, token metadata (`name`, `symbol`, `decimals`), and a human-readable `valueWithDecimals`. Transfers appear in both confirmed and unconfirmed payloads.

    ```javascript expandable theme={null}
    {
      "confirmed": false,
      "chainId": "0x5",
      "streamId": "c4cf9b1a-0cb3-4c79-9ca3-04f11856c555",
      "tag": "ChrisWallet",
      "retries": 0,
      "block": {
        "number": "8037952",
        "hash": "0x607ff512f17f890bf9ee6206e2029cd8530819ab72b2b9161f9b90d18ece8e03",
        "timestamp": "1669667244"
      },
      "logs": [ /* ... raw Transfer log ... */ ],
      "txs": [ /* ... underlying tx ... */ ],
      "txsInternal": [],
      "erc20Transfers": [
        {
          "transactionHash": "0x1642a3b9b39e63d7fe571e7c22b80a5b059d2647fe4866d3f7105630f822d833",
          "logIndex": "132",
          "contract": "0x0041ebd11f598305d401cc1052df49219630ab79",
          "from": "0x0a46413965858a6ac4ed5184d7643dc055a4fea3",
          "to": "0xe496601436da37a045d8e88bbd6b2c2e17d8fe33",
          "value": "499999000000000000000000",
          "tokenName": "Example Token",
          "tokenSymbol": "Token",
          "tokenDecimals": "18",
          "possibleSpam": false,
          "valueWithDecimals": "499999"
        }
      ],
      "erc20Approvals": [],
      "nftApprovals": { "ERC1155": [], "ERC721": [] },
      "nftTransfers": []
    }
    ```

    ### ERC-20 Approvals

    ERC-20 approvals are also automatically decoded and include owner and spender, approved amount, and token metadata.

    ```javascript expandable theme={null}
    {
      "erc20Approvals": [
        {
          "transactionHash": "0x59cd370a41c699bdb77a020b3a27735bb7442ace68ec8313040b8b9ee2672244",
          "logIndex": "135",
          "contract": "0x96beaa1316f85fd679ec49e5a63dacc293b044be",
          "owner": "0x1748789703159580520cc2ce6d1ba01e7359c44c",
          "spender": "0x1111111254eeb25477b68fb85ed929f73a960582",
          "value": "115792089237316195423570985008687907853269984665640564039457584007913129639935",
          "tokenName": "This Is Not Alpha",
          "tokenSymbol": "TINA",
          "tokenDecimals": "18",
          "valueWithDecimals": "1.15792...e+59"
        }
      ]
    }
    ```

    ### NFT Transfers

    NFT transfers are automatically decoded for both ERC-721 and ERC-1155 tokens. Each NFT transfer includes:

    * `tokenName`: the name of the NFT
    * `tokenSymbol`: the symbol of the NFT (only for [ERC721](https://eips.ethereum.org/EIPS/eip-721))
    * `tokenContractType`: the type of the NFT (either [ERC721](https://eips.ethereum.org/EIPS/eip-721) or [ERC1155](https://eips.ethereum.org/EIPS/eip-1155))
    * `to`: the receiver address of the NFT transfer
    * `from`: the sender address of the NFT transfer
    * `amount`: the amount of NFT transferred (`1` for ERC-721)
    * `transactionHash`: the transaction hash of the NFT transfer
    * `tokenId`: the token ID of the NFT transferred
    * `operator`: a third-party address approved to manage NFTs owned by `from` (see [EIP-1155](https://eips.ethereum.org/EIPS/eip-1155))
    * `contract`: the contract address of the NFT transferred

    ```javascript expandable theme={null}
    {
      "nftTransfers": [
        {
          "operator": null,
          "from": "0x74f64bebb1a9615fc7c2ead9c894b6ffd1803582",
          "to": "0xe496601436da37a045d8e88bbd6b2c2e17d8fe33",
          "tokenId": "0",
          "amount": "1",
          "transactionHash": "0x5ecd6b57593ab2f4f3e39fbb3318a3933e2cf9fdcf5b7ca671fb0fc2ce9dc4b5",
          "logIndex": "72",
          "contract": "0x26b4e79bca1a550ab26a8e533be97c40973b2671",
          "possibleSpam": false,
          "tokenName": "Test",
          "tokenSymbol": "SYMBOL",
          "tokenContractType": "ERC721"
        }
      ]
    }
    ```

    ### NFT Approvals

    Approval events for ERC-721 and ERC-1155 tokens are grouped under `nftApprovals` and decoded automatically.

    ### Smart Contract Events Only

    If you configure a stream to listen only to specific contract events:

    * Only `logs` will be populated
    * ABI decoding is applied using the ABI you provide
    * No token or transaction arrays are included unless explicitly enabled

    ```javascript expandable theme={null}
    {
      "confirmed": false,
      "chainId": "0x1",
      "abi": [
        {
          "anonymous": false,
          "inputs": [
            { "indexed": false, "name": "reserve0", "type": "uint112" },
            { "indexed": false, "name": "reserve1", "type": "uint112" }
          ],
          "name": "Sync",
          "type": "event"
        }
      ],
      "streamId": "6378fe38-54c7-4816-8d61-fca8e128e260",
      "tag": "test_events",
      "retries": 1,
      "block": { /* ... */ },
      "logs": [ /* ... matching Sync logs ... */ ],
      "txs": [],
      "txsInternal": [],
      "erc20Transfers": [],
      "erc20Approvals": [],
      "nftApprovals": { "ERC1155": [], "ERC721": [] },
      "nftTransfers": []
    }
    ```

    ### Internal Transactions (`txsInternal`)

    Internal transactions represent value transfers occurring **inside contract execution**. Included when `includeInternalTxs` is enabled. Useful for DeFi protocol tracing, internal fund movement, and advanced analytics.

    ```javascript expandable theme={null}
    {
      "txsInternal": [
        {
          "from": "0x1111111254eeb25477b68fb85ed929f73a960582",
          "to": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
          "value": "11000000000000000",
          "gas": "117885",
          "transactionHash": "0x0e5c3114c0ee7d29cca17aa0b8e790c4d7d25b4789bd14150f113956b5ce94de"
        }
      ]
    }
    ```
  </Tab>

  <Tab title="Bitcoin">
    ### Block metadata

    Each Bitcoin payload begins with the block the matched transaction was included in:

    * `hash` — block hash
    * `height` — block height
    * `timestamp` — Unix timestamp
    * `difficulty` — block difficulty
    * `merkleRoot` — merkle root of transactions in the block
    * `txCount` — number of transactions in the block

    ### Matched transactions (`txs`)

    Each matched transaction includes:

    * `txid` — Bitcoin transaction id (the natural deduplication key)
    * `version` — transaction version
    * `locktime` — earliest time the transaction can be mined
    * `vin` — array of inputs (structural fields only — see warning below)
    * `vout` — array of outputs

    Each `vout` entry has:

    * `n` — output index
    * `value` — output value as a **BTC decimal** (e.g. `3.13258866`)
    * `scriptPubKey.address` — recipient address (P2PKH `1...`, P2SH `3...`, or Bech32 `bc1q...`)
    * `scriptPubKey.type` — script type (e.g. `witness_v0_keyhash`)

    <Warning>
      Even with `includeInputs: true`, the `address` and `value` fields on `vin` entries return `null`. You can reliably detect **inbound** activity to watched addresses, not outflows.
    </Warning>

    ### Confirmation phases

    A matched transaction generates **two** webhook deliveries:

    1. **First delivery (near-tip)** — `confirmed: false`, sent when the matching transaction is included in a block. The block is close to the chain tip and could still be reorged.
    2. **Second delivery (reorg-safe)** — `confirmed: true`, sent after 2 additional blocks have been mined on top. Moralis re-fetches the block and treats the transaction as final.

    Use `txid` as your dedupe key and upsert on the second delivery to flip your local confirmation flag.

    ### Coinbase detection

    `isCoinbase` is unreliable. Detect coinbase transactions with this heuristic:

    ```js theme={null}
    const isCoinbase =
      tx.vin.length === 1 &&
      tx.vout.some((out) => out.scriptPubKey?.type === "nulldata"); // OP_RETURN
    ```

    ### Value conversion

    Convert BTC decimals to satoshis before feeding integer-based ledgers:

    ```js theme={null}
    const btc = vout.value;
    const satoshis = Math.round(btc * 1e8);
    ```

    For full background, see [Bitcoin Streams](/streams/bitcoin-streams).
  </Tab>

  <Tab title="Solana">
    ### Block metadata

    Each Solana payload begins with the block the matched transaction belongs to:

    * `slot` — Solana's time unit (most slots produce a block; some are skipped)
    * `blockHash` — base58 block hash
    * `blockHeight` — block height
    * `blockTime` — Unix timestamp
    * `parentSlot`, `previousBlockHash` — chain links

    ### Matched transactions (`transactions`)

    Each matched transaction includes:

    * `signature` — base58-encoded transaction id (used to look up the transaction)
    * `slot` — slot the transaction was processed in
    * `blockTime` — Unix timestamp
    * `fee` — fee in lamports
    * `err` — `null` on success, error object otherwise
    * `accountKeys` — every account the transaction touches (signers, recipients, programs, reads, writes)
    * `instructions` — top-level instructions
    * `innerInstructions` — nested instructions emitted via Cross-Program Invocations (CPIs)
    * `preTokenBalances` / `postTokenBalances` — SPL balance snapshots for the affected accounts before and after the transaction

    <Warning>
      Solana addresses are base58 and **case-sensitive**. Submit them in their original case — unlike EVM, lowercased addresses will not match.
    </Warning>

    ### How filters interact with the payload

    * `addresses` matches against `accountKeys` — a single Solana transaction can match multiple watched addresses.
    * `programIds` matches against the program invoked by an instruction.
    * `mintAddresses` matches via `pre` / `postTokenBalances`.

    ### Computing token deltas

    Subtract `preTokenBalances` from `postTokenBalances` for the accounts you care about — no instruction replay required.

    ### Inner instructions

    Each top-level instruction can trigger inner instructions when one program calls another (CPIs). The webhook includes both, so you can trace nested behavior directly.

    For full background and the bridge from EVM concepts (smart contracts, ERC-20, transaction hash) to Solana concepts (programs, mint addresses, signature), see [Solana Streams](/streams/solana-streams).
  </Tab>
</Tabs>

***

## Retry Metadata

If a webhook delivery fails:

* `retries` increments
* The event is retried automatically
* Failed deliveries are retained for replay (plan-dependent)

See [Retries & Replays](/streams/webhooks/retries-and-replays) for full recovery behavior.

***

## Common Next Steps

Depending on what you're building:

* Need cleaner decoded data? Explore [Parsed Data](/streams/streams-concepts/parsed-data)
* Need fine-grained filtering? Explore [Filters](/streams/streams-concepts/filters)
* Need on-chain lookups inside webhooks (EVM only)? Explore [Triggers](/streams/streams-concepts/triggers)
* Handling high throughput? Explore [Rate Limits](/streams/streams-concepts/rate-limits)
