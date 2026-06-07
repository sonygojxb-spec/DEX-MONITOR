> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Compliance & AML

> A Data Feeds recipe bundle for compliance, AML, and forensics teams — a complete, ordered, auditable trail of everything an address did, plus its asset positions and risk surface, synced into your own database.

### Who it's for

Teams building **compliance, AML, transaction-monitoring, and forensics** tooling — anything that needs a complete, ordered, defensible record of what an address did and what it holds. The goal is a full audit trail you own: every event in sequence, every counterparty, the address's current and historical positions, and the standing risk it has granted — all reconstructable from Moralis-indexed, normalized per-block onchain data.

### The recipe bundle

This use case combines a small set of recipes. Start with **Wallet History** as the chronological backbone, layer **Token Transfers** and **Swaps by Wallet** for asset-level and DEX-activity trails, **Token Balances by Wallet** and **Native Balances** for the address's full asset positions, and **Token Approvals** for the standing risk surface.

| Recipe                                                                          | Role in the trail                                                                                                                                                                                                            |
| ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Wallet History](/data-feeds/recipes/wallet/wallet-history)                     | The backbone — every event an address was involved in, in on-chain order, classified by `direction` and `event_type`, with USD value inline. Token, native, and NFT transfers, swaps, approvals, and LP changes in one feed. |
| [Token Transfers](/data-feeds/recipes/token/token-transfers)                    | Asset-first movement trail — every ERC-20 transfer of a token, with `from_address` / `to_address` and the initiator, for counterparty and flow tracing.                                                                      |
| [Token Balances by Wallet](/data-feeds/recipes/wallet/token-balances-by-wallet) | The address's token holdings — current and historical positions per token, for net-worth, exposure, and balance-at-block snapshots.                                                                                          |
| [Native Balances](/data-feeds/recipes/wallet/native-balances)                   | The address's native-asset (gas-token) position over time, for net-worth and balance-at-block snapshots.                                                                                                                     |
| [Token Approvals](/data-feeds/recipes/wallet/token-approvals)                   | The risk surface — every allowance the address has granted, so you can compute the live exposure to each spender.                                                                                                            |
| [Swaps by Wallet](/data-feeds/recipes/markets/swaps-by-wallet)                  | DEX activity per address — every trade, with notional in USD, for layering/structuring detection.                                                                                                                            |
| [Contract Logs](/data-feeds/recipes/logs/contract-logs)                         | Audit-grade completeness — every raw event log emitted by a contract of interest (mixer, bridge, sanctioned address, custom protocol), including events the decoded recipes don't model.                                     |
| [Logs by Event Signature](/data-feeds/recipes/logs/logs-by-topic0)              | One event signature (`topic0`) chain-wide — capture a specific event across all contracts (e.g. every interaction of a flagged signature) for screening and pattern detection.                                               |

<Note>
  **Wallet History already contains the transfer, swap, and approval events.** If a single, filterable event feed per address is enough, the backbone recipe alone is your audit trail. Add the standalone recipes when you want dedicated, differently-keyed tables — **Token Transfers** keyed by token for counterparty tracing, **Swaps by Wallet** for trade-level notional, **Token Approvals** for live-allowance reconciliation, and **Token Balances by Wallet** + **Native Balances** for current/historical position snapshots. Add the **log recipes** when you need raw, decode-it-yourself completeness — events on custom or non-standard contracts that the decoded feeds don't cover, which an audit can't afford to miss.
</Note>

### How the pieces fit

```
                          ┌──► Token Transfers     (counterparty / flow trail)
Wallet History  ──────────┤
  (ordered event feed)    ├──► Swaps by Wallet      (DEX activity / notional)
                          │
Token Balances  ─────────┐│
Native Balances ─────────┤│
Token Approvals ─────────┤├──►  your audit trail per address
                          │
Contract Logs ───────────┤   (raw events the decoded feeds don't model —
Logs by Signature ───────┘    custom contracts, flagged signatures)
```

