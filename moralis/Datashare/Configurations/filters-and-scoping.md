> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Filters & Scoping

> Control the scope and cost of your Datashare exports using date range, wallet, and token filters.

Filters determine how much data your export includes — and how many credits it consumes. Apply filters to narrow exports to exactly the data you need.

***

### Date Range (Required)

The date range is the **single biggest driver of export size**. Wider ranges mean more rows, more GB, and higher credit cost.

* Start with a **single day or week** for initial runs
* Use the **"Current"** button to set the end date to the present
* Supports **datetime values** for hourly precision

<Warning>
  An unfiltered Ethereum Token Transfers job spanning a month will be very large. Always estimate before you run.
</Warning>

***

### Wallet Address (Optional)

Filter results to activity involving specific wallet addresses.

* Supports up to **500 addresses** per job
* Useful for verifying output against known wallet activity
* If no addresses are specified, the export includes **all addresses** on the chain — useful for full-chain data pulls, but expect significantly larger exports

***

### Token Address (Optional)

Filter to specific token contracts — for example, USDC or WETH. This is useful when you only need transfer or swap data for particular tokens rather than all activity on the chain.

***

### Field Selection

When creating an export, you can select specific fields from each dataset. More fields increase export size and GB consumption **proportionally**.

Start with the minimum fields you actually need. You can always run additional exports with more fields later.

***

### Scoping Best Practices

| Approach                   | Impact                                          |
| -------------------------- | ----------------------------------------------- |
| Narrow date range          | Fewer rows, lower credit cost                   |
| Add wallet or token filter | Targets specific activity instead of full chain |
| Select fewer fields        | Smaller file size per row                       |
| Combine all three          | Minimal, focused export for validation          |

<Note>
  You can run **estimates as many times as you want at no cost**. Use estimates to iterate on your filters before committing credits.
</Note>
