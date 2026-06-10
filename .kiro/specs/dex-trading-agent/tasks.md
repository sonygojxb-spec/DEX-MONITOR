# Implementation Plan: DEX Trading Agent

## Overview

This plan implements the DEX Trading Agent in **Python** using **Hypothesis** for property-based
testing (100+ iterations per property) and **pytest** for unit/integration tests. It follows a
test-driven, bottom-up sequence so that each task builds on the previous and ends wired into the
running system, with no orphaned code:

1. **Foundation** — project scaffolding, data models/enums, repository abstractions + in-memory
   repos, provider interfaces + in-memory fakes, and the Config_Manager (everything else depends on
   config and models).
2. **Analysis** — Security_Inspector, Backend_Analyzer, Metrics_Tracker, and the Audit/persistence
   service (shared range-query + retention logic).
3. **Decision** — Signal_Engine (entry eligibility, rug-pull, dump predicates).
4. **Safety-critical** — Risk_Manager, Authorization_Manager, then Trade_Executor (gated by both).
5. **Action & Control** — Notifier, then the Monitoring Orchestrator + Data_Ingestor loop.
6. **Integration** — wire all components behind the orchestrator and add end-to-end integration tests.

### Conventions

- The implementation language is **Python**; all code is written in Python.
- External providers (`MarketDataProvider`, `ChainDataProvider`, `ContractInspectorProvider`,
  `TradeVenueProvider`, `NotificationChannel`) and all repositories are accessed only through
  interfaces and are injected. **Property tests replace them with in-memory fakes** so input
  variation is cheap and trade-execution safety can be exercised at scale without network/chain calls.
- Operations return an explicit `Result` (success value or typed error: `ProviderError`,
  `TimedOut`, `Unverified`, etc.); no failure path performs partial state mutation.
- Each of the design's **34 Correctness Properties** maps to exactly one Hypothesis property test
  running **>= 100 iterations**, tagged with a comment:
  `Feature: dex-trading-agent, Property {n}: {property_text}`.
- Sub-tasks marked with `*` are optional (tests) and may be skipped for a faster MVP; non-`*`
  sub-tasks are core implementation and must be implemented.

---

## Tasks

- [x] 1. Set up project structure, tooling, and test harness
  - [x] 1.1 Scaffold the package layout, tooling, and shared Result/error types
    - Create the Python package layout: `dex_agent/` with sub-packages `models/`, `providers/`,
      `repositories/`, `analysis/`, `decision/`, `execution/`, `control/`, `notify/`, `config/`,
      `audit/`; and a `tests/` tree mirroring it.
    - Add `pyproject.toml` with dependencies: `hypothesis`, `pytest`, `pytest-asyncio` (for async
      monitoring loops); configure pytest and a default Hypothesis profile of `max_examples=100`.
    - Define the shared `Result` type (success/typed-error union) and the typed error taxonomy
      (`ProviderError`, `TimedOut`, `Unverified`, `NotFound`) used across component boundaries.
    - _Requirements: foundational (supports all); Design: "Technology Approach", "Error model"_

- [x] 2. Define core data models and enums
  - [x] 2.1 Implement identity, market, and security models
    - Implement `Network`, `Token`, `TradingPair`, `WatchlistEntry`, `PairSnapshot` and the
      `Severity` ordered enum `{None=0, Low=1, Medium=2, High=3, Critical=4}`, plus `SecurityIssue`
      and `SecurityEvaluation`.
    - Provide a `max_by_ordinal` helper over `Severity` (default `None` for empty input).
    - Constrain `TradingPair.quote_asset` to the supported quote assets **SOL** and **USDC** for the
      initial Solana deployment (validated where pairs are constructed/resolved).
    - _Requirements: 2.1; Design: "Data Models", "External Integrations", `SEVERITY_ORDER`_
  - [x] 2.2 Implement wallet, metrics, signal, position, order, config, audit, and auth models
    - Implement `WalletClassification`, `WalletAnalysis`, `HolderBalance`, `MetricKind`,
      `MetricEntry` (value or `MISSING`), `AuditInfo`, `SignalType`/`ExitClass`/`Signal`,
      `Position`, `RiskProfile`, `OrderKind`/`OrderStatus`/`OrderRecord`, `Configuration`,
      `ActionType`/`AuditRecord`, `AuthStatus`/`AuthorizationRecord`.
    - Add `PerOrderSize` as a discriminated value (`FIXED_QUOTE` carrying a quote-asset amount |
      `PERCENT_BALANCE` carrying a percentage of available Quote_Asset balance) and a `per_order_size`
      field on `RiskProfile`; these drive order sizing in the Trade_Executor (Req 6.9).
    - Add the `InFlightRegistry` concept and an `OrderStatus` terminal-status notion (terminal =
      `{CONFIRMED, CANCELLED, FAILED, TIMED_OUT}`): the registry tracks at most one in-flight order per
      `pair_id`, with a marker set on submit and cleared when the order reaches a terminal status
      (Req 12.1-12.4).
    - `Configuration` now carries distinct interval fields: `refresh_interval_s` (Data_Refresh_Interval,
      range [5,300], default 30) and `signal_interval_s` (Signal_Computation_Interval, range [1,300],
      default 15), plus `discovery_scan_interval_s` (range [30,300]) and a single `measurement_period_s`
      (range [60,86400]).
    - _Requirements: 3.x, 4.x, 5.x, 6.x, 7.1, 7.2, 9.1, 9.x, 10.1, 11.6, 12.1-12.4; Design: "Data Models"_
  - [x] 2.3 Write unit tests for model construction and the severity ordering helper
    - Verify `Severity` ordering and `max_by_ordinal` edge cases (empty, single, ties).
    - _Requirements: 2.1, 2.7_

