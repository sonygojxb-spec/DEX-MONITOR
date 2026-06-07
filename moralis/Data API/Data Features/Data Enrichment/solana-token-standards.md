> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Solana Token Standards

> Understand the Solana token standards supported by Moralis, including the SPL Token Program and Metaplex metadata standard.

Solana uses a different token model than EVM chains. Instead of each token deploying its own smart contract, all tokens are managed by shared **token programs**. Moralis supports the major Solana token standards and enriches API responses with decoded metadata.

***

## Token Programs

### SPL Token Program

The original **SPL Token Program** is the standard for fungible and non-fungible tokens on Solana. Most tokens on Solana — including SOL-wrapped tokens, stablecoins, and meme coins — use this program.

Key characteristics:

* Tokens are identified by their **mint address**
* Each holder has an **associated token account** (ATA) linked to their wallet
* Token metadata (name, symbol, logo) is stored offchain via the **Metaplex** standard

## Metaplex Metadata Standard

Most Solana tokens and NFTs use the **Metaplex** metadata standard to store human-readable information (name, symbol, image, attributes) offchain. The `standard` field in Moralis API responses indicates when a token follows this standard.

When Moralis returns `"standard": "metaplex"`, the response includes a `metaplex` object:

```json theme={null}
{
  "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
  "standard": "metaplex",
  "name": "Fartcoin",
  "symbol": "Fartcoin",
  "metaplex": {
    "metadataUri": "https://ipfs.io/ipfs/QmYfe8zVGHA1heej47AkBX3Nnetg2h2kqj5yymz1xyKeHb",
    "masterEdition": false,
    "isMutable": false,
    "sellerFeeBasisPoints": 0,
    "updateAuthority": "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM",
    "primarySaleHappened": 0
  }
}
```

### Metaplex fields explained

| Field                  | Description                                                    |
| ---------------------- | -------------------------------------------------------------- |
| `metadataUri`          | URI pointing to the full metadata JSON (often IPFS or Arweave) |
| `updateAuthority`      | The address that can modify the token's metadata               |
| `sellerFeeBasisPoints` | Creator royalty on secondary sales (100 = 1%)                  |
| `primarySaleHappened`  | Whether the initial sale has occurred                          |
| `isMutable`            | Whether the metadata can still be updated                      |
| `masterEdition`        | Whether this is a master edition NFT                           |

***

## NFTs on Solana

Unlike EVM chains where NFTs are grouped under a single contract, each Solana NFT is represented by a **unique mint address**. Moralis returns rich NFT metadata including:

* **Collection data** — `collectionAddress`, collection name, description, and verification status
* **Attributes** — Trait types and values (e.g., `"traitType": "Gender", "value": "Male"`)
* **Creator information** — Addresses, share percentages, and verification status
* **Media previews** — Low, medium, and high resolution image URLs via Moralis CDN

Example NFT metadata:

```json theme={null}
{
  "address": "FVzM6rUA1SigPxh6e3iQ8dAPjQNf2guap3Xcdj8Q6R2H",
  "standard": "metaplex",
  "name": "Mad Lads #7256",
  "symbol": "MAD",
  "metaplex": {
    "metadataUri": "https://madlads.s3.us-west-2.amazonaws.com/json/7256.json",
    "updateAuthority": "2RtGg6fsFiiF1EQzHqbd66AhW7R5bWeQGpTbv2UMkCdW",
    "sellerFeeBasisPoints": 420,
    "primarySaleHappened": 1,
    "isMutable": true,
    "masterEdition": false
  },
  "collection": {
    "collectionAddress": "J1S9H3QjnRtBbbuD4HjPV6RpRhwuk4zKbxsnCHuTgh9w",
    "name": "Mad Lads",
    "description": "Fock it.",
    "metaplexMint": "J1S9H3QjnRtBbbuD4HjPV6RpRhwuk4zKbxsnCHuTgh9w",
    "sellerFeeBasisPoints": 500
  },
  "creators": [
    {
      "address": "5XvhfmRjwXkGp3jHGmaKpqeerNYjkuZZBYLVQYdeVcRv",
      "share": 0,
      "verified": true
    },
    {
      "address": "2RtGg6fsFiiF1EQzHqbd66AhW7R5bWeQGpTbv2UMkCdW",
      "share": 100,
      "verified": true
    }
  ]
}
```

<Info>Some NFTs may lack a `collectionAddress` or other metadata fields. You can identify Metaplex-standard NFTs by the presence of a `metaplexMint` value.</Info>

***

## How Moralis Uses These Standards

Moralis automatically detects the token standard and enriches responses accordingly:

* **Fungible tokens** — Returns mint address, name, symbol, decimals, supply, logo, and market data (price, FDV)
* **NFTs** — Returns full Metaplex metadata, collection info, creator details, attributes, and media previews
* **Token balances** — Includes associated token account addresses and formatted amounts

The `standard` field in API responses tells you which metadata standard a token uses (currently `"metaplex"` for most Solana tokens).

***

## Related Pages

* [Token Metadata](/data-api/data-features/data-enrichment/token-metadata) — EVM token metadata enrichment
* [NFT Metadata](/data-api/data-features/data-enrichment/nft-metadata) — NFT metadata across chains
