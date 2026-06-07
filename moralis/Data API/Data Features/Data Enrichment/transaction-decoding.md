> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Transaction Decoding

> Moralis enriches raw blockchain transactions with human-readable meaning, making it easier to understand what actually happened onchain.

Instead of working with low-level logs and method calls, you get **decoded actions, labels, and categories** that describe wallet activity in a clear, consistent way.

***

## What This Includes

Transaction decoding and enrichment combines two core capabilities:

* **Wallet activity categorisation** (what type of action occurred)
* **ABI-based decoding and labelling** (what the transaction did at a contract level)

Together, these form Moralis’ **semantic transaction layer**.

***

## Wallet Activity Decoding

Moralis can return a **single, chronological view of a wallet’s onchain activity**, covering all major transaction types.

This includes:

* Native transfers
* ERC20 swaps and token transfers
* NFT transfers and sales
* DeFi interactions
* Smart contract interactions

All activity is normalized into a consistent timeline, removing the need to aggregate multiple endpoints or data sources.

### Key Benefits

* **Single API request**\
  Fetch a complete wallet history in one call.
* **Automatic categorisation**\
  Each transaction is classified into a clear, human-readable category.
* **Reduced complexity**\
  No need to manually decode logs, traces, or contract calls.
* **Consistent ordering**\
  Transactions are returned in a clean, chronological format.

***

## Transaction Categories

Each transaction is assigned a category based on its onchain behavior.

Currently supported categories include:

* Send
* Receive
* Token Send
* Token Receive
* NFT Send
* NFT Receive
* Deposit
* Withdraw
* Token Swap
* Airdrop
* Mint
* Burn
* NFT Purchase
* NFT Sale
* Borrow
* Approve
* Revoke
* Contract Interaction

<Note>
  Category support is continuously expanding as new transaction patterns and protocols are added.
</Note>

***

## ABI Decoding & Transaction Labelling

Beyond high-level categories, Moralis also decodes transactions at the **contract interaction level**.

Using verified ABIs and internal decoding logic, Moralis:

* Decodes method calls
* Interprets parameters
* Assigns meaningful **labels** to transactions

This allows you to distinguish between different contract interactions even when they fall under the same high-level category.

***

## Why This Matters

Transaction decoding and enrichment enables you to:

* Build readable wallet activity feeds
* Show users *what they actually did* onchain
* Power analytics, notifications, and alerts
* Avoid custom ABI decoding and protocol-specific logic
* Deliver consistent UX across chains and protocols

This is especially valuable for:

* Wallets and portfolio trackers
* Analytics dashboards
* Tax and accounting tools
* Compliance and monitoring systems

***

## Important Notes

* Decoding and categorisation are **best-effort** and based on available onchain data and ABIs
* Unknown or unverified contracts may fall back to generic labels (e.g. `Contract Interaction`)
* New transactions occurring during pagination will not affect already-decoded results (see Pagination)
