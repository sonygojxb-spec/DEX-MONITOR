> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Spam Filtering

> Spam detection helps you identify and handle potentially harmful contracts in the Web3 ecosystem, in real time.

Our spam filtering is designed to protect applications and end users from interacting with spam, phishing, or low-quality token and NFT contracts.

## How It Works

Moralis automatically evaluates contracts as they are processed onchain.

For both **ERC20 tokens** and **NFT contracts**, Moralis adds a boolean field:

```
"possible_spam": true | false
```

This field indicates whether a contract is **likely to be spam or malicious**.

Spam detection is applied **in real time** as part of contract metadata processing (e.g. name, symbol, decimals, NFT metadata).

## Detection Logic

Spam detection is based on multiple internal signals, including:

* Keyword-based matching across contract metadata
* Known spam and phishing patterns
* Heuristic analysis from historical onchain behavior

Detection rules are continuously updated as new spam patterns emerge.

## Using Spam Detection

You can use the `possible_spam` field to:

* Hide suspicious tokens or NFTs from your UI
* Warn users before interacting with risky contracts
* Filter out spam from analytics, balances, or portfolios

Many Moralis endpoints (such as [Token Balances](/data-api/evm/wallet/token-balances)) support **excluding spam contracts** directly at query time.

## ERC20 Tokens & Token Scores

For ERC20 tokens, spam detection works well alongside [**Token Scores**](/data-api/data-features/token-scores).

While `possible_spam` focuses on **known and likely spam signals**, Token Scores provide a broader **token quality and safety assessment**, considering factors such as:

* Liquidity
* Trading volume
* Holder distribution
* Transaction activity
* Token age

Using both together gives a more complete picture of token risk and quality.

***

## Notes

* `possible_spam` is a **best-effort signal**, not a guarantee
* Always apply additional validation for high-value or security-critical workflows
