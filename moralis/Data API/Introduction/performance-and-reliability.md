> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Performance

> Performance characteristics of Moralis APIs, including latency percentiles, supported request rates, data freshness, uptime, and enterprise SLAs.

This page outlines the **real-world performance characteristics** of Moralis APIs, including **latency**, **request throughput**, **data freshness**, and **availability**.

The figures below reflect typical production behavior under normal load and are intended to help teams design and operate reliable systems.

***

## API Latency

Moralis APIs are optimized for **low-latency, high-throughput** access to blockchain data.

Typical response times across core read endpoints:

| Percentile | Latency       |
| :--------- | :------------ |
| **p50**    | **\< 50 ms**  |
| **p90**    | **\< 500 ms** |
| **p95**    | **\< 1 s**    |

Latency may vary based on:

* Endpoint complexity
* Chain and network conditions
* Result size and pagination
* Applied enrichment (decoding, pricing, analytics)

***

## Throughput & Request Rates

Moralis supports **high sustained request volumes** for production workloads.

* **1,000+ requests per second (RPS)** is supported on appropriate plans
* Throughput is governed by **Compute Units (CUs)** and plan-level limits
* Short bursts are supported within rolling rate-limit windows
* Enterprise customers can request **custom throughput limits** and dedicated capacity

For plan-specific limits, see:

* [**Rate Limits**](/data-api/resources/rate-limits)
* [**Pricing**](/data-api/pricing)

***

## Data Freshness

Data freshness reflects how quickly new on-chain activity becomes available via the API.

Typical freshness for indexed on-chain data:

| Percentile | Freshness  |
| :--------- | :--------- |
| **p50**    | **\< 4 s** |
| **p90**    | **\< 8 s** |

Notes:

* Blocks, transactions, and transfers are indexed near real time
* Price and market data update continuously
* Derived metrics (holders, analytics, PnL) may lag slightly during periods of high activity

***

## Availability & Uptime

Moralis operates production infrastructure **24/7/365**.

* **Enterprise customers** are supported with a **24/7/365 SLA**
* Platform uptime and incident history are publicly available at:\
  [**status.moralis.io**](http://status.moralis.io)
