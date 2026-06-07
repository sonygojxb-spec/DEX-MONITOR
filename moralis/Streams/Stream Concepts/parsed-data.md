> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Parsed Data

> Learn how to extract typed, decoded data from Streams webhooks across EVM (ERC-20 / NFT transfers, contract events), Bitcoin (UTXO outputs), and Solana (SPL balance snapshots, instructions).

## Overview

Moralis Streams makes it easy to work with webhook payloads by providing **parsed, structured data** for common on-chain activity. The data Moralis parses for you depends on the chain.

<Tabs>
  <Tab title="EVM">
    On EVM, Moralis includes ready-to-use parsed sections such as:

    * **Transactions** (`txs`)
    * **Internal transactions** (`txsInternal`)
    * **ERC-20 transfers** (`erc20Transfers`)
    * **ERC-20 approvals** (`erc20Approvals`)
    * **NFT transfers** (`nftTransfers`)
    * **NFT approvals** (`nftApprovals`)
    * **Custom smart contract events**, decoded using your ABI

    This avoids manually decoding logs and building your own parsing pipeline.

    Example payload shape:

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

    Learn more about [EVM Webhook Payloads](/streams/webhooks/webhook-payloads).
  </Tab>

  <Tab title="Bitcoin">
    On Bitcoin, each matched transaction comes with parsed UTXO-level fields:

    * **Block metadata** — hash, height, timestamp, difficulty, merkle root, transaction count
    * **Transaction details** — `txid`, `version`, `locktime`, input/output counts
    * **Outputs (`vout`)** — value in BTC (not satoshis), `scriptPubKey.address` (recipient), `scriptPubKey.type`
    * **Inputs (`vin`)** — structural fields only (`address` and `value` are always `null`)

    Output recipient addresses are already parsed and matched against your watched addresses (or addresses derived from a registered xpub) — no additional decoding required.

    <Warning>
      `vin` entries do not include populated `address` or `value` fields, even with `includeInputs: true`. You can reliably detect **inbound** transfers; outflows require additional lookup. See [Bitcoin Streams](/streams/bitcoin-streams).
    </Warning>

    Output values are BTC decimals — convert to satoshis with `Math.round(btc * 1e8)`.
  </Tab>

  <Tab title="Solana">
    On Solana, every matched transaction comes with parsed snapshots that make instruction-level replay unnecessary for most use cases:

    * **`accountKeys`** — every account the transaction touches (signers, recipients, programs, reads, writes)
    * **`instructions`** — top-level instructions with their `programId` and accounts
    * **`innerInstructions`** — nested instructions emitted via Cross-Program Invocations (CPIs)
    * **`preTokenBalances` / `postTokenBalances`** — SPL token balance snapshots before and after the transaction

    To compute SPL token deltas, subtract `preTokenBalances` from `postTokenBalances` for the accounts you care about — no instruction replay required.

    <Warning>
      Solana addresses are base58 and **case-sensitive**. Submit them in their original case — unlike EVM, lowercased addresses will not match.
    </Warning>

    Learn more about [Solana Streams](/streams/solana-streams).
  </Tab>
</Tabs>

***

## Parsing Smart Contract Events (EVM)

<Note>
  Custom-event ABI decoding is an EVM-only feature. Bitcoin and Solana payloads are pre-parsed into their native shapes and do not require ABI decoding.
</Note>

If you are streaming a smart contract event on EVM, you can decode the logs from the webhook into a typed structure.

```javascript theme={null}
import Moralis from "moralis";
import { BigNumber } from "@moralisweb3/core";

interface URI {
  value: string;
  id: BigNumber;
}

const webhookData = {
  confirmed: true,
  chainId: "0x1",
  abi: [
    {
      anonymous: false,
      inputs: [
        { indexed: false, internalType: "string", name: "value", type: "string" },
        { indexed: true, internalType: "uint256", name: "id", type: "uint256" },
      ],
      name: "URI",
      type: "event",
    },
  ],
  logs: [
    {
      logIndex: "475",
      transactionHash:
        "0x55125fa34ce16c295c222d48fc3efe210864dc2fb017f5965b4e3743d72342d5",
      address: "0x495f947276749ce646f68ac8c248420045cb7b5e",
      data: "0x0000000000000000000000000000000000000000000000000000000000000020...",
      topic0:
        "0x6bb7ff708619ba0610cba295a58592e0451dee2622938c8755667688daf3529b",
      topic1:
        "0xab6953e647a36018fc48d6223583597b84c755a0000000000000010000000001",
      topic2: null,
      topic3: null,
    },
  ],
  erc20Transfers: [],
  erc20Approvals: [],
  nftApprovals: { ERC1155: [], ERC721: [] },
  nftTransfers: [],
};

const decodedLogs = Moralis.Streams.parsedLogs<URI>(webhookData);

console.log(decodedLogs[0].value);
console.log(decodedLogs[0].id.toString());
```

***

## Notes

* On EVM, prefer the dedicated parsed arrays (`erc20Transfers`, `nftTransfers`, etc.) over decoding raw logs yourself.
* On EVM, custom-event decoding relies on the ABI you configure for the stream — raw logs remain available in the payload alongside parsed data.
* On Bitcoin, output addresses and values are already parsed; no decoding step is needed.
* On Solana, account keys, instructions, and SPL balance snapshots are already parsed; subtract pre/post token balances to derive deltas.
