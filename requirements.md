# Requirements Document

## Introduction

The DEX Trading Agent is an automated system that monitors, tracks, analyzes, and trades tokens on decentralized exchange (DEX) data platforms such as DEX Screener. The Agent ingests live market and on-chain data, performs token security inspection, analyzes the on-chain transaction and wallet behavior behind each token, continuously tracks market metrics (liquidity, market capitalization, fully diluted valuation, buy/sell counts and volumes, and audit status), and computes entry and exit signals intended to protect the user from rug pulls and price dumps. When authorized by the user, the Agent executes buy and sell trades on the user's behalf within user-defined risk limits.

This document defines the functional and quality requirements for the Agent. Implementation choices (specific exchanges, blockchains, data providers, machine-learning techniques, and storage technologies) are deferred to the design phase.

## Glossary

- **Agent**: The DEX Trading Agent system as a whole, encompassing all monitoring, analysis, prediction, and trading components.
- **Token**: A tradable on-chain asset identified by a unique contract address on a specific blockchain network.
- **Trading_Pair**: A market that pairs a Token with a quote asset (for example, a Token paired with a stablecoin) on a specific DEX.
- **Data_Ingestor**: The component that retrieves market and on-chain data from external data sources.
- **Security_Inspector**: The component that evaluates a Token contract for security risks and assigns a severity rating.
- **Backend_Analyzer**: The component that analyzes on-chain transactions and wallets associated with a Token.
- **Metrics_Tracker**: The component that continuously records and computes time-series market metrics for a Trading_Pair.
- **Signal_Engine**: The component that computes entry and exit signals for a Trading_Pair.
- **Trade_Executor**: The component that submits buy and sell orders to a DEX.
- **Risk_Manager**: The component that enforces user-defined position limits and risk controls.
- **Notifier**: The component that delivers alerts and status messages to the user.
- **Watchlist**: The user-defined set of Tokens or Trading_Pairs that the Agent actively monitors.
- **Severity_Rating**: A categorical risk classification assigned to a Token, with the ordered values None, Low, Medium, High, and Critical, where None is the lowest rating and Critical is the highest rating.
- **Bot_Wallet**: A wallet classified by the Backend_Analyzer as exhibiting automated trading behavior according to defined heuristics.
- **Liquidity**: The total value of assets held in a Trading_Pair's liquidity pool, expressed in the quote asset.
- **Market_Cap**: The circulating-supply market capitalization of a Token.
- **FDV**: Fully Diluted Valuation, the market capitalization of a Token assuming the total token supply is in circulation.
- **Entry_Signal**: A computed indication that recommends opening a position in a Trading_Pair.
- **Exit_Signal**: A computed indication that recommends closing an existing position in a Trading_Pair.
- **Rug_Pull**: An event in which Liquidity is removed or a contract privilege is exercised such that token holders are unable to sell at expected value.
- **Position**: An open holding of a Token resulting from an executed buy that has not yet been fully sold.
- **Risk_Profile**: The user-configured set of parameters that govern position sizing, exposure limits, and acceptable risk thresholds.
- **In_Flight_Order**: An order that has been submitted to a DEX but has not yet reached a terminal state, where a terminal state is one of confirmed, cancelled, failed, or timed out.
- **Data_Refresh_Interval**: The user-configured period at which the Data_Ingestor refreshes Trading_Pair data and the Metrics_Tracker records market metrics, between 5 seconds and 300 seconds inclusive, defaulting to 30 seconds.
- **Signal_Computation_Interval**: The user-configured period at which the Signal_Engine computes Entry_Signals and Exit_Signals, between 1 second and 300 seconds inclusive, defaulting to 15 seconds.
- **Measurement_Period**: The user-configured time span over which transaction counts, volumes, and signal comparisons are aggregated, between 60 seconds and 86400 seconds inclusive.
- **Quote_Asset**: The asset in which a Trading_Pair is priced and in which order sizes and wallet balances are denominated.
- **Per_Order_Size**: The user-configured amount allocated to a single buy order, expressed either as a fixed Quote_Asset amount or as a percentage of available Quote_Asset balance.

## Requirements

### Requirement 1: Token Discovery and Watchlist Monitoring

**User Story:** As a trader, I want the Agent to discover and continuously monitor tokens on DEX platforms, so that I can track trading opportunities without manual searching.

#### Acceptance Criteria

