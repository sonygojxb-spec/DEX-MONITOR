> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Datashare Supported Data

> Data types available through Moralis Datashare for bulk historical exports.

### Supported Data Types

Moralis Datashare provides access to two categories of blockchain data: **decoded data** with enriched, human-readable information, and **raw data** for lower-level blockchain primitives.

***

## Decoded Data

Decoded data is processed and enriched blockchain data that has been parsed, labeled, and normalized for easier analysis. These datasets include contextual information such as token metadata, event types, and standardized schemas.

| Data Type            | Description                                                                                   |
| -------------------- | --------------------------------------------------------------------------------------------- |
| **Liquidity Events** | DEX liquidity pool additions and removals, including pool addresses, token pairs, and amounts |
| **Native Transfers** | Transfers of native blockchain currencies (ETH, MATIC, BNB, etc.) between addresses           |
| **NFT Transfers**    | ERC-721 and ERC-1155 token transfers with collection metadata and token IDs                   |
| **Swap Events**      | DEX swap transactions including input/output tokens, amounts, and exchange rates              |
| **Token Transfers**  | ERC-20 token transfers with token metadata, amounts, and decimal normalization                |

***

## Raw Data

Raw data provides direct access to blockchain primitives as they exist on-chain. These datasets are useful for custom parsing, low-level analysis, or when you need complete blockchain state data.

| Data Type                 | Description                                                                               |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| **Blocks**                | Block headers including timestamps, gas limits, miner/validator info, and block hashes    |
| **Transactions**          | Complete transaction data including sender, recipient, value, gas, input data, and status |
| **Internal Transactions** | Trace-level internal calls and value transfers within transaction execution               |
| **Logs**                  | Event logs emitted by smart contracts, including topics and raw data fields               |

***

### Field Selection

When creating an export, you can select specific fields from each dataset. More fields increase export size and GB consumption proportionally — start with the minimum fields you actually need.

<Warning>
  DataShare exports raw on-chain data. Token names, symbols, logos, spam labels, and metadata enrichment are **not included**. Plan for separate metadata enrichment post-export if needed.
</Warning>

***

### Data Availability

Data availability varies by chain. See the [Supported Chains](/datashare/supported-chains) page for a complete breakdown of which data types are available for each blockchain.
