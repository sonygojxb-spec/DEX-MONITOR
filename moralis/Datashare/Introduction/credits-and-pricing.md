> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Credits & Pricing

> How Datashare's prepaid GB credit model works, including top-ups, tiered pricing, and credit consumption.

Datashare operates on a **prepaid GB credit model**. You purchase credits in advance, and they are consumed when exports complete.

***

### How Credits Work

* Credits are consumed upon **export completion**, not when you run an estimate
* Your current **GB balance** is displayed in the top-right corner of the Datashare dashboard
* Estimates are **free** — run as many as you need before committing

***

### Credit Consumption

Credit usage is based on **uncompressed data size**, regardless of the output format you choose.

| Factor                           | Impact on Credits                                            |
| -------------------------------- | ------------------------------------------------------------ |
| Wider date range                 | More rows = more GB consumed                                 |
| More selected fields             | Larger row size = more GB consumed                           |
| No wallet/token filters          | Full chain activity = significantly more GB                  |
| Output format (Parquet/CSV/JSON) | No impact — credits always calculated on uncompressed volume |

<Note>
  Parquet typically achieves 5–10x compression, so the actual files in your S3 bucket will be much smaller than the credited amount. CSV with gzip also compresses significantly.
</Note>

***

### Topping Up Credits

1. Click **Top Up** in the top-right of the Datashare main screen
2. Enter the GB quantity you need
3. Tiered pricing applies — higher volumes receive a **lower per-GB cost**
4. Top-ups are **manually approved** with confirmation

***

### Mid-Process Top-Up

If you realize you have insufficient credits while configuring an export:

1. Request a top-up and wait for approval
2. Return to **Create Export**
3. Re-run the estimate
4. Proceed with the export

<Warning>
  Always ensure you have sufficient credits **before** clicking Export. If credits run out mid-job, the export may fail, and the 5-minute export window may expire.
</Warning>