1. WHEN the user adds a Token to the Watchlist, THE Agent SHALL resolve the associated Trading_Pair and begin monitoring the associated Trading_Pair within 10 seconds.
2. IF the user adds a Token for which no associated Trading_Pair can be resolved, THEN THE Agent SHALL reject the addition and SHALL return an error identifying the Token.
3. WHEN the user removes a Token from the Watchlist, THE Agent SHALL stop monitoring the associated Trading_Pair.
4. WHEN the user removes a Token from the Watchlist, THE Agent SHALL retain previously collected data for the associated Trading_Pair.
5. WHERE automatic discovery is enabled, THE Data_Ingestor SHALL scan for Trading_Pairs first listed within the preceding 24 hours that match the user's defined discovery filters at the discovery scan interval, where the discovery scan interval is between 30 seconds and 300 seconds inclusive.
6. WHERE automatic discovery is enabled, WHEN a discovery scan identifies a Trading_Pair first listed within the preceding 24 hours that matches the user's defined discovery filters, THE Data_Ingestor SHALL add the Trading_Pair to the Watchlist.
7. WHILE a Trading_Pair is on the Watchlist, THE Data_Ingestor SHALL refresh the Trading_Pair data at the Data_Refresh_Interval, where the Data_Refresh_Interval is between 5 seconds and 300 seconds inclusive and defaults to 30 seconds.
8. IF the Data_Ingestor fails to retrieve data for a Trading_Pair, THEN THE Agent SHALL record the failure, retain the last successfully retrieved data, and retry retrieval at the configured interval for up to 5 consecutive attempts.
9. IF retrieval of data for a Trading_Pair fails on 5 consecutive attempts, THEN THE Notifier SHALL send a stale-data notification identifying the Trading_Pair.
10. THE Agent SHALL support monitoring at least 200 Trading_Pairs concurrently.
11. IF adding a Trading_Pair to the Watchlist would cause the number of concurrently monitored Trading_Pairs to exceed 200, THEN THE Agent SHALL reject the addition and SHALL return an error indicating the concurrency limit was reached.

### Requirement 2: Token Security and Severity Inspection

**User Story:** As a trader, I want the Agent to inspect each token's contract for security risks and assign a severity rating, so that I can avoid trading malicious or high-risk tokens.

#### Acceptance Criteria

1. THE Security_Inspector SHALL represent the Severity_Rating of a Token as exactly one value from the ordered set {None, Low, Medium, High, Critical}, where None is the lowest rating and Critical is the highest rating.
2. WHEN a Token is added to the Watchlist, THE Security_Inspector SHALL evaluate the Token contract and assign a Severity_Rating within 30 seconds.
3. IF a trade is requested for a Token to which no Severity_Rating has been assigned, THEN THE Agent SHALL reject the trade request.
4. THE Security_Inspector SHALL detect the presence of mintable supply, transfer-disabling functions, modifiable transaction fees, and ownership-privilege functions in the Token contract.
5. WHEN the Security_Inspector detects a contract privilege that allows arbitrary disabling of token transfers, THE Security_Inspector SHALL assign a Severity_Rating of Critical to the Token.
6. THE Security_Inspector SHALL record each detected security issue with its issue type, description, and contributing Severity_Rating.
7. THE Security_Inspector SHALL set the overall Severity_Rating of a Token to the highest contributing Severity_Rating among the Token's detected security issues.
8. WHEN the Security_Inspector completes an evaluation, THE Security_Inspector SHALL store the evaluation result with a UTC timestamp recorded to second-level precision.
9. IF the Token contract source code cannot be retrieved within 30 seconds, THEN THE Security_Inspector SHALL assign a Severity_Rating of High and SHALL record that the contract is unverified.
10. WHEN the Security_Inspector detects a change to the contract state of a monitored Token, THE Security_Inspector SHALL re-evaluate the Token and update the Severity_Rating within 60 seconds of detecting the change.

### Requirement 3: Token Backend and Wallet Analysis

**User Story:** As a trader, I want the Agent to analyze the wallets and transactions behind a token, so that I can understand whether trading activity is organic or driven by bots.

#### Acceptance Criteria

