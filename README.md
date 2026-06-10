# DEX Trading Agent

An autonomous monitoring, analysis, and trading agent for tokens on Solana decentralized exchanges. Built with a safety-first architecture — monitoring-only by default, trading only when explicitly authorized.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Tests](https://img.shields.io/badge/tests-394%20passed-green.svg)
![Properties](https://img.shields.io/badge/correctness%20properties-34-purple.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

## What it does

- **Token Discovery** — automatically discovers new tokens on Pump.fun and other Solana DEXs (< 24h old)
- **Security Inspection** — detects mint authority, freeze authority, Token-2022 fee extensions, and ownership privileges via Solana RPC; assigns severity ratings (None → Critical)
- **Wallet & Bot Analysis** — classifies transacting wallets as bot/organic, computes bot-transaction percentages, and flags holder concentration risk (top-10 wallets)
- **Market Metrics Tracking** — records liquidity, market cap, FDV, buy/sell counts and volumes as time-series data
- **Entry/Exit Signal Prediction** — computes entry signals from combined security + wallet + market data; detects rug-pull (liquidity drain) and dump (sell/buy volume ratio) exit conditions
- **Automated Trade Execution** — executes Jupiter swaps with slippage protection, risk limits, stop-loss, and in-flight order control (only when explicitly enabled)
- **Real-Time Alerts** — Telegram notifications for security threats, signal events, and trade confirmations
- **Desktop GUI** — native dark-mode desktop app with live watchlist, alerts log, and settings

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DEX Trading Agent                         │
├─────────────────────────────────────────────────────────────┤
│  Ingestion    │ Moralis API (primary) + Solana RPC          │
│  Real-Time    │ Moralis Solana Streams (webhooks)           │
│  Analysis     │ Security Inspector, Backend Analyzer,       │
│               │ Metrics Tracker                             │
│  Decision     │ Signal Engine, Risk Manager                 │
│  Execution    │ Jupiter Adapter (swap), Trade Executor      │
│  Alerts       │ Telegram Bot + GUI Channel                  │
│  Persistence  │ In-memory repositories + audit trail        │
└─────────────────────────────────────────────────────────────┘
```

## Safety Guardrails

| Guardrail | How it works |
|-----------|-------------|
| Monitoring-only default | Agent boots with `automated_trading_enabled=False` and no wallet connected |
| Explicit authorization | Two deliberate user actions required: connect wallet + enable trading |
| Risk limits | Every buy gated by per-token position limit, total exposure limit, and severity ceiling |
| Stop-loss | Automatic sell when unrealized loss exceeds configured threshold |
| Slippage protection | Orders cancelled if executed slippage exceeds tolerance |
| Trade idempotency | At most one in-flight order per trading pair; no duplicate buys/sells |
| State recovery | Open positions and watchlist restored on restart |
| No-key-storage | Private keys never persisted or logged; signing via injected signer |

## Quick Start

### Prerequisites

- Python 3.11+
- Moralis API key ([get one here](https://admin.moralis.com/))
- Solana RPC endpoint (public `https://api.mainnet-beta.solana.com` or a paid provider)
- Telegram bot token (from [@BotFather](https://t.me/BotFather))

### Installation

```bash
git clone https://github.com/sonygojxb-spec/DEX-MONITOR.git
cd DEX-MONITOR
python -m venv .venv
.venv/Scripts/activate      # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -e ".[test]"
pip install httpx python-dotenv customtkinter
```

### Configuration

Create a `.env` file in the project root (never commit this):

```env
MORALIS_API_KEY=your_moralis_api_key
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Optional
GOPLUS_API_KEY=your_goplus_key
WEBHOOK_URL=https://your-domain.com/webhook
SEED_TOKENS=DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263
```

### Run

**Desktop App (GUI):**
```bash
python -m dex_agent.gui
```

**Command Line:**
```bash
python -m dex_agent
```

Both start in monitoring-only mode — no trading possible without explicit wallet connection.

## Project Structure

```
dex_agent/
├── __main__.py              # CLI entry point
├── agent.py                 # Agent composition & build_production_agent()
├── result.py                # Result[T] type (Ok/Err discriminated union)
├── errors.py                # Typed error taxonomy
├── models/                  # Data models & enums
│   ├── market.py            #   Token, TradingPair, PairSnapshot, Network
│   ├── security.py          #   Severity, SecurityIssue, SecurityEvaluation
│   ├── wallet.py            #   WalletClassification, WalletAnalysis
│   ├── metrics.py           #   MetricKind, MetricEntry, AuditInfo
│   ├── signal.py            #   Signal, SignalType, ExitClass
│   ├── position.py          #   Position, PerOrderSize, RiskProfile
│   ├── order.py             #   OrderRecord, OrderStatus, InFlightRegistry
│   ├── config.py            #   Configuration (all params + ranges)
│   ├── audit.py             #   AuditRecord, ActionType
│   └── auth.py              #   AuthStatus, AuthorizationRecord
├── providers/
│   ├── interfaces.py        # MarketDataProvider, ChainDataProvider, etc.
│   ├── clients.py           # HttpClient / RpcClient transport protocols
│   ├── fakes.py             # In-memory fakes for testing
│   ├── ratelimit.py         # CU-budgeted per-provider rate limiter
│   ├── selection.py         # Fallback/provider-selection strategy
│   ├── streams.py           # Moralis Solana Streams webhook intake
│   └── adapters/
│       ├── moralis.py       #   MoralisAdapter (PRIMARY: market + chain + security)
│       ├── solana_rpc.py    #   SolanaRpcAdapter (authority + fallback + confirmation)
│       ├── jupiter.py       #   JupiterAdapter (trade execution)
│       ├── telegram.py      #   TelegramChannel (notifications)
│       ├── dexscreener.py   #   DexScreenerAdapter (optional fallback)
│       └── goplus.py        #   GoPlusAdapter (optional fallback)
├── analysis/
│   ├── security_inspector.py    # Severity rating from mint/freeze authority
│   ├── backend_analyzer.py      # Bot-wallet classification + concentration
│   └── metrics_tracker.py       # Time-series market metrics
├── decision/
│   ├── signal_engine.py     # Entry/exit signal computation
│   └── risk_manager.py      # Pre-trade approval + stop-loss
├── execution/
│   └── trade_executor.py    # Order submission with safety guards
├── control/
│   ├── orchestrator.py      # Monitoring loop + concurrency cap (200 pairs)
│   ├── data_ingestor.py     # Watchlist management + discovery scans
│   └── authorization_manager.py  # Wallet connection + trading gate
├── notify/
│   └── notifier.py          # Multi-channel alerts with retry + quiet hours
├── config/
│   └── manager.py           # Parameter validation + persistence
├── audit/
│   └── service.py           # Append-only audit trail + retention
└── gui/
    ├── __main__.py          # GUI entry point
    ├── app.py               # DEXMonitorApp root window
    ├── thread.py            # AgentThread + AgentState + WatchlistRow
    ├── channel.py           # GUIChannel (NotificationChannel for in-app alerts)
    ├── frames/
    │   ├── status_bar.py    #   Active pairs, uptime, last tick, alerts count
    │   ├── watchlist.py     #   Token table with severity/bot%/liquidity/signals
    │   ├── token_input.py   #   Add/remove token input
    │   ├── alerts_log.py    #   Scrollable alerts history
    │   └── controls.py      #   Start/Stop/Settings buttons
    └── dialogs/
        └── settings.py      #   Configuration dialog (all thresholds)
```

## External Integrations

| Provider | Role | Endpoint |
|----------|------|----------|
| **Moralis** (PRIMARY) | Market data, holders, swaps, Token Score, Streams | solana-gateway.moralis.io + deep-index.moralis.io |
| **Solana RPC** | Mint/freeze authority (authoritative), supply, confirmation | api.mainnet-beta.solana.com |
| **Moralis Streams** | Real-time rug/dump detection via webhooks | api.moralis-streams.com |
| **Jupiter** | Swap execution + price quotes | dev.jup.ag |
| **Telegram** | Alert notifications | api.telegram.org |
| **DexScreener** _(optional)_ | Market data fallback | docs.dexscreener.com |
| **GoPlus** _(optional)_ | Security signal corroboration | docs.gopluslabs.io |

## Testing

```bash
# Run the full test suite (394 tests)
pytest

# Run with verbose output
pytest -v

# Run only property-based tests
pytest -k "property" -v

# Run a specific test module
pytest tests/analysis/test_security_inspector.py -v
```

### Test Strategy

- **34 Correctness Properties** — verified by Hypothesis property-based tests (100+ iterations each)
- **Unit tests** — record completeness, error paths, edge cases
- **Integration tests** — end-to-end workflows, timing, capacity (200 pairs)
- All tests use **in-memory fakes** — no real network/chain calls in tests

### Key Properties Verified

| # | Property | What it guarantees |
|---|----------|-------------------|
| 1 | Severity membership | Rating is always in {None, Low, Medium, High, Critical} |
| 9 | Concurrency cap | Active pairs never exceeds 200 |
| 17 | Rug-pull predicate | Exit signal fires iff liquidity drops > threshold |
| 19 | Risk approval | Buy approved iff within per-token + total exposure + severity limits |
| 23 | Monitoring-only safety | No order submitted without authorization + enablement |
| 25 | Non-confirmed orders | Failed/timed-out orders never change position or balance |
| 32 | Trade idempotency | At most one in-flight order per pair; no duplicates |
| 33 | Startup recovery | Positions and watchlist restored correctly on restart |

(See `.kiro/specs/dex-trading-agent/design.md` for all 34 properties)

## Spec Documentation

The full formal specification lives in `.kiro/specs/dex-trading-agent/`:

- **requirements.md** — 13 EARS-format requirements with testable acceptance criteria
- **design.md** — architecture, data models, component interfaces, 34 correctness properties, Moralis endpoint reference, security considerations
- **tasks.md** — 20 implementation tasks with dependency graph and property coverage map

## Configuration Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| refresh_interval_s | 5–300 | 30 | Market data polling interval |
| signal_interval_s | 1–300 | 15 | Signal computation interval |
| discovery_scan_interval_s | 30–300 | 60 | New token discovery scan cadence |
| measurement_period_s | 60–86400 | 3600 | Aggregation window for volumes/counts |
| bot_pct_threshold | 0–100 | 50 | Bot % alert threshold |
| holder_conc_threshold | 0–100 | 50 | Top-10 holder concentration alert |
| rugpull_threshold | 0–100 | 50 | Liquidity drop % for rug-pull exit |
| dump_threshold | 0.1–100 | 50 | Sell/buy volume ratio for dump exit |
| entry_threshold | 0–100 | 50 | Entry signal score threshold |
| slippage_tolerance | 0.01–100 | 1 | Max acceptable slippage % |
| confirmation_timeout_s | 10–600 | 60 | On-chain confirmation timeout |
| exit_alert_retries | 1–10 | 3 | Exit alert delivery retry count |
| retention_days | 30–3650 | 30 | Audit record retention period |

## Security

- **API keys** loaded from `.env` (gitignored), never hard-coded
- **Private keys** never stored — signing via injected signer abstraction
- **Monitoring-only default** — physically cannot trade without explicit enablement
- **Untrusted data** — all provider responses validated and range-checked
- **Audit trail** — every analysis and action persisted with UTC timestamps

## Roadmap

- [x] Monitoring-only MVP (discovery, security, metrics, signals, alerts)
- [x] Desktop GUI (CustomTkinter dark-mode app)
- [x] Safety-critical trading components (Risk Manager, Trade Executor)
- [ ] Live trading validation (devnet testing)
- [ ] Signal scoring tuning with real market data
- [ ] Web dashboard (FastAPI + frontend)
- [ ] Multi-chain support (EVM chains via new adapters)

## License

MIT

---

**⚠️ Warning:** This agent can trade real funds when trading is enabled. Always:
- Start in monitoring-only mode and observe for days/weeks
- Use a dedicated bot wallet with limited funds
- Test on devnet or with tiny amounts before real capital
- The entry signal scoring needs real-world tuning — the framework is correct, but weights need market observation to refine
