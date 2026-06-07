> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Overview

> Moralis Cortex is your gateway to real-time, AI-driven insights from blockchain data. Ask natural language questions. Get structured, explainable answers. Use it via our hosted API or run the Cortex MCP Server in your own infrastructure.

<Warning>
  **Deprecated — scheduled for removal on June 4, 2026.** The Cortex API is being retired. Migrate to [Onchain Skills](/data-api/onchain-skills/overview), which replaces Cortex with a more capable AI interface for Moralis data. See the [changelog](/changelog) for details.
</Warning>

## What is Moralis Cortex?

Moralis Cortex is an AI-native data layer for Web3, built on top of the Moralis Model Context Protocol (MCP). It connects blockchain data with large language models like GPT-4 or Claude - enabling you to query on-chain activity using plain English or structured prompts.

Whether you're building dashboards, bots, reports, or intelligent assistants, Cortex gives you the power of AI - grounded in real blockchain data.

***

## Choose How To Use It

### Option1: Cortex API (Hosted)

Use our hosted API to ask blockchain questions and get real-time insights - no setup required.

* \*\*POST \*\*[**https://cortex-api.moralis.io/chat**](https://cortex-api.moralis.io/chat) - simple, secure REST endpoint
* Powered by enterprise-grade LLMs and Moralis infrastructure
* Returns summaries and structured data
* Supports chat history (chatId) for multi-turn conversations
* Optional streaming data - get live responses

**✅ Best for:**

* Startups, growth teams, and AI tooling
* Dashboards, chat agents, or in-product insights
* Teams who want fast access without infra overhead

### Option 2: MCP Server (Self-Hosted)

Deploy the MCP server in your own environment for full control and customization.

* Distributed via NPM
* Plug in your own LLM credentials (OpenAI, Claude, open-source)
* Customize grounding logic, data access, and plugins
* Run entirely inside your infra for privacy and compliance

**✅ Best for:**

* Enterprises with security/compliance requirements
* Developers building deeply integrated AI apps
* Teams wanting full control over data and model behavior

## Why Use Cortex?

* **🔍 Ask anything** about on-chain behavior - wallet activity, dapp usage, token flows, etc.
* **🧠 LLM-powered**: Use GPT-4, Claude, or open-source models with full flexibility
* **📊 Grounded in Moralis data**: No hallucinations - only indexed, verified blockchain truth
* **⚙️ Integrate anywhere**: APIs, agents, dashboards, or local developer tooling
* **🔒 Built for production**: Secure, composable, and extensible