* **Wallet History** is the spine — the complete, ordered, classified feed for one address. Each row is tagged `sent` / `received` / `self` / `minted` / `burned` via `direction`, and the event kind via `event_type`, so a full activity timeline falls out of one table.
* **Token Transfers** and **Swaps by Wallet** are asset-first and trade-first views of the same source events, keyed for the questions a forensics workflow asks — "who did this address transact with for token X" and "what was the USD notional of each trade."
* **Token Balances by Wallet**, **Native Balances**, and **Token Approvals** describe *state*: the address's token and native positions over time, and the standing allowances it has granted. Balances answer "what does this address hold, now or at block N"; approvals are the risk surface — an unrevoked unlimited allowance is live exposure regardless of activity.
* **The log recipes** are the completeness backstop. The decoded feeds cover standard transfers, swaps, and approvals; **Contract Logs** and **Logs by Event Signature** capture *everything else* — custom protocol events, non-standard contracts, interactions with a flagged address — as raw `topic0…3` + `data` you decode against the ABI. For audit defensibility, "we indexed every event" beats "we indexed the events we had a decoder for."

### Building the per-address audit trail

The compliance question is "show me everything this address did, in order." That is the Wallet History feed, read reorg-safe with `FINAL`:

```sql theme={null}
-- Full chronological event trail for one address.
SELECT  block_timestamp,
        event_type,
        direction,
        counterparty,
        token_address,
        amount,
        amount_usd,
        tx_hash
FROM    recipe_wallet_history_full.fact_wallet_history_full FINAL
WHERE   chain_id = 1
  AND   wallet_address = lower('0x…')
ORDER BY block_number DESC, log_index DESC;
```

To assess the standing risk surface alongside the activity trail, compute the address's live allowances — the latest approval per `(token, spender)`, dropping anything revoked to zero:

```sql theme={null}
-- Live allowances the address has granted (the risk surface).
SELECT  token_address,
        spender_address,
        argMax(value, (block_number, log_index)) AS current_allowance
FROM    recipe_token_approvals.fact_token_approvals FINAL
WHERE   chain_id = 1
  AND   owner_address = lower('0x…')
GROUP BY token_address, spender_address
HAVING  current_allowance != '0' AND current_allowance != ''
ORDER BY token_address, spender_address;
```

Use `argMax` over `(block_number, log_index)` rather than a bare `WHERE sign = 1` so the read is correct under the collapsing log-table model and converges after reorgs.

### Notes and considerations

* **Read canonical state correctly.** On ClickHouse, every fact table follows the collapsing log-table pattern. Read with `FINAL` or a sign-aware aggregate (`argMax`, `sum(sign)`), never a bare `WHERE sign = 1`, so the trail stays correct across chain reorganizations.
* **Approvals are EVM-only** (ERC-20 `Approval(owner, spender, value)`). Value the *exposure*, not allowance × price — an unlimited approval is `2^256-1`, so dollar-weighting it is meaningless; treat unrevoked unlimited allowances as a categorical risk flag.
* **Chains.** Wallet History, Token Transfers, Token Balances by Wallet, Native Balances, and Swaps by Wallet are chain-parametrized across EVM and Solana; Token Approvals is EVM only.
* **Counterparty enrichment is yours.** The recipes deliver the complete, ordered primitives — addresses, amounts, directions, counterparties. Sanctions screening, address labelling, and risk scoring are downstream layers your application runs over this trail.
* **Decimals and USD.** Scale raw `amount` / `value` text fields by `10^token_decimals` before reporting; source decimals from a Token Metadata sync. Wallet History folds USD inline where decimals are known (swaps, LP changes); Swaps by Wallet carries `notional_usd` per trade.
* **Completeness for audit.** Run the ClickHouse path in `hybrid` mode so the trail backfills full history and then stays current, reorg-safe, at the chain head.
* **Pairing.** For valuation across every asset, add [Token Prices](/data-feeds/recipes/token/token-prices); for holder-side context on a token of interest, add [Token Holders](/data-feeds/recipes/token/token-holders).

### Get started

Data Feeds is in early access.

<Card title="Request Early Access" icon="rocket" href="/data-feeds/early-access">
  Build an owned, auditable per-address trail with the Moralis team.
</Card>
