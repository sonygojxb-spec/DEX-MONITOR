> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# NFT Marketplace

> A Data Feeds recipe bundle for NFT marketplaces and analytics platforms — collection trade history, current ownership, wallet inventories, and collection metadata, synced into your own database.

### Who it's for

Teams building **NFT marketplaces, collection explorers, and NFT analytics** platforms — anything that needs sale history, current ownership, and per-wallet inventories without polling an API per page view. The output is your own set of tables: every marketplace trade, the live owner of every token, what each wallet holds, and the collection metadata to label it all.

### The recipe bundle

This use case combines a handful of recipes. Start with **NFT Trades** for sale history, layer **NFT Owners by Contract** and **NFTs by Wallet** for the two ownership views, and add **NFT Collection Metadata** to label collections. Drop down to **NFT Transfers** when you need the raw movement feed under the trades.

| Recipe                                                                     | Role in this use case                                                                                                                                                     |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [NFT Trades](/data-feeds/recipes/nft/nft-trades)                           | The sale feed — every marketplace trade (seller, buyer, collection, token ID, price, marketplace) by collection, by single token, or by wallet as seller/buyer.           |
| [NFT Owners by Contract](/data-feeds/recipes/nft/nft-owners-by-contract)   | Current owners of a collection — the latest non-zero holding per `(token_id, wallet)`. The holder list and floor/holder analytics base.                                   |
| [NFTs by Wallet](/data-feeds/recipes/wallet/nfts-by-wallet)                | A wallet's NFT inventory — every token a wallet currently holds, keyed by `(wallet, token_address, token_id)`.                                                            |
| [NFT Collection Metadata](/data-feeds/recipes/nft/nft-collection-metadata) | Collection-level metadata (name, symbol, ERC-721/1155 type, deployer) to label collections across every other table.                                                      |
| [NFT Transfers](/data-feeds/recipes/nft/nft-transfers)                     | The raw movement feed — every NFT transfer (mints, burns, plain sends, and the transfer legs of trades). Provenance and the substrate the ownership views are built from. |

<Note>
  **Trades and transfers are different feeds.** NFT Transfers is *every* movement of a token — mints, gifts, wallet-to-wallet sends, and the transfer leg of a marketplace sale. NFT Trades is the subset that settled through a marketplace, re-assembled with seller, buyer, price, and the marketplace address. Use Trades for sale history and volume; use Transfers for full provenance and to drive ownership.
</Note>

### How the pieces fit

```
                          NFT Collection Metadata
                            (labels everything)
                                   │
NFT Transfers ──► NFT Owners by Contract  (owners of a collection)
   (movements)└─► NFTs by Wallet          (a wallet's inventory)

NFT Trades ─────► sale history · volume · floor / last-sale
```

* **NFT Transfers** is the substrate: every `(token_address, token_id)` movement, in on-chain order. The two ownership views are the same ingest sorted two ways — **NFT Owners by Contract** keys on `(token_address, token_id, wallet)` to answer "who owns this collection," and **NFTs by Wallet** keys on `(wallet, token_address, token_id)` to answer "what does this wallet hold."
* **NFT Trades** is the marketplace-settled subset, enriched with seller, buyer, price, and marketplace address — the feed behind sale history, volume charts, and last-sale prices.
* **NFT Collection Metadata** is the label layer: join `token_address` to attach a collection's name, symbol, and contract type to any trade, holding, or transfer row.

### Building a collection dashboard

A typical collection page needs sale history and the current holder set, labeled with collection metadata. The trades feed answers sale history and volume directly:

```sql theme={null}
-- Recent sales for a collection, newest first.
SELECT  t.block_number,
        t.token_id,
        t.seller_address,
        t.buyer_address,
        t.price,
        t.price_token_address,
        t.marketplace_address,
        t.tx_hash
FROM    recipe_nft_trades.fact_nft_trades AS t FINAL
WHERE   t.chain_id = 1
  AND   t.token_address = lower('0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D')
ORDER BY t.block_number DESC
LIMIT 50;
```

The current holder set comes from the ownership view — read the latest non-zero holding per `(token_id, wallet)` with a sign-aware aggregate over `FINAL`:

```sql theme={null}
-- Current owners of a collection (latest non-zero holding per token_id + wallet).
SELECT  token_id,
        wallet_address,
        argMax(contract_type, (block_number, log_index)) AS contract_type,
        argMax(amount,        (block_number, log_index)) AS current_amount
FROM    recipe_nft_owners_by_contract.fact_nft_owners_by_contract FINAL
WHERE   chain_id = 1
  AND   token_address = lower('0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D')
GROUP BY token_id, wallet_address
HAVING  current_amount != '0' AND current_amount != ''
ORDER BY token_id, wallet_address;
```

Label either result with a collection row from the metadata sync (latest deploy wins, defensive against CREATE2 re-deploys):

```sql theme={null}
SELECT  token_address,
        argMax(name,          (block_number, transaction_index)) AS name,
        argMax(symbol,        (block_number, transaction_index)) AS symbol,
        argMax(contract_type, (block_number, transaction_index)) AS contract_type
FROM    recipe_nft_collection_metadata.fact_nft_collection_metadata FINAL
WHERE   chain_id = 1
  AND   token_address = lower('0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D')
GROUP BY token_address;
```

### Notes and considerations

* **Read canonical state correctly.** ClickHouse recipes use the collapsing log-table pattern. Read with `FINAL` or a sign-aware aggregate (`argMax` over the latest `(block_number, log_index)`) — never a bare `WHERE sign = 1`, which double-counts reorged rows.
* **No off-chain enrichment.** The trade and transfer arrays carry no marketplace human-name, no USD price, and no address labels. `price` is in `price_token_address` units; value it in USD by joining a Token Prices sync, and resolve marketplace/address names in your own application.
* **Ownership = current state.** NFT Owners by Contract and NFTs by Wallet keep the *latest* holding per key; filter to non-zero amounts to drop wallets that transferred out. For full history, read NFT Transfers or NFT Trades directly.
* **ERC-721 vs ERC-1155.** `contract_type` carries the discriminator. ERC-1155 `amount` can exceed 1 per `(token_id, wallet)`; raw `uint256` amounts are stored as text — compare against `'0'`, don't assume a single-owner-per-token model.
* **Chains.** NFT Trades, Transfers, Owners by Contract, NFTs by Wallet, and Collection Metadata are chain-parametrized — point them at any supported EVM chain or Solana. Solana marketplace trades (Magic Eden, Tensor, and others) populate the same trade shape; trade identity is widened with `(seller, buyer, token_address, token_id)` to keep rows distinct where one instruction shares a `log_index`.
* **Scale and live tailing.** Run the ClickHouse path in `hybrid` mode to backfill collection history and then stay current, reorg-safe, at the chain head. For a chain-wide view across many collections, the by-collection and by-token-id prefixes keep reads scoped.
* **Pair with other recipes.** Add [Token Prices](/data-feeds/recipes/token/token-prices) to value trades in USD, and [Wallet History](/data-feeds/recipes/wallet/wallet-history) for a per-wallet feed that already folds NFT transfers in alongside tokens and swaps.

### Get started

Data Feeds is in early access.

<Card title="Request Early Access" icon="rocket" href="/data-feeds/early-access">
  Build NFT marketplace and analytics data into your own infrastructure with the Moralis team.
</Card>
