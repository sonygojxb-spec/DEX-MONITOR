> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Datashare Export Options

> Supported export destinations for Moralis Datashare bulk data exports.

### Export Destinations

Moralis Datashare supports exporting blockchain data directly to a variety of S3-compatible object storage providers. This enables seamless integration with your existing data infrastructure and analytics pipelines.

| Provider                           | Description                                                     |
| ---------------------------------- | --------------------------------------------------------------- |
| **AWS S3**                         | Amazon Web Services Simple Storage Service                      |
| **Google Cloud Storage**           | Google Cloud Platform object storage                            |
| **Cloudflare R2**                  | Cloudflare's S3-compatible object storage with zero egress fees |
| **Backblaze B2**                   | Cost-effective cloud storage with S3-compatible API             |
| **DigitalOcean Spaces**            | Simple object storage from DigitalOcean                         |
| **Wasabi**                         | High-performance cloud storage with no egress fees              |
| **MinIO**                          | Self-hosted, high-performance object storage                    |
| **Linode (Akamai) Object Storage** | Akamai's S3-compatible cloud storage                            |
| **Vultr Object Storage**           | S3-compatible storage from Vultr                                |
| **Scaleway Object Storage**        | European cloud provider's object storage solution               |

***

### Configuration

All export destinations use S3-compatible credentials and endpoints. When setting up an export, you'll need to provide:

* **Bucket name** - The destination bucket for your data
* **Access key** - Your storage provider access key ID
* **Secret key** - Your storage provider secret access key
* **Endpoint URL** - The S3-compatible endpoint (required for non-AWS providers)
* **Region** - The storage region (where applicable)

***

### Output Formats

Choose an output format based on your analytics tooling and use case.

| Format      | Best For                        | Notes                                                                     |
| ----------- | ------------------------------- | ------------------------------------------------------------------------- |
| **Parquet** | Athena, Spark, DuckDB, BigQuery | Columnar, highly compressed (5–10x). Recommended for analytics workloads. |
| **CSV**     | Excel, general compatibility    | Larger files than Parquet. Compresses well with gzip.                     |
| **JSON**    | Debugging, human inspection     | Largest output format. Useful for spot-checking data.                     |

<Note>
  Export size estimates are based on **uncompressed** data size. Parquet typically achieves 5–10x compression, and CSV with gzip also compresses significantly. Credits are calculated on uncompressed volume regardless of the format you choose.
</Note>

***

### Getting Started

To request access to Datashare and configure your export destination, see the [Early Access](/datashare/early-access) page.