- [x] 3. Define repository abstractions and in-memory implementations
  - [x] 3.1 Implement repository interfaces, in-memory repos, and shared query primitives
    - Define repository interfaces for Tokens, Pairs, Watchlist, SecurityEval, WalletAnalysis,
      Metrics time-series, Signals, Positions, RiskProfile, Config, Audit, and Authorization.
    - Implement in-memory repositories with append idempotency keyed by
      `(pair_id, kind, timestamp)` / `tx_id` so retries cannot create duplicates.
    - Provide a shared, reusable `entries_in_range(items, start, end)` query primitive (inclusive,
      ascending) and an `older_than(items, period)` retention primitive used by both Metrics and Audit.
    - _Requirements: 1.4 (data retention), 4.4, 4.6, 10.2; Design: "Persistence Layer", "Concurrency / Idempotent persistence"_

- [x] 4. Define provider interfaces, in-memory fakes, and Solana adapters (primary Moralis adapter + real-time/fallback adapters)
  - [x] 4.1 Define provider interfaces and in-memory fakes
    - Define interfaces `MarketDataProvider`, `ChainDataProvider`, `ContractInspectorProvider`,
      `TradeVenueProvider`, and `NotificationChannel` exactly as in the design.
    - Implement in-memory fakes for each (scriptable responses, injectable failures/timeouts, recorded
      calls) for property, unit, and integration tests; all business logic continues to depend only on
      the interfaces and uses these fakes so input variation stays cheap and trade-execution safety can
      be exercised at scale without network/chain calls.
    - _Requirements: foundational for 1.x, 2.x, 3.x, 6.x, 8.x; Design: "Data Ingestion Strategy", "Testing Strategy"_
  - [x] 4.2 Implement the concrete Solana adapters behind the same interfaces (each with an injected client)
    - `MoralisAdapter` (**PRIMARY**) → implements `MarketDataProvider` (PRIMARY: token metadata +
      batch metadata, market metrics/prices, swaps & pairs, search/discovery), `ChainDataProvider`
      (PRIMARY: holders, swaps, wallet/portfolio), `ContractInspectorProvider` risk inputs (PRIMARY
      supporting inputs: token metadata + **Token Score**), AND **Moralis Solana Streams** (PRIMARY
      real-time webhooks; intake wired in Task 4.5). The adapter targets **two base URLs**:
      `https://solana-gateway.moralis.io` (Solana-native: token metadata, batch metadata, pairs, swaps,
      holders, top-holders, new tokens, price) and `https://deep-index.moralis.io/api/v2.2` (token
      analytics + Token Score, `chain=solana`); both authenticate via the `X-API-Key` header. Streams
      are managed at `https://api.moralis-streams.com` (`PUT /streams/solana`). Map each endpoint group
      to the interface methods; use the Moralis **batch metadata** endpoint (POST batch, <=100 addresses)
      for batched/coalesced token lookups. The adapter MAY be split into **MoralisMarketAdapter** /
      **MoralisChainAdapter** / **MoralisSecurityAdapter** / **MoralisStreamsAdapter** without
      architectural change. Auth: Moralis API key from secrets/config (read-only data scope; same key
      used for Streams).
      **Do NOT** use the deprecated/removed Moralis **Snipers** and **Filtered Tokens** endpoints;
      bot/sniper detection comes from **Token Swaps + Streams pre/postTokenBalance deltas**, and
      discovery comes from **Pump.fun new tokens + token-search**.
    - `SolanaRpcAdapter` → base on-chain fallback AND the **authoritative source for SPL mint/freeze
      authority**: `getAccountInfo` on the SPL mint (mintAuthority / freezeAuthority / Token-2022
      transfer-fee extension), plus `getTokenSupply`, `getTokenLargestAccounts`,
      `getSignaturesForAddress`, `getTransaction` (state/supply/holders/tx stream) and
      order-confirmation polling; used when Moralis chain data is unavailable and always for authority
      determination.
    - `DexScreenerAdapter` → `MarketDataProvider` **OPTIONAL FALLBACK**: batched token/pair lookups
      (coalesce multiple addresses per call) with awareness of the ~300 req/min token/pair limit; used
      only when Moralis market data is unavailable or for cross-checking. **Disabled unless configured.**
    - `GoPlusAdapter` → `ContractInspectorProvider` **OPTIONAL FALLBACK**: Solana token security signals
      mapped to `SecurityIssue` types (semantics mapping implemented in Task 7); used only when Moralis
      Token Score is unavailable or for corroboration. **Disabled unless configured.**
    - `JupiterAdapter` → `TradeVenueProvider` (unchanged): Quote+Swap API returning a serialized
      transaction, the Jupiter native slippage parameter, and confirmation polled via Solana RPC;
      signing via the injected signer (Task 15.2).
    - `TelegramChannel` → `NotificationChannel` (unchanged): bot `sendMessage`, with bot token + chat id
      from secrets/config.
    - Implement the **provider-selection / fallback strategy** in the Data_Ingestor: each abstraction
      resolves to its PRIMARY adapter (Moralis) first; on a typed `ProviderError`, timeout, or missing
      required field, fall back to the configured fallback adapter behind the same interface
      (DexScreener for market data, GoPlus for contract inspection, Solana RPC for base chain reads),
      otherwise apply the existing failure/last-good policy. **Fallbacks are optional and disabled by
      default** unless wired in configuration.
    - Each adapter takes an injected HTTP/RPC client so it stays testable; these are core
      implementation, while their live/network behavior is exercised by thin adapter unit tests (4.4)
      and business logic keeps using the in-memory fakes (4.1).
    - _Requirements: 1.1, 2.4, 2.5, 3.1-3.3, 3.6, 4.1-4.3, 6.1, 6.2, 6.4, 6.5, 8.1; Design: "External Integrations", "Per-Integration Details", "Provider-selection / fallback strategy"_
  - [x] 4.3 Implement the per-provider rate limiter fronting each adapter
    - Implement a reusable token-bucket/rate limiter wrapping each adapter call. Front the **Moralis**
      adapter (primary) with its limiter budgeting by Moralis **compute units (CU)** per endpoint
      (token metadata **10** / batch metadata **100**, token analytics **80**, Token Score **100**,
      holders / top-holders **50**, swaps **50**, pairs **50**, price **50**), batching token lookups
      via the Moralis **batch-metadata** endpoint (POST batch, <=100 addresses); expose the
      remaining-budget signal that the Orchestrator consumes to derive the effective poll interval
      (Task 18.7). **Moralis Solana Streams** push latency-sensitive rug/dump events, removing the need
      for tight polling of those events. DexScreener limits (~300/min token/pair, ~60/min
      profiles/boosts) apply **only when the DexScreener fallback is active**; GoPlus per its plan.
    - _Requirements: supports 1.7, 1.10; Design: "Concurrency", "Rate Limits & Real-Time Strategy"_
  - [x] 4.4 Write adapter unit tests with mocked HTTP/RPC clients
    - Verify request batching, response-to-model mapping, error/timeout typing, and rate-limiter
      behavior using mocked clients (no real network/chain calls). Include **MoralisAdapter**
      mapping/batching tests across **both hosts** (`solana-gateway.moralis.io` token metadata + POST
      batch metadata, pairs/swaps/holders/top-holders/new-tokens/price; and `deep-index.moralis.io`
      token analytics + Token Score with `chain=solana`), **Moralis Streams** webhook
      intake/verification-handshake/dedupe tests (Task 4.5), **Solana RPC authority-detection** mapping
      tests (`getAccountInfo` mintAuthority/freezeAuthority/Token-2022 transfer-fee → `SecurityIssue`
      types), and tests for the **provider-selection / fallback-selection logic** (primary Moralis →
      configured fallback on typed `ProviderError`/timeout/missing field; fallbacks disabled by default).
    - _Requirements: 1.1, 2.4, 2.5, 6.4, 8.1_

  - [x] 4.5 Implement the Moralis Solana Streams webhook intake
    - Create the stream via `PUT /streams/solana` (at `https://api.moralis-streams.com`) filtered by
      the watched `mintAddresses`, and expose a **publicly reachable HTTPS webhook endpoint** to receive
      stream callbacks. Implement the **empty-body verification handshake** (respond HTTP 200 to the
      verification request). Make intake **idempotent**, keyed on transaction `signature`, with dedupe
      that **ALWAYS returns HTTP 200** (even for duplicates/already-processed events). Compute balance
      deltas from `preTokenBalances` / `postTokenBalances` and route liquidity-removal (rug) and dump
      events into the Signal_Engine exit path (Req 5.3/5.4) and the <=5s exit alert (Req 5.5), and feed
      the bot/sniper heuristics. Inject the stream/webhook client so intake is exercised with in-memory
      fakes in tests. **This replaces the former real-time webhook intake.**
    - _Requirements: 5.3, 5.4, 5.5; Design: "Rate Limits & Real-Time Strategy", "Per-Integration Details"_

