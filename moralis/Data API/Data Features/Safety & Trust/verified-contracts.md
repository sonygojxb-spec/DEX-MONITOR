> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Verified Contracts

> Moralis surfaces verification signals for ERC20 tokens and NFT collections to help you distinguish legitimate projects from impersonators, clones, or scams.

These signals are based on trusted third-party verification sources and are exposed directly in API responses.

## Verified Contracts (ERC20)

The `verified_contract` flag indicates that an **ERC20 token contract has been verified by CoinGecko**.

<Note>
  This verification is **not** based on Etherscan contract verification.
</Note>

### What CoinGecko Verification Means

When a contract is marked as verified:

* The token has been reviewed by the **CoinGecko team**
* It has passed CoinGecko’s internal criteria for legitimacy
* It is considered a **trusted, recognised token** within the ecosystem

This helps developers:

* Filter out scam or impersonator tokens
* Prioritise legitimate assets in search and UI
* Build safer default experiences for users

***

## Verified NFT Collections

The `verified_collection` flag applies to **NFT collections** that have been verified by **OpenSea**.

When a collection is verified:

* OpenSea has reviewed and validated the collection
* The collection is recognised as authentic
* Users can more easily distinguish real projects from fakes

This is the same verification signal users see as a **verified badge on OpenSea**.

***

## Why Verification Matters

Verification signals are especially useful for:

* Wallets and portfolio trackers
* Token and NFT discovery
* Search and filtering experiences
* Reducing exposure to scams and copycat projects

They are often used alongside:

* [Spam Filtering](/data-api/resources/spam-filtering)
* [Token Scores](/data-api/data-features/token-scores)
* [Token Filtering](/data-api/data-features/search-and-discovery/token-filtering)

to build a layered safety model.

***

## Notes & Limitations

* Verification is **source-dependent**:
  * ERC20 tokens → CoinGecko
  * NFT collections → OpenSea
* Not all legitimate projects are verified
* Verification status may change over time as source data updates

Always treat verification as a **signal**, not a guarantee.