1. WHILE a Trading_Pair is monitored, THE Backend_Analyzer SHALL count the number of distinct wallets that transact in the Trading_Pair within a user-configured time window, where the time window is configurable between 1 minute and 1440 minutes (24 hours) inclusive.
2. THE Backend_Analyzer SHALL classify each transacting wallet as exactly one of Bot_Wallet or non-bot wallet according to the defined behavioral heuristics, such that every transacting wallet within the time window receives exactly one classification.
3. WHEN at least one transaction exists for the Trading_Pair within the configured time window, THE Backend_Analyzer SHALL compute the percentage of transactions attributable to Bot_Wallet entities as a value between 0 and 100 inclusive.
4. IF zero transactions exist for the Trading_Pair within the configured time window, THEN THE Backend_Analyzer SHALL record the Bot_Wallet transaction percentage as 0 and the distinct wallet count as 0.
5. WHEN the percentage of transactions attributable to Bot_Wallet entities exceeds a user-configured threshold (configurable between 0 and 100 inclusive), THE Notifier SHALL send, within 60 seconds of the threshold being exceeded, an alert identifying the Trading_Pair and the measured percentage.
6. THE Backend_Analyzer SHALL compute the holder concentration as the percentage, between 0 and 100 inclusive, of total token supply held by the top 10 holding wallets.
7. WHEN the holder concentration exceeds a user-configured threshold (configurable between 0 and 100 inclusive), THE Backend_Analyzer SHALL record a concentration-risk flag for the Token.
8. THE Backend_Analyzer SHALL record each wallet analysis result with the Trading_Pair identifier and a timestamp.
9. IF the data source required to retrieve wallet or transaction data is unavailable, THEN THE Backend_Analyzer SHALL record an error result indicating data unavailability for the Trading_Pair, retain any previously recorded analysis results, and produce no new classification or percentage for the affected time window.

### Requirement 4: Continuous Market Metrics Tracking

**User Story:** As a trader, I want the Agent to continuously track market metrics for each token, so that I can observe how a token's market behaves over time.

#### Acceptance Criteria

1. WHILE a Trading_Pair is monitored, THE Metrics_Tracker SHALL record Liquidity, Market_Cap, and FDV at each Data_Refresh_Interval, where the Data_Refresh_Interval is between 5 seconds and 300 seconds inclusive and defaults to 30 seconds.
2. WHILE a Trading_Pair is monitored, THE Metrics_Tracker SHALL record the count of buy transactions and the count of sell transactions for each Measurement_Period, where the Measurement_Period is between 60 seconds and 86400 seconds inclusive.
3. WHILE a Trading_Pair is monitored, THE Metrics_Tracker SHALL record the buy volume and the sell volume, expressed in the Quote_Asset, for each Measurement_Period.
4. WHEN the Metrics_Tracker records a metric value, THE Metrics_Tracker SHALL store a time-series entry containing the metric value, a timestamp recorded to second-level precision, and the Trading_Pair identifier, ordered by ascending timestamp.
5. WHERE audit information is available for a Token, THE Metrics_Tracker SHALL record the audit provider, the audit result, and the audit date.
6. WHEN the user requests metric history for a Trading_Pair over a specified time range, THE Metrics_Tracker SHALL return the recorded time-series entries within that range ordered by ascending timestamp.
7. IF the user requests metric history for a Trading_Pair over a time range whose start instant is later than its end instant, THEN THE Metrics_Tracker SHALL reject the request, return an invalid-time-range error, and leave the stored data unchanged.
8. IF the user requests metric history for a Trading_Pair that is not monitored, THEN THE Metrics_Tracker SHALL return an error indicating the Trading_Pair is not monitored and SHALL leave the stored data unchanged.
9. IF the user requests metric history for a Trading_Pair and no time-series entries fall within the specified time range, THEN THE Metrics_Tracker SHALL return an empty result set without error.
10. IF a metric value is unavailable at a Data_Refresh_Interval, THEN THE Metrics_Tracker SHALL record the value as missing for that interval and SHALL continue tracking subsequent intervals.

### Requirement 5: Entry and Exit Signal Prediction

**User Story:** As a trader, I want the Agent to predict entry and exit points and warn me before a token is wiped out, so that I can protect my capital from rug pulls and dumps.

#### Acceptance Criteria