- [x] 5. Implement Config_Manager
  - [x] 5.1 Implement parameter ranges, validation, defaults, persistence, and startup load
    - Implement `PARAM_RANGES`, documented `DEFAULTS`, `save(input)` (reject non-numeric/missing and
      out-of-range while retaining the active config and identifying the offending parameter),
      `load_at_startup()` (latest persisted or defaults), and persistence-failure tolerance.
    - Include `signal_interval_s` (Signal_Computation_Interval, [1,300]) and
      `discovery_scan_interval_s` ([30,300]) in `PARAM_RANGES`/validation alongside the existing
      `refresh_interval_s` (Data_Refresh_Interval, [5,300]) and the single `measurement_period_s`
      ([60,86400]) so all are validated as numeric, in-range parameters (Req 9.1).
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7; Design: "Config_Manager"_
  - [x] 5.2 Write property test for configuration validation
    - **Property 29: Configuration validation accepts exactly in-range numeric values**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.7**
  - [x] 5.3 Write property test for persistence round-trip and latest-wins load
    - **Property 30: Configuration persistence round-trip and latest-wins**
    - **Validates: Requirements 9.4, 9.5**
  - [x] 5.4 Write property test for documented defaults within allowed ranges
    - **Property 31: Documented defaults fall within their allowed ranges**
    - **Validates: Requirements 9.6**
  - [x] 5.5 Write unit test for config persistence-failure indication
    - Verify active config retained and failure surfaced when the config repo fails.
    - _Requirements: 9.7_

