> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Export Your First Dataset

> Learn how to create your first Datashare export, from selecting data to verifying output in your S3 bucket.

### Dashboard Overview

The Datashare dashboard is your export control panel. It displays all historical and active jobs, with options to:

* **Search** by Job ID to find specific exports
* **Filter** by status: Pending, Running, Completed, or Failed
* **View credits** — your GB balance is shown in the top-right corner
* **Create Export** — start a new export job

### Create Export Workflow

The Create Export screen has a three-panel layout:

| Panel                              | Purpose                                                                 |
| ---------------------------------- | ----------------------------------------------------------------------- |
| **Schema Explorer** (left)         | Select chain, dataset type, and fields                                  |
| **Filters & Destination** (middle) | Set date range, wallet/token filters, output format, and S3 destination |
| **Preview & Export** (right)       | View estimate, preview sample rows, and trigger the export              |

The workflow is: **select data → scope with filters → choose destination → estimate → export**.

***

### Step 1: Select Your Data

**Choose a chain** — one chain per export job. See [Supported Chains](/datashare/supported-chains) for the full list.

**Choose a dataset** — see [Supported Data](/datashare/supported-data) for available types (Token Transfers, Native Transfers, NFT Transfers, Swap Events, Liquidity Events, plus raw data).

**Select fields** — after choosing a dataset, expand the field list and select only the fields you need. More fields increase export size and GB consumption proportionally.

<Warning>
  DataShare exports raw on-chain data. Token names, symbols, logos, spam labels, and metadata enrichment are **not included**. Plan for separate metadata enrichment post-export if needed.
</Warning>

***

### Step 2: Apply Filters

Set date range, wallet address, and token address filters to control the scope and cost of your export. See [Filters & Scoping](/datashare/filters-and-scoping) for full details.

***

### Step 3: Choose Destination & Format

**Output Format**

| Format      | Best For                        | Notes                                                           |
| ----------- | ------------------------------- | --------------------------------------------------------------- |
| **Parquet** | Athena, Spark, DuckDB, BigQuery | Columnar, highly compressed (5–10x). Recommended for analytics. |
| **CSV**     | Excel, general compatibility    | Larger files than Parquet. Compresses well with gzip.           |
| **JSON**    | Debugging, human inspection     | Largest output. Useful for spot-checking data.                  |

**S3 Destination**

Select a saved destination or add a new one. Destination profiles are reusable across future jobs. See [S3 Bucket Setup](/datashare/s3-bucket-setup) for configuration instructions, or [Export Options](/datashare/export-options) for all supported providers.

***

### Step 4: Estimate

Click **Estimate** before triggering the export. This gives you:

* The GB of credits the export will consume
* A sample row preview to verify your schema

Estimates are **free** and can be run as many times as needed.

***

### Step 5: Export

Once you click **Export**, the system locks your configuration and begins processing.

<Warning>
  There is a **5-minute export window** after clicking Export. Top up credits and finalize your S3 configuration before this step. Navigating away or session timeout during this window may require re-running the estimate.
</Warning>

***

### Your First Export Recipe

Use this minimal configuration to validate the end-to-end flow without significant credit spend:

| Setting        | Value                                                     | Rationale                                     |
| -------------- | --------------------------------------------------------- | --------------------------------------------- |
| Chain          | Ethereum                                                  | Highest activity; good scale test             |
| Dataset        | Token Transfers                                           | Most commonly used; well-understood schema    |
| Date Range     | Last 24 hours                                             | Smallest reasonable validation window         |
| Wallet Address | 1 recognized address                                      | Verify output matches known activity          |
| Fields         | `from`, `to`, `value`, `token_address`, `block_timestamp` | Minimal schema confirming data delivery       |
| Format         | Parquet                                                   | Smallest files; compatible with DuckDB/Athena |

**After exporting:**

1. Check your S3 bucket for output files
2. Query locally with DuckDB:

```sql theme={null}
SELECT * FROM read_parquet('*.parquet') LIMIT 10;
```

3. Or use Athena to query directly from S3
4. Confirm rows match the expected wallet activity