1. WHILE a Trading_Pair is monitored, THE Signal_Engine SHALL compute an Entry_Signal and an Exit_Signal at each Signal_Computation_Interval using the recorded security, wallet, and market metrics, where the Signal_Computation_Interval is between 1 second and 300 seconds inclusive and defaults to 15 seconds.
2. WHEN the Signal_Engine computes an Entry_Signal that meets the user-configured entry threshold AND the Token Severity_Rating is at or below the user-configured maximum acceptable severity, THE Signal_Engine SHALL mark the Trading_Pair as eligible for entry.
3. WHEN Liquidity for a monitored Trading_Pair decreases by a percentage greater than the user-configured rug-pull threshold within a single Measurement_Period, where the Measurement_Period is the user-configured period between 60 seconds and 86400 seconds inclusive, THE Signal_Engine SHALL generate an Exit_Signal classified as rug-pull risk.
4. WHEN the ratio of sell volume to buy volume for a monitored Trading_Pair exceeds the user-configured dump threshold within a single Measurement_Period, where the Measurement_Period is the user-configured period between 60 seconds and 86400 seconds inclusive, THE Signal_Engine SHALL generate an Exit_Signal classified as dump risk.
5. WHEN the Signal_Engine generates an Exit_Signal for a Trading_Pair in which a Position is held, THE Notifier SHALL send an alert within 5 seconds identifying the Trading_Pair and the Exit_Signal classification.
6. THE Signal_Engine SHALL record each generated Entry_Signal and Exit_Signal with the contributing metric values and a timestamp.
7. IF the metrics required to compute signals for a Trading_Pair are unavailable or stale, THEN THE Signal_Engine SHALL skip signal computation for that Signal_Computation_Interval, record the skipped condition, and retain the previously generated signals.
8. IF delivery of an Exit_Signal alert fails, THEN THE Notifier SHALL retry delivery up to a user-configured number of attempts between 1 and 10 inclusive, defaulting to 3, and IF all attempts fail, THEN THE Notifier SHALL record the Exit_Signal alert as undelivered.

### Requirement 6: Automated Trade Execution

**User Story:** As a trader, I want the Agent to execute buy and sell trades on my behalf, so that I can act on signals without manual intervention.

#### Acceptance Criteria

1. WHERE automated trading is enabled by the user, WHEN the Signal_Engine marks a Trading_Pair as eligible for entry AND the Risk_Manager approves the trade, THE Trade_Executor SHALL submit a buy order for the Trading_Pair.
2. WHERE automated trading is enabled by the user, WHEN the Signal_Engine generates an Exit_Signal for a Trading_Pair in which a Position is held AND the Risk_Manager approves the trade, THE Trade_Executor SHALL submit a sell order for the Position.
3. WHERE automated trading is disabled, WHEN the Signal_Engine generates an Entry_Signal or Exit_Signal, THE Notifier SHALL send a trade recommendation to the user and THE Trade_Executor SHALL NOT submit an order.
4. WHEN the Trade_Executor submits an order, THE Trade_Executor SHALL apply the user-configured maximum slippage tolerance to the order.
5. WHEN an order is confirmed on-chain, THE Trade_Executor SHALL record the order type, executed price, quantity, transaction fee, and transaction identifier with a timestamp within 5 seconds of the confirmation.
6. IF an order is not confirmed on-chain within the user-configured confirmation timeout, where the confirmation timeout is between 10 seconds and 600 seconds inclusive and defaults to 60 seconds, THEN THE Trade_Executor SHALL cancel the order, record the timeout reason, and leave the Position and the wallet balance unchanged.
7. IF an order submission fails or is rejected, THEN THE Trade_Executor SHALL record the failure reason, notify the user within 5 seconds of detecting the failure, and leave the Position and the wallet balance unchanged.
8. IF the executed slippage of an order would exceed the user-configured maximum slippage tolerance, THEN THE Trade_Executor SHALL cancel the order, record the cancellation reason, and leave the Position and the wallet balance unchanged.
9. WHEN the Trade_Executor prepares a buy order, THE Trade_Executor SHALL determine the order size from the Per_Order_Size, capped so that the resulting per-Token position and total exposure remain within the Risk_Profile limits.
10. IF the available Quote_Asset wallet balance is insufficient to fund a prepared buy order, THEN THE Trade_Executor SHALL NOT submit the order, SHALL record an insufficient-balance reason, and SHALL notify the user.

### Requirement 7: Risk Management and Position Controls

**User Story:** As a trader, I want the Agent to enforce my risk limits, so that the Agent cannot expose me to more loss than I am willing to accept.

#### Acceptance Criteria