- [x] 6. Checkpoint - foundation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement Security_Inspector
  - [x] 7.1 Implement contract issue detection and severity aggregation
    - Implement `detect_issues` (MINTABLE, TRANSFER_DISABLE, FEE_MODIFIABLE, OWNERSHIP_PRIVILEGE),
      force `Critical` for arbitrary transfer-disable, and `evaluate` setting
      `rating = max_by_ordinal(issues.severity, default=None)`, recording each issue
      (type/description/severity) and a UTC second-precision timestamp.
    - Implement the Solana security-semantics mapping in the `Security_Inspector`. Mint/freeze
      authority is determined **AUTHORITATIVELY from Solana RPC `getAccountInfo` on the SPL mint**
      (via `SolanaRpcAdapter`): an active **mintAuthority** -> `MINTABLE`; an active **freezeAuthority**
      -> `TRANSFER_DISABLE` and forces `Critical` (the Solana realization of an arbitrary
      transfer-disable privilege, Req 2.5); a **Token-2022 transfer-fee** extension present ->
      `FEE_MODIFIABLE`. **Moralis token metadata** (`metaplex.updateAuthority` -> `OWNERSHIP_PRIVILEGE`,
      `isMutable`, `isVerifiedContract`, `possibleSpam`, numeric score) and **Moralis Token Score** are
      **SUPPORTING risk inputs only** (NOT the authority source). `GoPlusAdapter` is an optional
      corroborating fallback when inputs are unavailable. Map these inputs to the `SecurityIssue` types
      and the Critical trigger. The `Severity` ordering and `SecurityIssue` types are unchanged
      (Properties 1-4 mappings unchanged).
    - _Requirements: 2.1, 2.4, 2.5, 2.6, 2.7, 2.8; Design: "Security_Inspector", "Solana Security Semantics"_
  - [x] 7.2 Implement unverified/timeout handling and re-evaluation on state change
    - On contract unretrievable/timeout within the limit, assign `High` and set `unverified=true`;
      implement `on_state_change` re-evaluation.
    - Remap the Req 2.9 High trigger to Solana: raise `High` with `unverified=true` (issue type
      `UNVERIFIED`) when the **SPL mint is unanalyzable/unavailable** (Solana RPC `getAccountInfo`
      fails), OR when Moralis flags **`possibleSpam` / an adverse score**, OR when the token has **both
      an active, unrenounced mint authority and freeze authority** (GoPlus optional as a corroborating
      fallback); Property 3 mapping is unchanged.
    - _Requirements: 2.9, 2.10; Design: "Security_Inspector", "Solana Security Semantics"_
  - [x] 7.3 Write property test for severity membership
    - **Property 1: Severity rating is always a member of the ordered set**
    - **Validates: Requirements 2.1**
  - [x] 7.4 Write property test for max-contributing-severity aggregation
    - **Property 2: Overall severity equals the maximum contributing severity**
    - **Validates: Requirements 2.5, 2.7, 2.4**
  - [x] 7.5 Write property test for unverified-contract rating
    - **Property 3: Unverified or unretrievable contracts rate High**
    - **Validates: Requirements 2.9**
  - [x] 7.6 Write unit tests for issue-record completeness and timestamp formatting
    - _Requirements: 2.6, 2.8_

- [x] 8. Implement Backend_Analyzer
  - [x] 8.1 Implement wallet classification, distinct count, bot percentage, and threshold alert
    - Compute distinct wallet count over the configurable window, classify each wallet as exactly one
      of BOT / NON_BOT, and compute `bot_pct = 100 * bot_txs / total_txs` (0 for empty window).
    - When `bot_pct` exceeds the user-configured bot-percentage threshold, emit a bot-threshold alert
      (dispatched via the Notifier, Task 17) identifying the Trading_Pair and the measured percentage,
      delivered within 60 seconds of the threshold being exceeded.
    - Bot/sniper detection derives from **Moralis Token Swaps** (`walletAddress`, `transactionType`,
      `bought`/`sold`, `blockTimestamp`) plus **Streams pre/postTokenBalance deltas** with custom
      heuristics; there is **no dedicated sniper API**.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5; Design: "Backend_Analyzer"_
  - [x] 8.2 Implement holder concentration, risk flag, persistence, and unavailable-data path
    - Compute top-10 holder concentration in [0,100], set concentration-risk flag when threshold
      exceeded, persist analysis with pair_id + timestamp, and on provider unavailability record an
      error result while retaining prior results and producing no new classification.
    - _Requirements: 3.6, 3.7, 3.8, 3.9; Design: "Backend_Analyzer"_
  - [x] 8.3 Write property test for distinct wallet count
    - **Property 5: Distinct wallet count equals wallet-set cardinality**
    - **Validates: Requirements 3.1, 3.4**
  - [x] 8.4 Write property test for classification partition
    - **Property 6: Wallet classification partitions all transacting wallets**
    - **Validates: Requirements 3.2**
  - [x] 8.5 Write property test for bot-transaction percentage bounds/correctness
    - **Property 7: Bot transaction percentage is bounded and correct**
    - **Validates: Requirements 3.3, 3.4**
  - [x] 8.6 Write property test for holder concentration and flagging
    - **Property 8: Holder concentration is bounded and flagged correctly**
    - **Validates: Requirements 3.6, 3.7**
  - [x] 8.7 Write unit tests for analysis-record persistence and data-unavailable path
    - _Requirements: 3.8, 3.9_

- [x] 9. Implement Metrics_Tracker
  - [x] 9.1 Implement metric recording (time-series append)
    - Append `LIQUIDITY`, `MARKET_CAP`, `FDV` per refresh and buy/sell counts and volumes per
      measurement period; each entry holds value-or-`MISSING`, second-precision timestamp, and
      pair_id; record audit provider/result/date when available; record `MISSING` when a value is
      unavailable and continue.
    - For the `AuditInfo` security metadata (Req 4.5), source it from **Solana RPC authority checks +
      Moralis metadata/Token Score** (provider label e.g. `"Moralis+SolanaRPC"`); use `GoPlusAdapter`
      only as an optional fallback (`provider = "GoPlus"`) when those inputs are unavailable, and leave
      the field null when no security metadata is available.
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.10; Design: "Metrics_Tracker", "Audit field clarification (Req 4.5)"_
  - [x] 9.2 Implement range query with validation
    - Implement `query_history` using the shared in-range primitive: reject `NOT_MONITORED`, reject
      inverted range with `INVALID_RANGE` (no mutation), and return ascending entries (possibly empty).
    - _Requirements: 4.6, 4.7, 4.8, 4.9; Design: "Metrics_Tracker"_
  - [x] 9.3 Write property test for ascending-ordered series storage
    - **Property 12: Metric series is stored in ascending timestamp order**
    - **Validates: Requirements 4.4, 4.10**
  - [x] 9.4 Write property test for in-range query correctness (covers metrics and audit)
    - **Property 13: Range queries return exactly the in-range entries, ascending**
    - **Validates: Requirements 4.6, 4.9, 10.2, 10.3**
  - [x] 9.5 Write property test for inverted-range rejection without mutation (covers metrics and audit)
    - **Property 14: Inverted time ranges are rejected without mutation**
    - **Validates: Requirements 4.7, 4.8, 10.4**
  - [x] 9.6 Write unit tests for metric-recording fields and not-monitored query error
    - _Requirements: 4.1-4.3, 4.5, 4.8_

