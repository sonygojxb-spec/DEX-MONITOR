> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Accounting & Tax

> A Data Feeds recipe bundle for accounting, tax, and treasury tools — a wallet's full event feed plus per-asset transfer ledgers, valued in USD at block time, synced into your own database.

### Who it's for

Teams building **accounting, tax, bookkeeping, treasury, and audit** tooling — anything that needs a complete, valued, auditable record of what moved through a set of wallets. The goal is a ledger you own: every inflow and outflow, classified, with a USD value at the time it happened.

### The recipe bundle

This use case combines a small set of recipes. Start with **Wallet History** as the backbone, then add the standalone transfer recipes when you need per-asset ledger tables, and **Token Prices** for valuation.

| Recipe                                                                          | Role in the ledger                                                                                                                                                                  |
| ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Wallet History](/data-feeds/recipes/wallet/wallet-history)                     | The backbone — every event a wallet was involved in, in order, with inline USD value. Covers token, native, and NFT transfers, swaps, approvals, and LP changes in one feed.        |
| [Token Transfers](/data-feeds/recipes/token/token-transfers)                    | Per-token transfer ledger — every ERC-20 movement of a given token, keyed for asset-level reconciliation.                                                                           |
| Native Transfers                                                                | Native-asset (gas-token) movements, including internal transfers — available within Wallet History's `native_transfer` rows.                                                        |
| [NFT Transfers](/data-feeds/recipes/nft/nft-transfers)                          | NFT movements (collection + token ID) for inventory and disposal tracking.                                                                                                          |
| [Token Balances by Wallet](/data-feeds/recipes/wallet/token-balances-by-wallet) | Period-end token holdings per wallet — the balance-sheet snapshot, reconciled against the transfer ledger.                                                                          |
| [Native Balances](/data-feeds/recipes/wallet/native-balances)                   | Period-end native-asset (gas-token) balance per wallet.                                                                                                                             |
| [Token Prices](/data-feeds/recipes/token/token-prices)                          | The valuation join target — USD/native marks used to value every transfer and holding at block time.                                                                                |
| [Contract Logs](/data-feeds/recipes/logs/contract-logs)                         | Raw events from contracts you can't book from decoded feeds — staking rewards, vesting, rebases, custom protocol events. Decode against the ABI to classify them as income/expense. |
| [Logs by Event Signature](/data-feeds/recipes/logs/logs-by-topic0)              | One event type chain-wide — e.g. capture a specific reward or distribution event across every protocol you interact with, in one feed.                                              |

<Note>
  **Wallet History already contains the transfer events.** If a single, filterable event feed per wallet is enough, the backbone recipe alone covers accounting. Add the standalone **Token / NFT Transfers** recipes when you want dedicated, per-asset tables (e.g. one table per token to reconcile against an exchange's books) rather than filtering one wide feed. Add the **log recipes** when income or expense lives in events the decoded feeds don't model — staking rewards, vesting unlocks, rebases, or any custom protocol event — so nothing falls outside the books. Add the **balance recipes** for the positions side — period-end holdings (the balance sheet) to reconcile against the transaction ledger.
</Note>

### How the pieces fit

```
Wallet History   ──┐
Token Transfers  ──┤
Native Transfers ──┼──►  transaction ledger (flows)   ──┐
NFT Transfers    ──┤                                    │
Contract Logs    ──┘  (custom income/expense events)    ├──► valued by ── Token Prices
                                                         │
Token Balances by Wallet ──┐                            │
Native Balances          ──┴─► balance-sheet (positions)┘
```

* **Wallet History** gives you the chronological, classified feed — each row already tagged `sent` / `received` / `self` / `minted` / `burned`, so debits and credits fall out of `direction`.
* **The transfer recipes** give you asset-first tables for reconciliation — "every movement of token X across all tracked wallets."
* **The log recipes** close the gap for income and expense that isn't a plain transfer — staking rewards, vesting unlocks, rebases, fee distributions. Decode the raw `data` against the contract ABI and classify each event into your chart of accounts.
* **Transfers are the flows; balances are the positions.** [Token Balances by Wallet](/data-feeds/recipes/wallet/token-balances-by-wallet) and [Native Balances](/data-feeds/recipes/wallet/native-balances) give the period-end holdings snapshot — the balance sheet — to reconcile against the transfer ledger and to value at the reporting date.
* **Token Prices** is the connective tissue: join any transfer or holding to the token's mark at its `block_number` to compute USD value at the time of the event (for the P\&L) or at period end (for the balance sheet) — the basis every tax and accounting calculation needs.

### Valuing transfers in USD

Wallet History folds USD values inline for the event types that carry decimals (swaps, LP changes) and for token transfers as an **unscaled** product (`raw_amount × price`). For a ledger you'll typically want fully-scaled dollar values for every asset, which is a join against the Token Prices sync:

```sql theme={null}
-- Token transfers for a wallet, valued in USD at block time.
SELECT  wh.block_timestamp,
        wh.direction,
        wh.token_address,
        wh.amount,
        wh.counterparty,
        wh.tx_hash
FROM    fact_wallet_history_full AS wh FINAL
WHERE   wh.chain_id = 1
  AND   wh.wallet_address = lower('0x…')
  AND   wh.event_type = 'token_transfer'
ORDER BY wh.block_number DESC, wh.log_index DESC;
```

Pair this with the Token Prices sync (joined on token + nearest block) and a token-decimals lookup to produce a fully-scaled, dated, dollar-valued ledger.

### Notes and considerations

* **Cost basis** is a downstream calculation (FIFO/LIFO/average) your application performs over this ledger — the recipes give you the valued, ordered events it needs, not the basis itself.
* **Decimals.** Scale raw `amount` values by `10^token_decimals` before reporting dollars; source decimals from a Token Metadata sync.
* **Native and NFT USD.** Wallet History leaves these `NULL`; value native movements against a native-price feed, and treat NFTs separately (cost/proceeds from trade data, not transfers).
* **Completeness for audit.** Run the ClickHouse path in `hybrid` mode so the ledger backfills history and then stays current, reorg-safe, at the chain head.

### Get started

Data Feeds is in early access.

<Card title="Request Early Access" icon="rocket" href="/data-feeds/early-access">
  Build an owned, auditable onchain ledger with the Moralis team.
</Card>