1. THE Risk_Manager SHALL maintain a Risk_Profile containing the Per_Order_Size, the maximum position size per Token, the maximum total exposure, the maximum acceptable Severity_Rating, and the stop-loss percentage, where the stop-loss percentage is a value between 0.01% and 100.00%.
2. THE Risk_Profile SHALL include a Per_Order_Size expressed either as a fixed Quote_Asset amount or as a percentage of available Quote_Asset balance.
3. WHEN the Trade_Executor requests approval for a buy order, THE Risk_Manager SHALL return an approval or rejection decision within 2 seconds, approving the order only if both the resulting position size for the Token and the resulting total exposure are less than or equal to their corresponding Risk_Profile limits.
4. IF a buy order would cause total exposure to exceed the maximum total exposure, THEN THE Risk_Manager SHALL reject the order, SHALL leave all existing positions unchanged, and SHALL record a rejection reason indicating the total exposure limit was exceeded.
5. IF a buy order would cause the position size for a Token to exceed the maximum position size per Token, THEN THE Risk_Manager SHALL reject the order, SHALL leave all existing positions unchanged, and SHALL record a rejection reason indicating the per-Token position limit was exceeded.
6. WHEN the unrealized loss percentage of a Position reaches or exceeds the configured stop-loss percentage, evaluated at an interval of at most 60 seconds, THE Risk_Manager SHALL request a sell order for the full Position from the Trade_Executor within 5 seconds of detection.
7. WHEN the user updates the Risk_Profile, THE Risk_Manager SHALL apply the updated parameters to all approval decisions initiated after the update completes, and SHALL NOT alter any approval decision already returned.
8. IF the Trade_Executor requests approval for a buy order for a Token whose Severity_Rating is higher than the maximum acceptable Severity_Rating in the Risk_Profile, THEN THE Risk_Manager SHALL reject the order and SHALL record a rejection reason indicating the Severity_Rating limit was exceeded.

### Requirement 8: Alerting and Notifications

**User Story:** As a trader, I want to receive timely alerts about significant events, so that I can stay informed about my monitored tokens and trades.

#### Acceptance Criteria

1. WHEN the Agent completes execution of a buy or sell order, THE Notifier SHALL send a confirmation message within 10 seconds containing the Trading_Pair, order type, executed price, and quantity.
2. WHEN the Security_Inspector assigns a Severity_Rating of Critical or High to a monitored Token, THE Notifier SHALL send an alert within 10 seconds of the rating being assigned.
3. WHILE a user has one or more notification channels enabled, THE Notifier SHALL deliver each alert through every enabled notification channel.
4. IF delivery of an alert through a notification channel fails, THEN THE Notifier SHALL retry delivery on that channel up to 3 additional times with an interval of at least 5 seconds between attempts, and SHALL record the final delivery status as delivered or failed for that channel.
5. IF all 4 delivery attempts on a notification channel fail, THEN THE Notifier SHALL record the alert as undelivered for that channel and SHALL surface a delivery-failure indication to the user without blocking delivery on other enabled channels.
6. WHERE the user has configured quiet hours, THE Notifier SHALL suppress alerts that are neither Critical nor Exit_Signal alerts for a Trading_Pair in which a Position is held during the configured quiet-hours window, SHALL deliver Critical alerts within 10 seconds regardless of quiet hours, and SHALL deliver Exit_Signal alerts for a Trading_Pair in which a Position is held within 10 seconds regardless of quiet hours.

### Requirement 9: Configuration Management

**User Story:** As a trader, I want to configure the Agent's thresholds and behavior, so that the Agent operates according to my strategy.

#### Acceptance Criteria

1. THE Agent SHALL allow the user to configure the following parameters within the stated inclusive ranges: the Data_Refresh_Interval between 5 seconds and 300 seconds, the Signal_Computation_Interval between 1 second and 300 seconds, the discovery scan interval between 30 seconds and 300 seconds, the Measurement_Period between 60 seconds and 86400 seconds, the bot-percentage threshold between 0 and 100 percent, the holder-concentration threshold between 0 and 100 percent, the rug-pull threshold between 0 and 100 percent, the dump threshold between 0.1 and 100, the entry threshold between 0 and 100, and the slippage tolerance between 0.01 and 100 percent.
2. IF the user submits a configuration value outside the allowed range for a parameter, THEN THE Agent SHALL reject the configuration, return a message identifying the parameter and its allowed range, and retain the active configuration.
3. IF the user submits a value that is non-numeric or missing for a parameter that requires a numeric value, THEN THE Agent SHALL reject the configuration, return a message identifying the parameter, and retain the active configuration.
4. WHEN the user saves a valid configuration, where a valid configuration is one in which every parameter value falls within its allowed range, THE Agent SHALL persist the configuration and SHALL apply the configuration to operations initiated within 5 seconds after the configuration is saved.
5. WHEN the Agent starts, THE Agent SHALL load the most recently persisted configuration.
6. WHERE no persisted configuration exists at startup, THE Agent SHALL apply documented default values for all parameters, where each default value falls within its parameter's allowed range.
7. IF persistence of a configuration fails, THEN THE Agent SHALL retain the active configuration, continue operating, and surface a persistence-failure indication to the user.

