> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Troubleshooting

> Common issues and mistakes when using Datashare, and how to resolve them.

### Common Mistakes

| Mistake                          | Consequence                                                 | Prevention                                                           |
| -------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------- |
| No filters on wide date range    | Massive export; large credit spend                          | Add wallet/token filter for initial runs; estimate first             |
| Selecting all fields             | Larger-than-necessary export                                | Start with the minimum fields you actually need                      |
| Expecting metadata in output     | No token names, symbols, logos, or spam labels              | Plan separate metadata enrichment post-export                        |
| No S3 destination configured     | Export cannot proceed                                       | Set up bucket and IAM before hitting Export                          |
| Incorrect bucket permissions     | Job failure                                                 | Confirm IAM policy includes `s3:PutObject` on the correct bucket ARN |
| Skipping the estimate            | Unexpected credit spend                                     | Always estimate — it's free and instant                              |
| Topping up after clicking Export | Export may fail if credits run out; 5-minute window expires | Top up before running the estimate                                   |

***

### Failed Exports

The most common cause of failed exports is **incorrect bucket credentials or missing write permissions** on the IAM user.

Double-check that:

* The **access key is active** and has not been revoked
* The IAM policy includes `s3:PutObject` on the **correct bucket ARN**
* The **bucket name and region** match your S3 configuration in Datashare

***

### Minimal IAM Policy

If you don't want to use `AmazonS3FullAccess`, you only need these three permissions on your bucket:

```json theme={null}
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR-BUCKET-NAME",
        "arn:aws:s3:::YOUR-BUCKET-NAME/*"
      ]
    }
  ]
}
```

Replace `YOUR-BUCKET-NAME` with your actual S3 bucket name.

***

### Job States

| State         | Meaning                                    | Action                                                   |
| ------------- | ------------------------------------------ | -------------------------------------------------------- |
| **Pending**   | Job queued, awaiting start                 | Wait for processing to begin                             |
| **Running**   | Data extraction and S3 writing in progress | Monitor progress on the dashboard                        |
| **Completed** | Export finished — data is in your bucket   | Access data via S3 Console, CLI, or analytics tooling    |
| **Failed**    | Error occurred                             | Check credentials, permissions, and bucket configuration |

<Note>
  There is no UI download link for completed exports. Data is accessed directly from your S3 bucket.
</Note>

***

### High Estimates

If your estimate is higher than expected, check for:

* **Overly wide date ranges** — narrow to a single day or week
* **Too many selected fields** — start with the minimum you need
* **Missing wallet or token filters** — add filters to target specific activity

Estimates are free — iterate until the scope looks right before exporting.
