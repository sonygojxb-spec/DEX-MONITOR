> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Analytics

> A Data Feeds recipe bundle for tracking a token's distribution and activity — holders, balances, transfers, transfer counters, and every DEX trade — synced into your own database.

### Who it's for

Token and project teams, growth and analytics functions, and dashboards that need a live, owned view of **a token's distribution and activity** — who holds it, how it's spread, how much it moves, and how it trades. The output is a set of token-keyed tables in your own warehouse: the holder list and its balances, the full transfer log, per-token counters, and every DEX trade touching the token.

### The recipe bundle

All of these recipes read the same Moralis-indexed, normalized per-block onchain data and key by token, so they compose into one token-centric view.

| Recipe                                                                       | Role in the analytics view                                                                                                                                               |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Token Holders](/data-feeds/recipes/token/token-holders)                     | The holder list — every non-zero holder with their current balance and a best-effort USD value, derived from the absolute post-transfer balances. The "who owns it" leg. |
| [Token Balances by Token](/data-feeds/recipes/token/token-balances-by-token) | The same holder balances without the in-block USD valuation — the lean distribution table when you don't need price enrichment.                                          |
| [Token Stats](/data-feeds/recipes/token/token-stats)                         | Per-token transfer counters — a reorg-safe rollup row per token, queried as one row for the full stats block.                                                            |
| [Token Transfers](/data-feeds/recipes/token/token-transfers)                 | The flat transfer log — one row per ERC-20 transfer of the token, the raw activity feed every counter and balance derives from.                                          |
| [Swaps by Token](/data-feeds/recipes/markets/swaps-by-token)                 | Every DEX trade that touched the token — direct pool fills and aggregator-routed trades — USD-enriched in-block for volume and notional.                                 |

<Note>
  **Token Holders is Token Balances by Token plus the USD valuation leg.** If you only need the distribution table — addresses and balances — run Token Balances by Token alone. Add Token Holders when you want the in-block USD spot price and `usd_value` folded onto each holding.
</Note>

### How the pieces fit

```
Token Transfers ──┬──►  Token Stats          (per-token transfer counters)
                  ├──►  Token Balances by Token  (latest balance per wallet)
                  └──►  Token Holders         (balances + in-block USD value)

Swaps by Token  ──────►  trade + volume feed  (every DEX fill, USD-enriched)
```

* **Token Transfers** is the activity backbone — every movement of the token, one row each. It carries each side's absolute post-transfer balance, which is what makes the balance and holder views a latest-observation lookup rather than a running sum.
* **Token Stats** folds the transfer stream into a per-token counter row — the cheap, always-current "how many transfers" answer, and the pattern to extend with any future per-token metric.
* **Token Balances by Token** and **Token Holders** project the same transfers into the current balance per `(token, wallet)`; Token Holders adds the in-block USD spot price and best-effort `usd_value`.
* **Swaps by Token** is the market leg — trading activity and USD volume, separate from raw transfers, so you can split "moved" from "traded."

### Distribution + activity in one read

A token dashboard usually wants the headline numbers together: holder count, top holders, transfer count, and recent trading volume. Each comes from its own recipe's token-keyed table, read with `FINAL` or a sign-aware aggregate so reorgs are corrected.

**Top holders with USD value** (Token Holders — `FINAL` collapses reorg `±1` pairs before `argMax`):

```sql theme={null}
SELECT wallet_address,
       argMax(balance, (block_number, log_index))   AS current_balance,
       argMax(usd_price, (block_number, log_index)) AS usd_price
FROM   recipe_token_holders.fact_token_holders FINAL
WHERE  chain_id = 1 AND token_address = lower('0xA0b8...')
GROUP BY wallet_address
HAVING current_balance != '0' AND current_balance != ''
ORDER BY toFloat64OrZero(current_balance) DESC
LIMIT 100;
```

**Total transfer count** (Token Stats — `sum` is reorg-safe, the reverted block's `-1` rows cancel the original `+1`):

```sql theme={null}
SELECT sum(transfers_total) AS transfers_total
FROM   recipe_token_stats.fact_token_stats
WHERE  chain_id = 1 AND token_address = lower('0xA0b8...');
```

**24h DEX volume** (Swaps by Token — sign-aware, cheaper than `FINAL`):

```sql theme={null}
SELECT sumIf(toFloat64OrZero(notional_usd), sign =  1)
     - sumIf(toFloat64OrZero(notional_usd), sign = -1) AS volume_usd
FROM   recipe_swaps_by_token.fact_swaps_by_token
WHERE  chain_id = 1
  AND  token_address = lower('0xA0b8...')
  AND  event_ts >= now() - INTERVAL 1 DAY;
```

Holder count is the same Token Holders table wrapped in a `count()` over the non-zero `argMax` balances; the raw activity behind any of these numbers is a scan of `recipe_token_transfers.fact_token_transfers` filtered to the token.

### Notes and considerations

* **Read canonical state correctly.** On ClickHouse, read with `FINAL` or a sign-aware aggregate (`sum`, `sumIf … sign`), never a bare `WHERE sign = 1`. The collapsing/summing log tables converge on canonical state on merge; a bare sign filter sees uncollapsed reorg rows.
* **Balances are observations, not deltas.** Token Holders and Token Balances by Token rely on the absolute `fromPostBalance` / `toPostBalance` carried on each transfer, so the current holding is just the latest observation per `(token, wallet)` — no reconstruction. The EVM zero address (mint/burn counterparty) is skipped.
* **Decimals and USD.** Token Holders' `usd_value` is a best-effort in-block mark using a fixed scale; for precise reporting, scale raw amounts by `10^token_decimals` from a Token Metadata sync and value against a Token Prices feed.
* **EVM + Solana.** These recipes are chain-parametrized; set the Solana chain env vars to run the same shapes against Solana, where the event ids stay row-unique despite repeated `logIndex` within an instruction.
* **Run mode and scale.** Run the ClickHouse path in `hybrid` mode to backfill history and then tail the chain head, reorg-safe. A high-volume token's transfer and swap tables are large — scope chain-wide reads to a block or time range, and lean on the token-first sort key for prefix scans.
* **Pair with other recipes.** Add [Token Prices](/data-feeds/recipes/token/token-prices) for precise valuation and price history, and [Token Metadata](/data-feeds/recipes/token/token-metadata) for decimals, name, and symbol on your dashboard.

### Get started

Data Feeds is in early access.

<Card title="Request Early Access" icon="rocket" href="/data-feeds/early-access">
  Track a token's holders, transfers, and trading in your own database with the Moralis team.
</Card>