- [x] 10. Implement Audit / persistence service
  - [x] 10.1 Implement append-only record with retry and retention enforcement
    - Implement `record(action_type, pair_id, outcome)` with millisecond UTC timestamp, retry up to
      3 times, then write a `PERSISTENCE_FAILURE` record and continue; implement `query` (reusing the
      shared in-range/inverted-range logic) and `enforce_retention` (period 30-3650 days, default 30)
      deleting exactly records older than the period.
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7; Design: "Audit / Persistence Service"_
  - [x] 10.2 Write property test for retention deletion boundary
    - **Property 15: Retention deletes exactly the records older than the period**
    - **Validates: Requirements 10.5, 10.6**
  - [x] 10.3 Write unit tests for audit record content/precision and persistence-failure record
    - _Requirements: 10.1, 10.7_

- [x] 11. Checkpoint - analysis and persistence
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement Signal_Engine
  - [x] 12.1 Implement entry scoring/eligibility and exit predicates
    - Compute entry score from security/wallet/market metrics at each Signal_Computation_Interval;
      mark eligible iff `entry_score >= entry_threshold AND severity <= max_severity`; emit `RUG_PULL`
      exit iff liquidity drop% between consecutive snapshots exceeds the rug-pull threshold; emit
      `DUMP` exit iff `sell_volume/buy_volume` (buy_volume > 0) over the single Measurement_Period
      exceeds the dump threshold; record signals with contributing metrics + timestamp.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6; Design: "Signal_Engine"_
  - [x] 12.2 Implement stale/missing-metrics skip path
    - When required metrics are stale/unavailable, skip computation, record the skipped condition,
      and retain previously generated signals.
    - _Requirements: 5.7; Design: "Signal_Engine"_
  - [x] 12.3 Write property test for entry eligibility predicate
    - **Property 16: Entry eligibility predicate**
    - **Validates: Requirements 5.2**
  - [x] 12.4 Write property test for rug-pull exit predicate
    - **Property 17: Rug-pull exit predicate**
    - **Validates: Requirements 5.3**
  - [x] 12.5 Write property test for dump exit predicate
    - **Property 18: Dump exit predicate**
    - **Validates: Requirements 5.4**
  - [x] 12.6 Write unit tests for signal record content and skip-on-stale path
    - _Requirements: 5.6, 5.7_

- [x] 13. Implement Risk_Manager (safety-critical)
  - [x] 13.1 Implement pre-trade buy approval predicate
    - Implement `approve_buy` returning approve/reject within the decision bound: reject
      `SEVERITY_EXCEEDED`, `TOTAL_EXPOSURE_EXCEEDED`, or `PER_TOKEN_EXCEEDED`; approve only when
      resulting per-token size <= limit AND resulting total exposure <= limit AND severity <= max.
      Rejections must leave all positions and total exposure unchanged.
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.7; Design: "Risk_Manager"_
  - [x] 13.2 Implement stop-loss monitoring and non-retroactive profile updates
    - Implement `monitor_stop_loss` (request full-position sell when unrealized loss% >= stop-loss%)
      and `update_profile` so updates apply only to decisions initiated after completion.
    - _Requirements: 7.5, 7.6; Design: "Risk_Manager", "Concurrency / shared-state safety"_
  - [x] 13.3 Write property test for risk approval predicate
    - **Property 19: Risk approval predicate**
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.7**
  - [x] 13.4 Write property test for rejected-order immutability
    - **Property 20: Rejected orders never change positions**
    - **Validates: Requirements 7.3, 7.4**
  - [x] 13.5 Write property test for stop-loss full-position sell trigger
    - **Property 21: Stop-loss triggers a full-position sell**
    - **Validates: Requirements 7.5**
  - [x] 13.6 Write property test for non-retroactive profile updates
    - **Property 22: Risk-profile updates do not retroactively alter decisions**
    - **Validates: Requirements 7.6**

- [x] 14. Implement Authorization_Manager (safety-critical)
  - [x] 14.1 Implement wallet connect/verify, revoke, and the trading-enabled gate
    - Implement `connect_wallet` (verify within bound -> enable trading + record `ENABLED`; else stay
      monitoring-only + surface error + record `FAILED`), `revoke` (disable trading within bound, keep
      monitoring, record `REVOKED`), and `trading_enabled()` defaulting false until an authorized
      wallet is connected. Record every status change with a timestamp.
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6; Design: "Authorization_Manager"_
  - [x] 14.2 Write unit tests for auth status-change records and monitoring-retained-after-revoke
    - _Requirements: 11.5, 11.6_

