> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Portfolio Tracking

> A Data Feeds recipe bundle for portfolio apps, wallets, and dashboards — every token, native asset, and NFT a wallet holds, valued in USD, synced into your own database.

### Who it's for

Teams building **portfolio apps, wallets, and dashboards** — anything that shows what a wallet holds right now and what it's worth. The goal is a current-holdings view you own: every token balance, native-asset balance, and NFT, each marked in USD, refreshed live at the chain head.

### The recipe bundle

This use case combines three balance recipes — one per asset class — with **Token Prices** for valuation. Each balance recipe is keyed by wallet, so "everything wallet Y holds" is a single prefix scan.

| Recipe                                                                          | Role in the portfolio                                                                                                  |
| ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| [Token Balances by Wallet](/data-feeds/recipes/wallet/token-balances-by-wallet) | Every ERC-20 / SPL token a wallet holds, with its current balance — the core fungible-holdings table, keyed by wallet. |
| [Native Balances](/data-feeds/recipes/wallet/native-balances)                   | The wallet's native-asset (gas-token) balance — ETH, BNB, SOL, etc. — tracked separately from tokens.                  |
| [NFTs by Wallet](/data-feeds/recipes/wallet/nfts-by-wallet)                     | Every NFT a wallet holds — collection address, token ID, and ERC-721 / ERC-1155 type.                                  |
| [Token Prices](/data-feeds/recipes/token/token-prices)                          | The valuation join target — the latest USD/native mark per token used to value fungible holdings.                      |

<Note>
  Balances are tracked as **post-balance observations**: each recipe records the holder's balance *after* every transfer it was part of, so the latest observation per `(wallet, asset)` is the current balance. No periodic re-scan of the chain is needed.
</Note>

### How the pieces fit

```
Token Balances by Wallet ──┐
Native Balances          ──┼──►  current holdings  ◄── valued by ──  Token Prices
NFTs by Wallet           ──┘     (per wallet)
```

* **The three balance recipes** each unpivot every transfer into per-wallet `(from, post-balance)` and `(to, post-balance)` observations. The latest observation per `(wallet, asset)` — `argMax` over `(block_number, log_index)` — is the live holding. Token and NFT balances are keyed by `(chain_id, wallet_address, token_address[, token_id])`; native balances drop `token_address` and tiebreak on `native_seq` (native transfers carry no `log_index`).
* **Token Prices** is the connective tissue: join each fungible balance to its token's latest mark to value the holding. The recipe ships a carry-forward `latest_token_price_dict`, so even quiet tokens keep their last on-chain mark — a single `dictGet` per token.

### Valuing a wallet's fungible holdings

Read the current non-zero token balances for a wallet, then value each against the latest USD mark from the Token Prices sync:

```sql theme={null}
SELECT  b.token_address,
        b.current_balance,
        dictGetOrDefault(
          'recipe_token_price_history.latest_token_price_dict', 'usd_price',
          tuple(b.chain_id, b.token_address), '0') AS usd_price
FROM (
  SELECT  chain_id,
          token_address,
          argMax(balance, (block_number, log_index)) AS current_balance
  FROM    recipe_token_balances_by_wallet.fact_balances_by_wallet FINAL
  WHERE   chain_id = 1 AND wallet_address = lower('0x…')
  GROUP BY chain_id, token_address
  HAVING  current_balance != '0' AND current_balance != ''
) AS b;
```

Scale `current_balance` by `10^token_decimals` before multiplying by `usd_price` to get a fully-scaled dollar value; source decimals from a Token Metadata sync. The native balance follows the same pattern against the Native Balances fact (tiebreak on `native_seq`), valued against a native-price feed.

### Notes and considerations

* **Read canonical state.** All three balance facts and Token Prices use the collapsing log-table pattern. Read with `FINAL` (then `argMax`) or a sign-aware aggregate — never a bare `WHERE sign = 1`, or unmerged reorg counter-rows will skew balances.
* **Decimals.** Balances are raw integer strings. Scale by `10^token_decimals` before displaying or valuing — pull decimals from a Token Metadata sync.
* **Chains.** Token Balances and Token Prices are chain-parametrized (EVM + Solana); set the chain env vars per sync. NFTs by Wallet is EVM (ERC-721 / ERC-1155).
* **Native vs token.** The native asset is not an ERC-20 and is tracked by its own recipe — don't expect it in the token-balances table. Value it against a native-price mark, not the token-price dictionary.
* **Pair with other recipes.** Add [Wallet History](/data-feeds/recipes/wallet/wallet-history) for the chronological feed behind a holding, and [Token Approvals](/data-feeds/recipes/wallet/token-approvals) to surface outstanding allowances in a wallet's security view.
* **Run mode.** Run the ClickHouse path in `hybrid` mode so balances backfill history and then stay current, reorg-safe, at the chain head.

### Get started

Data Feeds is in early access.

<Card title="Request Early Access" icon="rocket" href="/data-feeds/early-access">
  Build a live, valued portfolio view on your own infrastructure with the Moralis team.
</Card>
