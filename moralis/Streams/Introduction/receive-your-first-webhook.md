> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Receive Your First Webhook

> Understand the webhook lifecycle, payload structure, and how to handle confirmed and unconfirmed webhooks from Moralis Streams.

Once your stream is active, Moralis will send webhook `POST` requests to your configured URL whenever monitored addresses are involved in on-chain events.

## Mandatory Test Webhook

Whenever you create or update a stream, you will receive a **test webhook**. You must return a `200` status code (or any `2xx` code) for the stream to start delivering real data.

The test body looks like this:

```json theme={null}
{
  "abi": {},
  "block": {
    "hash": "",
    "number": "",
    "timestamp": ""
  },
  "txs": [],
  "txsInternal": [],
  "logs": [],
  "chainId": "",
  "tag": "",
  "streamId": "",
  "confirmed": true,
  "retries": 0,
  "erc20Approvals": [],
  "erc20Transfers": [],
  "nftApprovals": [],
  "nftTransfers": []
}
```

<Note>No response body is required — only the status code matters. See [Test Webhooks](/streams/webhooks/test-webhooks) for more details.</Note>

## Two Webhooks Per Event

You will receive **two webhooks** for each event:

1. **Unconfirmed** (`confirmed: false`) — Sent as soon as the transaction is included in a block. The block may still be dropped due to a chain reorganization. You are **not charged** for unconfirmed webhooks.

2. **Confirmed** (`confirmed: true`) — Sent once enough blocks have been mined to consider the block final. Only confirmed webhooks count toward your [billing](/streams/pricing).

<Warning>In rare cases, the confirmed webhook may arrive before the unconfirmed one. Make sure your application handles this scenario.</Warning>

## Webhook Payload Structure

The webhook body contains all the data for the block event. The key fields are:

| Field            | Description                                      |
| ---------------- | ------------------------------------------------ |
| `chainId`        | The chain ID (e.g., `0x1` for Ethereum)          |
| `block`          | Block metadata (number, hash, timestamp)         |
| `txs`            | Array of native transactions                     |
| `txsInternal`    | Array of internal transactions                   |
| `logs`           | Array of raw event logs                          |
| `erc20Transfers` | Decoded ERC20 transfer events (free)             |
| `erc20Approvals` | Decoded ERC20 approval events (free)             |
| `nftTransfers`   | Decoded NFT transfer events (free)               |
| `nftApprovals`   | Decoded NFT approval events (free)               |
| `tag`            | Your user-defined stream tag                     |
| `streamId`       | The ID of the stream that triggered this webhook |
| `confirmed`      | Whether the block is confirmed                   |
| `retries`        | Number of delivery retries                       |

## Example: Native Transaction Webhook

```json theme={null}
{
  "confirmed": false,
  "chainId": "0x1",
  "abi": [],
  "streamId": "c28d9e2e-ae9d-4fe6-9fc0-5fcde2dcdd17",
  "tag": "my_stream",
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
      "input": "0x...",
      "transactionIndex": "52",
      "fromAddress": "0x839d4641f97153b0ff26ab837860c479e2bd0242",
      "toAddress": "0x1111111254eeb25477b68fb85ed929f73a960582",
      "value": "0",
      "type": "2",
      "receiptCumulativeGasUsed": "3131649",
      "receiptGasUsed": "113816",
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

## Verifying Webhook Signatures

Every webhook includes an `x-signature` header — a SHA3 hash of the body combined with your API key. Always verify this signature to ensure the webhook is from Moralis.

<Tabs>
  <Tab title="JavaScript">
    ```javascript theme={null}
    import Moralis from "moralis";

    const { headers, body } = request;

    Moralis.Streams.verifySignature({
      body,
      signature: headers["x-signature"],
    }); // throws error if not valid
    ```
  </Tab>

  <Tab title="Python">
    ```python theme={null}
    from web3 import Web3

    def verify_signature(req, secret):
        provided_signature = req.headers.get("x-signature")
        if not provided_signature:
            raise TypeError("Signature not provided")

        data = req.data + secret.encode()
        signature = Web3.keccak(text=data.decode()).hex()

        if provided_signature != signature:
            raise ValueError("Invalid Signature")
    ```
  </Tab>
</Tabs>

For full details, see [Webhook Security](/streams/security-and-reliability/webhook-security).

## Decoded Data (Free)

Moralis automatically decodes standard contract events at no additional cost:

* **ERC20 Transfers** — Includes `tokenName`, `tokenSymbol`, `tokenDecimals`, `from`, `to`, `value`, and `contract` address.
* **ERC20 Approvals** — Includes `owner`, `spender`, `value`, and token metadata.
* **NFT Transfers** — Includes `tokenId`, `tokenName`, `tokenContractType` (ERC721/ERC1155), `from`, `to`, `amount`, and `contract` address.

These decoded fields are included in both confirmed and unconfirmed payloads and do **not** count as records for billing purposes.

## Next Steps

* [Webhook Payloads](/streams/webhooks/webhook-payloads) — Detailed reference for all payload types.
* [Confirmation and Finality](/streams/webhooks/confirmation-and-finality) — How block confirmations work across chains.
* [Pricing](/streams/pricing) — Understand how records and compute units are calculated.