### Requirement 10: Audit Trail and Data Persistence

**User Story:** As a trader, I want a durable record of the Agent's analyses and actions, so that I can review and verify the Agent's behavior.

#### Acceptance Criteria

1. WHEN the Agent completes a security inspection, wallet analysis, signal computation, or trade execution, THE Agent SHALL persist, within 5 seconds of completion, a record containing the action type, the associated Trading_Pair, the action outcome, and a UTC timestamp with millisecond precision.
2. WHEN the user requests the action history for a Trading_Pair over a specified time range bounded by a start instant and an end instant, THE Agent SHALL return all persisted records whose timestamp falls within the inclusive range, ordered from oldest to newest timestamp.
3. IF the user requests the action history for a Trading_Pair and no persisted records fall within the specified time range, THEN THE Agent SHALL return an empty result set without error.
4. IF a requested time range has a start instant later than its end instant, THEN THE Agent SHALL reject the request and SHALL return a result indicating an invalid time range.
5. THE Agent SHALL retain each persisted record for a user-configured retention period between 30 and 3650 days inclusive, defaulting to 30 days when not configured.
6. WHEN a persisted record's age exceeds the configured retention period, THE Agent SHALL delete that record.
7. IF persistence of a record fails, THEN THE Agent SHALL retry persistence up to 3 times, and IF all retry attempts fail, THEN THE Agent SHALL persist a persistence-failure record indicating the failed action type and SHALL continue operating without interrupting in-progress operations.

### Requirement 11: Wallet Connection and Trading Authorization

**User Story:** As a trader, I want to securely authorize the Agent to trade with my wallet, so that only approved trading actions are performed with my funds.

#### Acceptance Criteria

1. WHEN the user connects a trading wallet, THE Agent SHALL verify the wallet authorization within 5 seconds before enabling trade execution.
2. IF wallet authorization verification fails or does not complete within 5 seconds, THEN THE Agent SHALL NOT enable trade execution, SHALL remain in monitoring-only mode, and SHALL surface an error indication to the user.
3. WHILE no authorized trading wallet is connected, THE Trade_Executor SHALL NOT submit any order and THE Agent SHALL operate in monitoring-only mode.
4. WHEN the user revokes trading authorization, THE Agent SHALL disable trade execution within 5 seconds.
5. WHEN the user revokes trading authorization, THE Agent SHALL retain monitoring functions.
6. WHEN a change to trading authorization status occurs, THE Agent SHALL record the change to trading authorization status with a timestamp.

### Requirement 12: Trade Idempotency and In-Flight Order Control

**User Story:** As a trader, I want the Agent to avoid submitting duplicate or overlapping orders, so that a single signal cannot result in unintended repeated trades against my wallet.

#### Acceptance Criteria

1. THE Agent SHALL maintain at most one In_Flight_Order per Trading_Pair at any time.
2. IF an entry buy is eligible for a Trading_Pair in which a Position is already open OR an In_Flight_Order already exists, THEN THE Trade_Executor SHALL NOT submit a new buy order.
3. IF an Exit_Signal fires for a Trading_Pair for which a sell order is already in flight, THEN THE Trade_Executor SHALL NOT submit a duplicate sell order.
4. WHEN an In_Flight_Order for a Trading_Pair reaches a terminal state, where a terminal state is one of confirmed, cancelled, failed, or timed out, THE Agent SHALL clear the in-flight marker for that Trading_Pair so that subsequent eligible orders may be evaluated.

### Requirement 13: State Recovery on Startup

**User Story:** As a trader, I want the Agent to recover its open positions and watchlist after a restart, so that monitoring and protective controls resume without manual intervention.

#### Acceptance Criteria

1. WHEN the Agent starts, THE Agent SHALL restore all open Positions and the active Watchlist from persistence before resuming trade-affecting operations.
2. WHEN the Agent restores an open Position at startup, THE Agent SHALL resume stop-loss monitoring and exit-signal evaluation for that Position.
3. WHEN the Agent restores the active Watchlist at startup, THE Agent SHALL resume monitoring of each previously active Trading_Pair, subject to the limit of 200 concurrently monitored Trading_Pairs.
4. IF persisted Position or Watchlist state cannot be read at startup, THEN THE Agent SHALL start in monitoring-only mode, SHALL surface a recovery-failure indication to the user, and SHALL NOT submit any order until the state is resolved.
