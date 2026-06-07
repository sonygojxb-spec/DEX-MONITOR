> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Auth API

> Web3 authentication using wallet signature, built on the EIP-4361 standard for secure off-chain identity verification.

## Overview

Moralis **Auth API** enables secure **Web3 authentication** by letting users prove wallet ownership through message signing.

Instead of managing passwords or OAuth flows, Auth API uses cryptographic signatures to verify that users control their wallets - the native identity primitive of Web3.

***

## What Is Auth API?

Auth API provides a complete **wallet-based authentication flow** that:

* Generates secure challenge messages for users to sign
* Verifies wallet signatures cryptographically
* Returns a unique user identifier (`profileId`) across sessions
* Works with both EVM chains and Solana

The authentication follows the **EIP-4361** standard (Sign-In with Ethereum), ensuring compatibility with wallet apps and established security practices.

***

## How It Works

The authentication flow consists of three steps:

1. **Request Challenge** - Your backend requests a challenge message from Moralis
2. **User Signs** - The user signs the challenge message with their wallet
3. **Verify Signature** - Your backend sends the signature to Moralis for verification

Upon successful verification, you receive a `profileId` that uniquely identifies the user - regardless of which wallet or chain they used to authenticate.

***

## Key Features

Auth API includes:

* **EIP-4361 Standard** - Built on Sign-In with Ethereum for broad wallet compatibility
* **Unified Profile ID** - Single identifier per user across wallets and chains
* **Multi-Wallet Support** - Users can link multiple wallets to one profile
* **Cross-Chain** - Works with EVM chains and Solana
* **Stateless Verification** - No session management required on Moralis side

***

## Supported Networks

Auth API supports wallet authentication across:

* **EVM Chains** - Ethereum, Polygon, BNB Chain, Arbitrum, Optimism, Base, Avalanche, and more
* **Solana** - Full support for Solana wallet signatures

***

## Wallet Integrations

Auth API works with popular wallet connection libraries:

* MetaMask
* WalletConnect
* RainbowKit
* Coinbase Wallet
* Web3Auth
* Magic.Link
* Particle Network

***

## Common Use Cases

Auth API is commonly used for:

* **dApp Authentication**\
  (secure login without passwords)
* **Gated Content**\
  (verify wallet ownership before granting access)
* **NFT Verification**\
  (prove ownership for holder-only features)
* **Multi-Wallet Accounts**\
  (link multiple wallets to a single user profile)
* **Cross-Chain Identity**\
  (unified identity across EVM and Solana)

***

## Limitations

Auth API currently does **not** support:

* **EIP-1271 Signatures** - Smart contract wallet signatures (e.g., Safe, Argent) are not supported. Only EOA (Externally Owned Account) wallets can authenticate.

***

## Get Started

* [How to Authenticate Users with MetaMask](/get-started/tutorials/auth-api/authenticate-users-with-meta-mask)
* [How to Authenticate Users with RainbowKit](/get-started/tutorials/auth-api/authenticate-users-with-rainbow-kit)
* [How to Authenticate Users with WalletConnect](/get-started/tutorials/auth-api/authenticate-users-with-wallet-connect)
* [How to Authenticate Users with Coinbase Wallet](/get-started/tutorials/auth-api/authenticate-users-with-coinbase-wallet)
* [How to Authenticate Users with Web3Auth](/get-started/tutorials/auth-api/authenticate-users-with-web3-auth)
* [How to Authenticate Users with Magic.Link](/get-started/tutorials/auth-api/authenticate-users-with-magic-link)
