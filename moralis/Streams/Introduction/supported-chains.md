> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Streams Supported Chains

> Blockchains supported by Moralis Streams for real-time onchain event and activity monitoring.

### Streams Supported Chains

Moralis Streams provide **real-time onchain data delivery** via webhooks, allowing you to react to blockchain activity as it happens.

Streams support a subset of chains where:

* Real-time indexing is available.
* Finality and reorg handling meet production requirements.

Use the tables below to see which chains are supported for Streams and what types of events can be monitored.

### Non-EVM Chains

Bitcoin and Solana streams have their own API groups and chain-specific configuration. See [Bitcoin Streams](/streams/bitcoin-streams) and [Solana Streams](/streams/solana-streams) for details.

| Chain Name      | Type    | Chain ID         | Streams Supported | Confirmation Threshold |
| --------------- | ------- | ---------------- | ----------------- | ---------------------- |
| Bitcoin Mainnet | Mainnet | `btc-mainnet`    | ✓                 | 2 blocks               |
| Solana Mainnet  | Mainnet | `solana_mainnet` | ✓                 | 100 slots              |

<Note>
  `Internal Txs` is an EVM-only concept and does not apply to Bitcoin or Solana. On Solana, the time unit is the **slot** rather than the block — most slots produce a block.
</Note>

### EVM Chains

| Chain Name                  | Type    | Chain ID            | Streams Supported | Internal Txs | Blocks Until Confirmed |
| --------------------------- | ------- | ------------------- | ----------------- | ------------ | ---------------------- |
| Ethereum Mainnet            | Mainnet | 0x1 (1)             | ✓                 | ✓            | 12                     |
| Ethereum Sepolia            | Testnet | 0xaa36a7 (11155111) | ✓                 | ✗            | 18                     |
| Polygon Mainnet             | Mainnet | 0x89 (137)          | ✓                 | ✓            | 100                    |
| Polygon Amoy                | Testnet | 0x13882 (80002)     | ✓                 | ✗            | 100                    |
| Binance Smart Chain Mainnet | Mainnet | 0x38 (56)           | ✓                 | ✓            | 18                     |
| Binance Smart Chain Testnet | Testnet | 0x61 (97)           | ✓                 | ✗            | 18                     |
| Arbitrum                    | Mainnet | 0xa4b1 (42161)      | ✓                 | ✓            | 18                     |
| Arbitrum Sepolia            | Testnet | 0x66eee (421614)    | ✓                 | ✗            | 600                    |
| Base                        | Mainnet | 0x2105 (8453)       | ✓                 | ✓            | 100                    |
| Base Sepolia                | Testnet | 0x14a34 (84532)     | ✓                 | ✗            | 100                    |
| Optimism                    | Mainnet | 0xa (10)            | ✓                 | ✓            | 500                    |
| Optimism Sepolia            | Testnet | 0xaa37dc (11155420) | ✓                 | ✗            | 600                    |
| Linea                       | Mainnet | 0xe708 (59144)      | ✓                 | ✓            | 100                    |
| Linea Sepolia               | Testnet | 0xe705 (59141)      | ✓                 | ✗            | 100                    |
| Avalanche                   | Mainnet | 0xa86a (43114)      | ✓                 | ✓            | 100                    |
| Fantom Mainnet              | Mainnet | 0xfa (250)          | ✓                 | ✓            | 100                    |
| Fantom Testnet              | Testnet | 0xfa2 (4002)        | ✓                 | ✗            | 100                    |
| Cronos Mainnet              | Mainnet | 0x19 (25)           | ✓                 | ✗            | 100                    |
| Gnosis                      | Mainnet | 0x64 (100)          | ✓                 | ✗            | 100                    |
| Gnosis Chiado               | Testnet | 0x27d8 (10200)      | ✓                 | ✗            | 100                    |
| Chiliz Mainnet              | Mainnet | 0x15b38 (88888)     | ✓                 | ✓            | 100                    |
| Chiliz Testnet              | Testnet | 0x15b32 (88882)     | ✓                 | ✗            | 100                    |
| Moonbeam                    | Mainnet | 0x504 (1284)        | ✓                 | ✗            | 100                    |
| Moonriver                   | Testnet | 0x505 (1285)        | ✓                 | ✗            | 100                    |
| Moonbase                    | Testnet | 0x507 (1287)        | ✓                 | ✗            | 100                    |
| Flow                        | Mainnet | 0x2eb (747)         | ✓                 | ✓            | 100                    |
| Flow Testnet                | Testnet | 0x221 (545)         | ✓                 | ✗            | 100                    |
| Ronin                       | Mainnet | 0x7e4 (2020)        | ✓                 | ✓            | 100                    |
| Ronin Saigon Testnet        | Testnet | 0x7e5 (2021)        | ✓                 | ✗            | 100                    |
| Lisk                        | Mainnet | 0x46f (1135)        | ✓                 | ✓            | 100                    |
| Lisk Sepolia Testnet        | Testnet | 0x106a (4202)       | ✓                 | ✗            | 100                    |
| Pulsechain                  | Mainnet | 0x171 (369)         | ✓                 | ✗            | 100                    |
| HyperEVM                    | Mainnet | 0x3e7 (999)         | ✓                 | ✓            | 100                    |
| Sei                         | Mainnet | 0x531 (1329)        | ✓                 | ✗            | N/A                    |
| Sei Testnet                 | Testnet | 0x530 (1328)        | ✓                 | ✗            | N/A                    |
| Monad                       | Mainnet | 0x8f (143)          | ✓                 | ✓            | 100                    |