- [x] 15. Implement Trade_Executor (safety-critical)
  - [x] 15.1 Implement the monitoring-only gate and severity-presence guard
    - Submit no order unless `authz.trading_enabled()` AND automated trading is enabled (otherwise
      send a recommendation); reject any trade for a token with no assigned Severity_Rating.
    - _Requirements: 2.3, 6.1, 6.2, 6.3, 11.3; Design: "Trade_Executor", "Trade Execution with Risk Approval"_
  - [x] 15.2 Implement order submission with slippage, confirmation, and failure handling
    - Attach max slippage tolerance; submit via `TradeVenueProvider`; on confirmation record
      type/price/qty/fee/tx_id + timestamp and update position; on submission failure, confirmation
      timeout, or executed-slippage breach, cancel/record reason and leave Position and wallet balance
      unchanged; notify on failure within the bound.
    - Build the Jupiter swap transaction (serialized tx from the Swap API) and sign it via an
      **injected signer** (env-provided Solana keypair, or an external/remote KMS/HSM signer); never
      persist or log raw private keys, and never pass key material across the `TradeVenueProvider`
      boundary (the adapter receives a signing capability or a signed transaction only). API keys and
      the Telegram bot token are supplied from secrets/config. The signer path is reachable only when an
      authorized wallet is connected AND automated trading is enabled (Property 23).
    - _Requirements: 6.4, 6.5, 6.6, 6.7, 6.8; Design: "Trade_Executor", "Signer / Key Handling", "Security Considerations"_
  - [x] 15.3 Write property test for trades requiring an assigned severity rating
    - **Property 4: Trades require an assigned severity rating**
    - **Validates: Requirements 2.3**
  - [x] 15.4 Write property test for monitoring-only safety gate
    - **Property 23: Monitoring-only safety - no order without authorization and enablement**
    - **Validates: Requirements 6.3, 11.2, 11.3, 11.4**
  - [x] 15.5 Write property test for slippage attachment on submitted orders
    - **Property 24: Submitted orders carry the configured slippage tolerance**
    - **Validates: Requirements 6.4**
  - [x] 15.6 Write property test for no-side-effect on non-confirmed orders
    - **Property 25: Non-confirmed orders never change position or balance**
    - **Validates: Requirements 6.6, 6.7, 6.8**
  - [x] 15.7 Write unit test for order confirmation record fields
    - _Requirements: 6.5_
  - [x] 15.8 Implement the in-flight / idempotency guard
    - Enforce at most one in-flight order per Trading_Pair via the `InFlightRegistry`: submit no new
      buy while a Position is open or an order is in flight for that pair, and no duplicate sell while
      a sell is in flight (suppress with `SUPPRESSED_DUPLICATE_ENTRY` / duplicate-sell reason and make
      no state change); set the in-flight marker on order submit and clear it exactly when the order
      reaches a terminal status (`CONFIRMED`, `CANCELLED`, `FAILED`, `TIMED_OUT`).
    - _Requirements: 12.1, 12.2, 12.3, 12.4; Design: "Trade_Executor", "Concurrency"_
  - [x] 15.9 Implement position sizing and balance-sufficiency check
    - Derive the prepared buy size from `RiskProfile.per_order_size` (`FIXED_QUOTE` |
      `PERCENT_BALANCE`) and cap it so the resulting per-Token position and total exposure stay within
      the Risk_Profile limits; if available Quote_Asset balance is insufficient to fund the prepared
      order, submit no order, record an insufficient-balance reason, and notify.
    - _Requirements: 6.9, 6.10, 7.1, 7.2; Design: "Trade_Executor"_
  - [x] 15.10 Write property test for trade idempotency and in-flight order control
    - **Property 32: Trade idempotency and in-flight order control**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4**
  - [x] 15.11 Write property test for order sizing and balance sufficiency
    - **Property 34: Order sizing and balance sufficiency**
    - **Validates: Requirements 6.9, 6.10**

- [x] 16. Checkpoint - decision and safety-critical components
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Implement Notifier
  - [x] 17.1 Implement multi-channel dispatch, retry, quiet hours, and confirmation/severity alerts
    - Dispatch each alert to every enabled channel; per channel attempt up to 4 times (>=5s apart),
      recording final per-channel delivered/undelivered status and surfacing undelivered without
      blocking other channels; during quiet hours always deliver Critical alerts AND Exit_Signal
      alerts for any Trading_Pair in which a Position is held, suppressing only other non-Critical
      alerts; support order-confirmation messages, High/Critical severity alerts, and the configurable
      exit-signal retry budget (1-10, default 3).
    - _Requirements: 5.8, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6; Design: "Notifier", "Alerting"_
  - [x] 17.2 Write property test for bounded retry with recorded final status
    - **Property 26: Bounded retry with recorded final status**
    - **Validates: Requirements 5.8, 8.4, 8.5**
  - [x] 17.3 Write property test for dispatch to every enabled channel
    - **Property 27: Alerts are dispatched to every enabled channel**
    - **Validates: Requirements 8.3, 8.5**
  - [x] 17.4 Write property test for quiet-hours suppression preserving Critical and held-position exits
    - **Property 28: Quiet-hours suppression preserves Critical and held-position Exit_Signal alerts**
    - **Validates: Requirements 8.6**
  - [x] 17.5 Write unit test for confirmation-message content
    - _Requirements: 8.1_

