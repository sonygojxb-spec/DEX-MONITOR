> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Rate Limits

> Moralis APIs use a throughput-based rate-limiting system, measured in requests per second.

Each plan defines how many requests you can send per second. If you exceed this, requests will be rate-limited.

## Throughput & Rolling Window

Throughput limits are evaluated over a **rolling 4-second window**, not per exact second.

This allows short request bursts, as long as your total request count stays within your plan's limits over that window.

## Maximum requests per second

| Plan       | Throughput |
| :--------- | :--------- |
| Free       | 40 reqs/s  |
| Starter    | 40 reqs/s  |
| Pro        | 80 reqs/s  |
| Business   | 200 reqs/s |
| Enterprise | Custom     |

## Avoiding Rate Limits

To avoid rate limiting:

* Keep your request rate within your plan's throughput
* Avoid sustained spikes that exceed the rolling 4-second limit
* Upgrade your plan if you consistently hit limits

If you exceed your throughput, the API will return a **429 Too Many Requests** response.
