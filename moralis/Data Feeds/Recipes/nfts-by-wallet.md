> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# NFTs by Wallet

> Sync every NFT a wallet currently holds — collection, token ID, contract type, and balance — as a continuously updated holdings table in your own database. Mirrors the Moralis GET /{address}/nft endpoint.

### Question it answers

> "Give me every NFT wallet **0x…** currently holds — each row is a `(collection, token_id)` it owns, with the ERC-721/ERC-1155 contract type and current balance."

Mirrors Moralis `GET /{address}/nft`. It's the NFT-keyed sibling of [Token Balances by Wallet](/data-feeds/recipes/wallet/token-balances-by-wallet) — the same observation/latest-wins pattern, but sourced from NFT transfers and keyed on `(wallet, token_address, token_id)` instead of `(wallet, token_address)`.

### What you get

The recipe lands **NFT holding observations**, then the current holding is the latest non-zero observation per `(wallet, token_address, token_id)`. Each NFT transfer carries the **absolute post-transfer holdings** of each side (`from`/`to`), so the recipe never has to sum a running balance — the latest observation *is* the balance.

| Column                         | Description                                                                                                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `wallet_address`               | The holder (the `from` or `to` side of a transfer)                                                            |
| `token_address`                | The NFT contract (collection)                                                                                 |
| `token_id`                     | The NFT identifier — a `uint256`, stored as text (it exceeds numeric precision)                               |
| `contract_type`                | `ERC721` or `ERC1155` discriminator (from the transfer's token type)                                          |
| `balance`                      | Absolute post-transfer holding of this `token_id` for this wallet (`1`/`0` for ERC-721, a count for ERC-1155) |
| `block_number`, `log_index`    | Ordering tuple — the latest pair wins as the current holding                                                  |
| `event_ts` / `block_timestamp` | Block time                                                                                                    |

The EVM zero address (`0x0000…0000`) is a mint/burn counterparty, not a holder, so it's excluded. Observations with an empty post-balance string are filtered so the balance column never receives `''`.

### Source

The transform reads one per-block array and unpivots each transfer into two per-wallet observations:

`nftTokenTransfers`

Each transfer becomes `(from_address, from_post_balance)` and `(to_address, to_post_balance)`. `from_post_balance` / `to_post_balance` are the absolute post-transfer holdings of that wallet for the given `(token_address, token_id)`, so the latest observation with a non-zero balance is a current holding.

### Destination

| Destination                  | Table                                                            | Read pattern                                                                                                       |
| ---------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **ClickHouse** (first-class) | `fact_wallet_nfts`                                               | Prefix scan on `(chain_id, wallet_address, token_address, token_id, …)`; current holding via `argMax` over `FINAL` |
| **Postgres**                 | `wallet_nfts` (materialized view over `wallet_nft_observations`) | Partial index `(wallet_address, token_address, token_id) WHERE balance > 0`                                        |
| **MySQL**                    | `wallet_nfts`                                                    | PK `(wallet_address, token_address, token_id)` with zeroed positions cleaned up                                    |

ClickHouse uses the collapsing log-table pattern (see the [recipes overview](/data-feeds/recipes/overview#destinations)) so chain reorganizations self-correct. The fact table's sort key is wallet-first, so a wallet's full holdings set is a contiguous range read; `argMax` over `(block_number, log_index)` resolves the current balance per id. On Postgres/MySQL the current-holding table is derived by keeping the latest observation per `(wallet, token_address, token_id)`.

### Full schema

Below is the complete read table this recipe produces. It's a starting point — keep the columns you need and drop the rest (see [Schema & flexibility](/data-feeds/recipes/overview#schema--flexibility)). `token_id` is a `uint256` identifier stored as text (never numeric — ERC-1155/721 ids exceed any practical numeric precision), and `balance` is the absolute post-transfer holding.

<Accordion title="ClickHouse — fact_wallet_nfts">
  ```sql theme={null}
  CREATE TABLE recipe_wallet_nfts.fact_wallet_nfts
  (
      vendor_event_id   String,
      ingested_at       DateTime64(3),
      chain_id          UInt32,
      block_hash        String,
      block_number      UInt64,
      log_index         UInt32,
      event_ts          DateTime64(3),
      token_address     String,
      token_id          String,                   -- uint256 id → String, not numeric
      contract_type     LowCardinality(String),   -- ERC721 | ERC1155
      wallet_address    String,
      balance           String,                   -- absolute post-transfer holding
      leg               LowCardinality(String),   -- from | to
      sign              Int8
  )
  ENGINE = ReplicatedCollapsingMergeTree(
      '/clickhouse/tables/{database}/fact_wallet_nfts', '{replica}', sign)
  PARTITION BY (chain_id, toYYYYMM(event_ts))
  ORDER BY (chain_id, wallet_address, token_address, token_id, block_number, log_index, vendor_event_id, leg);
  ```

  The `sign` column drives reorg collapsing — read with `FINAL` then `argMax`, or a sign-aware aggregate, never a bare `WHERE sign = 1`. A single-node setup can use `CollapsingMergeTree(sign)` without the replication path.
</Accordion>

<Accordion title="Postgres — wallet_nfts">
  ```sql theme={null}
  -- 1. Observations (sink target). Latest per key wins as the current holding.
  CREATE TABLE public.wallet_nft_observations (
    position         BIGINT  NOT NULL,
    log_index        BIGINT  NOT NULL,
    block_number     BIGINT  NOT NULL,
    block_timestamp  BIGINT  NOT NULL,         -- unix seconds
    token_address    TEXT    NOT NULL,
    token_id         TEXT    NOT NULL,         -- uint256 id → TEXT, not numeric
    contract_type    TEXT    NOT NULL,         -- ERC721 | ERC1155
    wallet_address   TEXT    NOT NULL,
    balance          NUMERIC(76, 0) NOT NULL,  -- absolute post-balance of the id
    leg              TEXT    NOT NULL,
    vendor_event_id  TEXT    NOT NULL
  );

  -- Recency index: leads with the DISTINCT ON keys so REFRESH avoids a sort.
  CREATE INDEX wno_wallet_token_id_recency_idx
    ON public.wallet_nft_observations
    (wallet_address, token_address, token_id, block_number DESC, log_index DESC);

  -- 2. Current-holding view: latest observation per (wallet, token, token_id).
  CREATE MATERIALIZED VIEW public.wallet_nfts AS
  SELECT DISTINCT ON (wallet_address, token_address, token_id)
    wallet_address, token_address, token_id, contract_type,
    balance, block_number, log_index, block_timestamp
  FROM public.wallet_nft_observations
  ORDER BY wallet_address, token_address, token_id, block_number DESC, log_index DESC;

  CREATE UNIQUE INDEX wallet_nfts_pk
    ON public.wallet_nfts (wallet_address, token_address, token_id);

  -- Primary access path: NFTs currently held by a wallet.
  CREATE INDEX wallet_nfts_active_idx
    ON public.wallet_nfts (wallet_address, token_address, token_id)
    WHERE balance > 0;

  -- Sibling access path: all current holders of a given NFT id.
  CREATE INDEX wallet_nfts_by_token_active_idx
    ON public.wallet_nfts (token_address, token_id, wallet_address)
    WHERE balance > 0;

  -- Cleanup index for zeroed (no-longer-held) positions.
  CREATE INDEX wallet_nfts_zero_cleanup_idx
    ON public.wallet_nfts (wallet_address, token_address, token_id)
    WHERE balance = 0;
  ```

  Refresh the current-holding view on a schedule with `REFRESH MATERIALIZED VIEW CONCURRENTLY wallet_nfts;`. MySQL is the same shape with a trigger-maintained `wallet_nfts` table and a `DELETE … WHERE balance = 0` cleanup. `position` is the block-level cursor used during backfill.
</Accordion>

### Example reads

Every NFT a wallet currently holds — latest non-zero post-balance per id (ClickHouse):

```sql theme={null}
SELECT token_address, token_id, contract_type,
       argMax(balance, (block_number, log_index)) AS amount
FROM recipe_wallet_nfts.fact_wallet_nfts FINAL
WHERE chain_id = 1 AND wallet_address = lower('0x...')
GROUP BY token_address, token_id, contract_type
HAVING amount != '0' AND amount != ''
ORDER BY token_address, token_id;
```

The same holdings read on Postgres (after refreshing the view):

```sql theme={null}
REFRESH MATERIALIZED VIEW CONCURRENTLY wallet_nfts;

SELECT token_address, token_id, contract_type, balance
FROM public.wallet_nfts
WHERE wallet_address = lower('0x...') AND balance > 0
ORDER BY token_address, token_id;
```

### Modes

Shipped defaults: **ClickHouse `hybrid`** (backfill → realtime), **Postgres / MySQL `historical`** (one-shot backfill). For live/reorg-safe ingestion, use ClickHouse — see the [overview](/data-feeds/recipes/overview#modes).

<Note>
  `position` is block-level, so realtime/hybrid on Postgres/MySQL is constrained by their single-column `UNIQUE` requirement. Run realtime/hybrid on **ClickHouse**; the Postgres/MySQL configs target `historical` backfill.
</Note>

### Multichain

The recipe is chain-parametrized via the `chain` setting — point it at any supported EVM chain or Solana. NFTs on Solana are emitted on `nftTokenTransfers` too; the `vendor_event_id` identity already includes `(from, to, token, tokenId, amount)` so each row stays unique under Solana's repeated log indices. The holdings table it produces is identical in shape.

### Fidelity gaps

`GET /{address}/nft` returns collection and metadata fields that have **no source in this per-block stream**, so they are intentionally not populated:

* `name`, `symbol` — NFT contract name/symbol. Enrich downstream from a contract-metadata table if you need them.
* `token_uri`, `metadata`, `normalized_metadata` — per-token metadata fetched from the token URI by a separate indexer; not in block data.
* `owner_of` — the API echoes the queried wallet; here it is the `wallet_address` holding key.
* `block_number_minted`, `minter_address`, `possible_spam`, `verified_collection`, `collection_logo`, `floor_price*`, `rarity*` — enrichment from separate indexers / pricing services, with no per-block source.

Core holding fields — `token_address`, `token_id`, `contract_type`, `balance`, owner (via `wallet_address`), and block coordinates — are fully populated.

### Related

<Columns cols={2}>
  <Card title="Token Balances by Wallet" href="/data-feeds/recipes/wallet/token-balances-by-wallet" icon="wallet">
    The ERC-20 sibling — same latest-wins pattern, keyed by (wallet, token).
  </Card>

  <Card title="NFT Owners by Contract" href="/data-feeds/recipes/nft/nft-owners-by-contract" icon="users">
    The inverse view — all current holders of a collection.
  </Card>

  <Card title="Portfolio Tracking" href="/data-feeds/use-cases/portfolio-tracking" icon="chart-pie">
    Wallet holdings across tokens and NFTs in one owned dataset.
  </Card>

  <Card title="NFT Marketplace" href="/data-feeds/use-cases/nft-marketplace" icon="store">
    Per-wallet NFT inventory behind a marketplace.
  </Card>
</Columns>