- [x] 18. Implement Data_Ingestor and Monitoring Orchestrator
  - [x] 18.1 Implement Data_Ingestor watchlist add/resolve, refresh retry, and discovery scan
    - `add_token_to_watchlist` resolves pairs (reject `PAIR_NOT_FOUND` naming the token) and triggers
      security evaluation; `refresh` resets failure count on success, increments on failure while
      serving last-good, and triggers a stale notification at the 5th consecutive failure;
      `discovery_scan` adds exactly the candidate pairs first listed within the preceding 24h that
      match the filters.
    - Discovery sources candidates from **Pump.fun new tokens**
      (`GET /token/{net}/exchange/{exchange}/new`, filtered to `createdAt` < 24h) plus **token-search**;
      it does **NOT** use the deprecated discovery/filtered-tokens endpoint.
    - _Requirements: 1.1, 1.2, 1.5, 1.6, 1.7, 1.8, 1.9; Design: "Data_Ingestor"_
  - [x] 18.2 Implement Orchestrator concurrency cap, loop lifecycle, and per-tick pipeline
    - Maintain the bounded active-pair registry (atomic add: succeed iff count < 200, never exceed
      200; reject with `CONCURRENCY_LIMIT`); `remove_pair` stops the loop while repositories retain
      data; `tick` runs ingest -> analyze -> track -> signal per refresh interval with per-task
      isolation/timeouts.
    - _Requirements: 1.3, 1.4, 1.10, 1.11; Design: "Monitoring Orchestrator", "Concurrency"_
  - [x] 18.3 Write property test for the concurrency cap
    - **Property 9: Concurrency cap is never exceeded**
    - **Validates: Requirements 1.10, 1.11**
  - [x] 18.4 Write property test for discovery adding only recent, matching pairs
    - **Property 10: Discovery adds only recent, matching pairs**
    - **Validates: Requirements 1.5, 1.6**
  - [x] 18.5 Write property test for fetch-failure last-good retention and bounded retries
    - **Property 11: Fetch failures retain last-good data and bound retries**
    - **Validates: Requirements 1.8, 1.9**
  - [x] 18.6 Write unit tests for pair-not-found rejection and remove-retains-data
    - _Requirements: 1.2, 1.3, 1.4_
  - [x] 18.7 Derive the effective market-data poll interval from the rate-limiter budget
    - Using the per-provider rate limiter (Task 4.3), compute an effective market-data poll interval
      from the available budget and the active pair count, honoring the configured >=5s minimum
      (Req 1.7) as a per-pair floor and supporting >=200 active pairs (Req 1.10); the budget now
      derives from the **Moralis CU-budgeted limiter** (primary, Task 4.3), coalescing per-pair
      snapshots into **batched Moralis POST batch-metadata lookups** rather than one request per pair
      per tick (DexScreener batching applies only when its fallback is active).
    - _Requirements: 1.7, 1.10; Design: "Rate Limits & Real-Time Strategy", "Concurrency"_
  - [x] 18.8 Wire the Moralis Solana Streams intake into the Signal_Engine path
    - Consume the **Moralis Solana Streams** webhook intake (Task 4.5) as the **PRIMARY real-time
      intake** and route latency-sensitive liquidity-removal (rug) and dump events (derived from
      `preTokenBalances`/`postTokenBalances` deltas) into the Signal_Engine exit path (Req 5.3/5.4) and
      the <=5s exit alert (Req 5.5), rather than tight polling of the Moralis CU-budgeted market data;
      inject the stream/webhook client so the routing is exercised with in-memory fakes in tests.
    - _Requirements: 5.3, 5.4, 5.5; Design: "Rate Limits & Real-Time Strategy", "Per-Integration Details"_
  - [x] 18.9 Implement startup state recovery
    - Add `recover_on_startup()` that, before any trade-affecting operation, restores the persisted
      open Positions and active Watchlist: resume stop-loss and exit-signal evaluation for each
      restored Position and resume monitoring of the restored Watchlist pairs subject to the 200-pair
      cap; reconcile any non-terminal persisted order via a confirmation poll (transitioning it to a
      terminal status and clearing/keeping the in-flight marker accordingly); if the persisted state is
      unreadable, start in monitoring-only mode, surface a recovery-failure indication, and submit no
      orders until resolved.
    - _Requirements: 13.1, 13.2, 13.3, 13.4; Design: "Monitoring Orchestrator", "recover_on_startup"_
  - [x] 18.10 Write property test for startup state recovery
    - **Property 33: Startup state recovery**
    - **Validates: Requirements 13.1, 13.2, 13.3, 13.4**

- [x] 19. Integration and wiring
  - [x] 19.1 Wire all components into a runnable Agent with dependency injection
    - Compose Config_Manager, repositories, providers, analyzers, Signal_Engine, Risk_Manager,
      Authorization_Manager, Trade_Executor, Notifier, and Orchestrator; load config at startup
      (defaults when none persisted); boot in monitoring-only mode with automated trading disabled.
    - Wire the concrete Solana adapters behind their interfaces: **MoralisAdapter** (PRIMARY for
      `MarketDataProvider`/`ChainDataProvider` and `ContractInspectorProvider` risk inputs, **including
      the Moralis Solana Streams intake**, fronted by its per-provider CU-budgeted rate limiter),
      **SolanaRpcAdapter** (base on-chain fallback + **authoritative mint/freeze authority** +
      order-confirmation polling), **JupiterAdapter** (venue), and **TelegramChannel**; wire
      **DexScreenerAdapter** and **GoPlusAdapter** only as **optional fallbacks** (disabled unless
      configured). Each adapter is fronted by its per-provider rate limiter. Inject the Jupiter signer
      (env Solana keypair or external/remote signer) and supply the **Moralis API key** (also used for
      Streams), the **Solana RPC URL**, the **optional GoPlus key**, and the **Telegram bot token** from
      secrets/config (never hard-coded or logged). Provision the **publicly reachable HTTPS webhook
      endpoint** required by Moralis Solana Streams (Task 4.5). Constrain `TradingPair.quote_asset` to
      the supported quote assets **SOL** and **USDC** for the initial Solana deployment.
    - Run `Orchestrator.recover_on_startup()` (Task 18.9) **before any trade-affecting operation** so
      open Positions and the active Watchlist are restored first; wire the shared `InFlightRegistry`
      into the Trade_Executor and supply the `Per_Order_Size` (`RiskProfile.per_order_size`)
      configuration used for order sizing.
    - _Requirements: 9.5, 9.6, 11.3, 12.1-12.4, 13.1-13.4, 6.9; Design: "Architecture", "External Integrations", "Security Considerations"_
  - [x] 19.2 Write integration test for watchlist add -> monitoring begins
    - Add a resolvable token via a faked market provider; assert monitoring starts and remove stops it.
    - _Requirements: 1.1, 1.3_
  - [x] 19.3 Write integration test for the end-to-end authorized buy/sell happy path
    - With a faked venue: authorize wallet, enable trading, drive an eligible entry through Risk_Manager
      to a confirmed buy, then an exit signal to a confirmed sell, asserting confirmation notifications.
    - _Requirements: 6.1, 6.2, 8.1_
  - [x] 19.4 Write integration tests for cadence and timing behaviors
    - Discovery/refresh cadence, contract re-evaluation on state change, signal cadence, severity and
      bot-percentage alert timing, exit-signal alert timing, and stop-loss evaluation cadence using
      faked providers and a controllable clock.
    - _Requirements: 1.5, 1.7, 2.2, 2.10, 3.5, 5.1, 5.5, 7.5, 8.2_
  - [x] 19.5 Write capacity smoke test for 200 concurrent monitoring loops
    - Register 200 pairs and assert the registry stays responsive and the cap holds.
    - _Requirements: 1.10_
  - [x] 19.6 Write integration test for restart state recovery
    - Persist open Positions and an active Watchlist, restart the Agent, and assert recovery restores
      exactly those Positions (with stop-loss/exit evaluation resumed) and resumes monitoring of those
      pairs before any trade-affecting operation.
    - _Requirements: 13.1, 13.2, 13.3_
  - [x] 19.7 Write integration test for duplicate-order suppression
    - With a faked venue and an in-flight/open Position, assert a second buy/sell for the same pair is
      suppressed with no state change and the in-flight marker clears on terminal status.
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [x] 20. Final checkpoint - full suite
  - Ensure all tests pass (all 34 property tests at >= 100 iterations, plus unit and integration
    tests), ask the user if questions arise.

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "2.2"] },
    { "id": 2, "tasks": ["2.3", "3.1", "5.1"] },
    { "id": 3, "tasks": ["4.1", "5.2", "5.3", "5.4", "5.5"] },
    { "id": 4, "tasks": ["4.2"] },
    { "id": 5, "tasks": ["4.3", "4.5"] },
    { "id": 6, "tasks": ["4.4", "7.1", "8.1", "9.1", "10.1"] },
    { "id": 7, "tasks": ["7.2", "8.2", "9.2"] },
    { "id": 8, "tasks": ["7.3", "7.4", "7.5", "7.6", "8.3", "8.4", "8.5", "8.6", "8.7", "9.3", "9.4", "9.5", "9.6", "10.2", "10.3"] },
    { "id": 9, "tasks": ["12.1", "13.1", "14.1"] },
    { "id": 10, "tasks": ["12.2", "13.2", "14.2"] },
    { "id": 11, "tasks": ["12.3", "12.4", "12.5", "12.6", "13.3", "13.4", "13.5", "13.6"] },
    { "id": 12, "tasks": ["15.1", "17.1"] },
    { "id": 13, "tasks": ["15.2", "17.2", "17.3", "17.4", "17.5"] },
    { "id": 14, "tasks": ["15.8"] },
    { "id": 15, "tasks": ["15.9"] },
    { "id": 16, "tasks": ["15.3", "15.4", "15.5", "15.6", "15.7", "15.10", "15.11"] },
    { "id": 17, "tasks": ["18.1", "18.2"] },
    { "id": 18, "tasks": ["18.7"] },
    { "id": 19, "tasks": ["18.8"] },
    { "id": 20, "tasks": ["18.9"] },
    { "id": 21, "tasks": ["18.3", "18.4", "18.5", "18.6", "18.10"] },
    { "id": 22, "tasks": ["19.1"] },
    { "id": 23, "tasks": ["19.2", "19.3", "19.4", "19.5", "19.6", "19.7"] }
  ]
}
```

> **Scheduling notes.** Waves run in order; tasks within a wave are independent and may run in
> parallel. Setup/foundation (models, repos, provider interfaces/adapters, config) occupy the early
> waves; analysis, decision, and safety-critical components follow; integration and end-to-end tests
> are last. Implementation sub-tasks that edit the same component module (e.g. Trade_Executor 15.1 ->
> 15.2 -> 15.8 -> 15.9, and Orchestrator 18.2 -> 18.7 -> 18.8 -> 18.9) are placed in separate waves to
> avoid write conflicts. Test sub-tasks (including optional `*` tests) are scheduled after the code
> they exercise.

---

## Property Coverage Map (34/34)

| Property | Task |
|----------|------|
| P1, P2, P3 | 7.3, 7.4, 7.5 |
| P4 | 15.3 |
| P5, P6, P7, P8 | 8.3, 8.4, 8.5, 8.6 |
| P9, P10, P11 | 18.3, 18.4, 18.5 |
| P12, P13, P14 | 9.3, 9.4, 9.5 (P13/P14 also cover Audit 10.2-10.4) |
| P15 | 10.2 |
| P16, P17, P18 | 12.3, 12.4, 12.5 |
| P19, P20, P21, P22 | 13.3, 13.4, 13.5, 13.6 |
| P23, P24, P25 | 15.4, 15.5, 15.6 |
| P26, P27, P28 | 17.2, 17.3, 17.4 |
| P29, P30, P31 | 5.2, 5.3, 5.4 |
| P32 | 15.10 |
| P33 | 18.10 |
| P34 | 15.11 |

## Notes

- Tasks marked with `*` are optional (tests) and can be skipped for a faster MVP; core implementation
  tasks are never optional.
- Each task references specific requirement sub-clauses and design elements for traceability.
- Property tests use Hypothesis at `max_examples >= 100`, tagged
  `Feature: dex-trading-agent, Property {n}: {property_text}`, with in-memory provider fakes.
- Safety-critical components (Risk_Manager, Authorization_Manager, Trade_Executor) are implemented
  after their dependencies and gate all trading behind authorization + explicit enablement.
- This plan covers only coding, modification, and automated-testing work; no deployment, manual UAT,
  or production-operation tasks are included.
