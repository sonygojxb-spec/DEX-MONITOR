"""Runnable Agent assembly: dependency-injected composition of all components.

Design reference: "Architecture" (Component Diagram / Layered View), "External
Integrations", and "Security Considerations". Maps to Task 19.1 and Requirements
9.5, 9.6, 11.3, 12.1-12.4, 13.1-13.4, 6.9.

This module is the single wiring seam that composes the whole system into one
runnable :class:`Agent`:

* the **Config_Manager** (loads the latest persisted configuration at startup,
  falling back to documented defaults when none is persisted - Req 9.5/9.6);
* the twelve **repositories** (in-memory by default, injectable);
* the **providers** behind their interfaces - in tests these are the in-memory
  fakes (:mod:`dex_agent.providers.fakes`); in production they are the concrete
  Solana adapters (Moralis PRIMARY, Solana RPC authority/fallback, Jupiter venue,
  Telegram channel, optional DexScreener/GoPlus fallbacks);
* the **analyzers** (Security_Inspector, Backend_Analyzer, Metrics_Tracker);
* the **decision** layer (Signal_Engine, Risk_Manager);
* the **safety-critical** layer (Authorization_Manager, Trade_Executor) wired
  behind the shared :class:`~dex_agent.models.InFlightRegistry` (Req 12.1-12.4)
  and the Per_Order_Size from the Risk_Profile (Req 6.9);
* the **action/control** layer (Notifier, Data_Ingestor, Monitoring Orchestrator)
  plus the Moralis Solana Streams webhook intake; and
* the **Audit** service.

**Composition over inheritance / dependency injection.** Every component is
constructed from interfaces and injected callables, so the assembly supports two
modes with identical wiring:

* **Tests** pass an :class:`AgentProviders` carrying in-memory fakes (and a
  recording / passing wallet verifier and an in-memory signer), so *no* real
  network, chain, signing, or secret access occurs.
* **Production** calls :func:`build_production_agent`, which constructs the
  concrete Solana adapters from an injected :class:`AgentSecrets` (read from the
  environment) and injected transport clients, each adapter fronted by its
  per-provider rate limiter.

**Secrets** are read from an injected, environment-backed :class:`AgentSecrets`
object - never hard-coded - and are **never logged**: :class:`AgentSecrets`
redacts its values in ``repr``. The Moralis API key (also used for Streams), the
Solana RPC URL, the optional GoPlus key, and the Telegram bot token all travel
through this object. Signing is delegated to an injected
:class:`~dex_agent.execution.Signer`; raw key material never crosses the
:class:`~dex_agent.providers.interfaces.TradeVenueProvider` boundary.

**Monitoring-only boot (Req 11.3).** :meth:`Agent.boot` forces automated trading
off and leaves the trading gate closed (no wallet authorized), then runs
:meth:`MonitoringOrchestrator.recover_on_startup` **before any trade-affecting
operation** (Req 13.1) so open Positions and the active Watchlist are restored
first. Trading becomes possible only after two explicit user actions:
:meth:`Agent.connect_wallet` (authorized + verified) and
:meth:`Agent.enable_automated_trading`.
"""

from __future__ import annotations

import os
import time as _time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Callable, Mapping, Sequence

from dex_agent.analysis import BackendAnalyzer, MetricsTracker, SecurityInspector
from dex_agent.audit import AuditService
from dex_agent.config import ConfigManager
from dex_agent.control import (
    AuthorizationManager,
    DataIngestor,
    MonitoringOrchestrator,
)
from dex_agent.control.authorization_manager import Verifier
from dex_agent.decision import RiskManager, SellRequest, SignalEngine
from dex_agent.errors import Unverified
from dex_agent.execution import Signer, TradeExecutor
from dex_agent.models import (
    Configuration,
    InFlightRegistry,
    Network,
    OrderKind,
    PerOrderSize,
    PositionStatus,
    RiskProfile,
    Severity,
    TimeWindow,
    WatchlistSource,
    utc_now_seconds,
)
from dex_agent.notify import Notifier
from dex_agent.providers.interfaces import (
    ChainDataProvider,
    ContractInspectorProvider,
    MarketDataProvider,
    NotificationChannel,
    OrderRequest,
    TradeVenueProvider,
)
from dex_agent.providers.ratelimit import ProviderRateLimiter
from dex_agent.providers.streams import MoralisWebhookIntake, StreamClient
from dex_agent.repositories import (
    InMemoryAuditRepository,
    InMemoryAuthorizationRepository,
    InMemoryConfigRepository,
    InMemoryMetricsRepository,
    InMemoryOrderRepository,
    InMemoryPairRepository,
    InMemoryPositionRepository,
    InMemoryRiskProfileRepository,
    InMemorySecurityEvalRepository,
    InMemorySignalRepository,
    InMemoryTokenRepository,
    InMemoryWalletAnalysisRepository,
    InMemoryWatchlistRepository,
)
from dex_agent.repositories.interfaces import (
    AuditRepository,
    AuthorizationRepository,
    ConfigRepository,
    MetricsRepository,
    OrderRepository,
    PairRepository,
    PositionRepository,
    RiskProfileRepository,
    SecurityEvalRepository,
    SignalRepository,
    TokenRepository,
    WalletAnalysisRepository,
)
from dex_agent.result import Result

#: Quote-asset mint addresses for the supported Solana quote assets. Used to
#: build exit orders for stop-loss sells (Req 7.5) when only the quote-asset
#: symbol is known. Constrained to SOL and USDC for the initial deployment.
QUOTE_ASSET_MINTS: dict[str, str] = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
}


# ---------------------------------------------------------------------------
# Secrets (environment-backed, never logged)
# ---------------------------------------------------------------------------


@dataclass
class AgentSecrets:
    """Injected secrets for the concrete adapters (design "Security Considerations").

    Read from secrets/config (e.g. the environment) and **never hard-coded or
    logged**. ``repr`` redacts every secret value so the object can be safely
    included in diagnostics. The Moralis API key is scoped to read-only data
    access (and is also used for Streams); it grants no value-transfer
    capability - signing remains exclusively the injected
    :class:`~dex_agent.execution.Signer`.
    """

    moralis_api_key: str = ""
    solana_rpc_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    goplus_api_key: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "AgentSecrets":
        """Build secrets from environment variables (never hard-coded).

        Recognized variables: ``MORALIS_API_KEY``, ``SOLANA_RPC_URL``,
        ``TELEGRAM_BOT_TOKEN``, ``TELEGRAM_CHAT_ID``, ``GOPLUS_API_KEY``
        (optional - enables the GoPlus fallback only when present).
        """
        source = env if env is not None else os.environ
        goplus = source.get("GOPLUS_API_KEY") or None
        return cls(
            moralis_api_key=source.get("MORALIS_API_KEY", ""),
            solana_rpc_url=source.get("SOLANA_RPC_URL", ""),
            telegram_bot_token=source.get("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=source.get("TELEGRAM_CHAT_ID", ""),
            goplus_api_key=goplus,
        )

    @property
    def goplus_enabled(self) -> bool:
        """True iff a GoPlus key is configured (the fallback is opt-in)."""
        return bool(self.goplus_api_key)

    def __repr__(self) -> str:  # pragma: no cover - trivial, but security-relevant
        def _redact(value: str | None) -> str:
            return "***" if value else "<unset>"

        return (
            "AgentSecrets("
            f"moralis_api_key={_redact(self.moralis_api_key)}, "
            f"solana_rpc_url={_redact(self.solana_rpc_url)}, "
            f"telegram_bot_token={_redact(self.telegram_bot_token)}, "
            f"telegram_chat_id={_redact(self.telegram_chat_id)}, "
            f"goplus_api_key={_redact(self.goplus_api_key)})"
        )


# ---------------------------------------------------------------------------
# Injection bundles
# ---------------------------------------------------------------------------


class _InMemorySigner(Signer):
    """A benign, key-free signer for tests / dev wiring (no real keys).

    Returns a deterministic opaque "signed" string and exposes a stable public
    key. It performs no cryptography and holds no private key, so it is safe to
    use in tests; production wiring (:func:`build_production_agent`) requires an
    explicit, real :class:`~dex_agent.execution.Signer`. The signing path is
    reachable only when the monitoring-only gate is open (Property 23), so this
    default never runs in the monitoring-only boot state.
    """

    def __init__(self, public_key: str = "AgentInMemorySigner111") -> None:
        self._public_key = public_key

    @property
    def public_key(self) -> str:
        return self._public_key

    def sign_transaction(self, serialized_tx: str) -> str:
        return f"signed:{serialized_tx}"


def _deny_verifier(wallet_id: str) -> Result[object]:
    """Default wallet verifier: deny (monitoring-only stays the default).

    A real verifier (or a passing test fake) must be injected to authorize a
    wallet; the default refuses so the system cannot leave monitoring-only mode
    without an explicit, configured verification capability (Req 11.3).
    """
    from dex_agent.result import Err

    return Err(Unverified("no wallet verifier configured", subject=wallet_id))


@dataclass
class AgentProviders:
    """The injectable provider implementations behind their interfaces.

    Tests pass in-memory fakes here; :func:`build_production_agent` fills it with
    the concrete Solana adapters. The market/chain/contract/venue providers and
    the notification channels are the five external abstractions; ``signer`` is
    the injected signing capability; ``wallet_verifier`` is the
    Authorization_Manager seam; ``stream_client`` is the optional Moralis Streams
    management client.
    """

    market: MarketDataProvider
    chain: ChainDataProvider
    contract_inspector: ContractInspectorProvider
    venue: TradeVenueProvider
    channels: Sequence[NotificationChannel]
    signer: Signer | None = None
    wallet_verifier: Verifier | None = None
    stream_client: StreamClient | None = None
    rate_limiter: ProviderRateLimiter | None = None


@dataclass
class AgentRepositories:
    """The twelve durable stores (in-memory by default, injectable).

    Use :meth:`in_memory` to construct a fresh in-memory set; inject concrete
    backends per field for production. The same repository instances are shared
    across every component, so persisted state (Positions, Watchlist, orders) is
    consistent and survives an in-process "restart" (re-build with the same
    repositories) for recovery testing (Req 13.x).
    """

    tokens: TokenRepository
    pairs: PairRepository
    watchlist: WatchlistRepository
    security_eval: SecurityEvalRepository
    wallet_analysis: WalletAnalysisRepository
    metrics: MetricsRepository
    signals: SignalRepository
    positions: PositionRepository
    orders: OrderRepository
    risk_profile: RiskProfileRepository
    config: ConfigRepository
    audit: AuditRepository
    authorization: AuthorizationRepository

    @classmethod
    def in_memory(cls) -> "AgentRepositories":
        """Construct a fresh set of in-memory repositories."""
        return cls(
            tokens=InMemoryTokenRepository(),
            pairs=InMemoryPairRepository(),
            watchlist=InMemoryWatchlistRepository(),
            security_eval=InMemorySecurityEvalRepository(),
            wallet_analysis=InMemoryWalletAnalysisRepository(),
            metrics=InMemoryMetricsRepository(),
            signals=InMemorySignalRepository(),
            positions=InMemoryPositionRepository(),
            orders=InMemoryOrderRepository(),
            risk_profile=InMemoryRiskProfileRepository(),
            config=InMemoryConfigRepository(),
            audit=InMemoryAuditRepository(),
            authorization=InMemoryAuthorizationRepository(),
        )


def default_risk_profile() -> RiskProfile:
    """A conservative default Risk_Profile (Req 6.9 sizing + exposure limits).

    Trading remains gated by the monitoring-only default regardless of these
    values; they are sensible, non-zero limits so a configured deployment can
    trade once a wallet is authorized and automated trading is enabled. Callers
    typically inject their own profile.
    """
    return RiskProfile(
        per_order_size=PerOrderSize.fixed_quote(Decimal("0.1")),
        max_position_per_token=Decimal("1"),
        max_total_exposure=Decimal("5"),
        max_acceptable_severity=Severity.MEDIUM,
        stop_loss_pct=Decimal("20"),
    )


@dataclass(frozen=True)
class BootReport:
    """The outcome of :meth:`Agent.boot` (monitoring-only startup + recovery)."""

    config: Configuration
    recovery_ok: bool
    monitoring_only: bool
    restored_positions: tuple[str, ...] = ()
    resumed_watchlist: tuple[str, ...] = ()
    reconciled_orders: tuple[str, ...] = ()
    recovery_error: str | None = None


# ---------------------------------------------------------------------------
# The Agent
# ---------------------------------------------------------------------------


class Agent:
    """A fully wired, runnable DEX Trading Agent.

    Construct via :func:`build_agent` (general / fakes) or
    :func:`build_production_agent` (concrete Solana adapters). The constructor
    takes the already-wired components plus the small mutable state holders used
    for the monitoring-only gate and balance/mint lookups, so all dependency
    injection happens in the builders.
    """

    def __init__(
        self,
        *,
        config: Configuration,
        risk_profile: RiskProfile,
        config_manager: ConfigManager,
        repositories: AgentRepositories,
        providers: AgentProviders,
        notifier: Notifier,
        security_inspector: SecurityInspector,
        backend_analyzer: BackendAnalyzer,
        metrics_tracker: MetricsTracker,
        signal_engine: SignalEngine,
        risk_manager: RiskManager,
        authorization_manager: AuthorizationManager,
        trade_executor: TradeExecutor,
        data_ingestor: DataIngestor,
        orchestrator: MonitoringOrchestrator,
        audit: AuditService,
        webhook_intake: MoralisWebhookIntake,
        in_flight: InFlightRegistry,
        secrets: AgentSecrets,
        _trading_state: dict,
        _balance_state: dict,
        _watched_mints: set,
        _pair_mints: dict,
        _stop_loss_requests: list,
    ) -> None:
        self.config = config
        self.risk_profile = risk_profile
        self.config_manager = config_manager
        self.repositories = repositories
        self.providers = providers
        self.notifier = notifier
        self.security_inspector = security_inspector
        self.backend_analyzer = backend_analyzer
        self.metrics_tracker = metrics_tracker
        self.signal_engine = signal_engine
        self.risk_manager = risk_manager
        self.authorization_manager = authorization_manager
        self.trade_executor = trade_executor
        self.data_ingestor = data_ingestor
        self.orchestrator = orchestrator
        self.audit = audit
        self.webhook_intake = webhook_intake
        self.in_flight = in_flight
        self.secrets = secrets
        self._trading_state = _trading_state
        self._balance_state = _balance_state
        self._watched_mints = _watched_mints
        self._pair_mints = _pair_mints
        self._stop_loss_requests = _stop_loss_requests

    # -- startup (Req 9.5/9.6 load, 11.3 monitoring-only, 13.1 recovery) ---

    def boot(self) -> BootReport:
        """Boot in monitoring-only mode, then recover state before trading.

        Forces automated trading off and leaves the trading gate closed
        (Req 11.3), then runs :meth:`MonitoringOrchestrator.recover_on_startup`
        **before any trade-affecting operation** so open Positions and the active
        Watchlist are restored first (Req 13.1-13.3). If the persisted state is
        unreadable the Agent stays monitoring-only and the failure is surfaced
        (Req 13.4).
        """
        # Monitoring-only default: automated trading disabled at boot (Req 11.3).
        self._trading_state["automated"] = False

        recovery = self.orchestrator.recover_on_startup()
        if recovery.is_ok():
            report = recovery.value
            return BootReport(
                config=self.config,
                recovery_ok=True,
                monitoring_only=report.monitoring_only or not self._wallet_authorized(),
                restored_positions=report.restored_positions,
                resumed_watchlist=report.resumed_watchlist,
                reconciled_orders=report.reconciled_orders,
            )
        # Unreadable persisted state (Req 13.4): forced monitoring-only.
        return BootReport(
            config=self.config,
            recovery_ok=False,
            monitoring_only=True,
            recovery_error=str(recovery.error),
        )

    # -- authorization + trading gate (Req 11.x, 6.3) ----------------------

    def connect_wallet(self, wallet_id: str):
        """Connect + verify a trading wallet (Req 11.1/11.2)."""
        return self.authorization_manager.connect_wallet(wallet_id)

    def revoke_wallet(self):
        """Revoke trading authorization, retaining monitoring (Req 11.4/11.5)."""
        return self.authorization_manager.revoke()

    def enable_automated_trading(self) -> None:
        """Enable automated trading (still gated by wallet authorization, Req 6.3)."""
        self._trading_state["automated"] = True

    def disable_automated_trading(self) -> None:
        """Disable automated trading (return to monitoring-only execution)."""
        self._trading_state["automated"] = False

    @property
    def automated_trading_enabled(self) -> bool:
        """Whether automated trading has been explicitly enabled by the user."""
        return bool(self._trading_state["automated"])

    def trading_allowed(self) -> bool:
        """True iff an order may be submitted right now (all gates open).

        Requires an authorized wallet (Req 11.3), automated trading enabled
        (Req 6.3), and a resolved startup recovery (Req 13.4).
        """
        return (
            self._wallet_authorized()
            and self.automated_trading_enabled
            and self.orchestrator.trading_allowed()
        )

    def _wallet_authorized(self) -> bool:
        return self.authorization_manager.trading_enabled()

    # -- watchlist / monitoring (Req 1.x) ----------------------------------

    def add_token(
        self,
        token_address: str,
        network: Network = Network.SOLANA,
        *,
        source: WatchlistSource = WatchlistSource.MANUAL,
    ):
        """Add a Token to the Watchlist and begin monitoring it (Req 1.1).

        On success the resolved pair's mint is registered for Moralis Streams
        routing (Req 5.3-5.5) and recorded for stop-loss exit-order building.
        """
        result = self.data_ingestor.add_token_to_watchlist(
            token_address, network, source=source
        )
        if result.is_ok():
            pair_id = result.value.pair_id
            self._register_pair_mint(pair_id, token_address)
        return result

    def remove_pair(self, pair_id: str) -> None:
        """Stop monitoring ``pair_id`` while repositories retain its data (Req 1.3/1.4)."""
        self.orchestrator.remove_pair(pair_id)

    def is_monitoring(self, pair_id: str) -> bool:
        """True iff ``pair_id`` is currently being monitored."""
        return self.orchestrator.is_active(pair_id)

    def tick(self, pair_id: str):
        """Run one monitoring tick for ``pair_id`` (ingest/analyze/track/signal)."""
        return self.orchestrator.tick(pair_id)

    # -- balances + mint registration (sizing / stream routing) ------------

    def set_quote_balance(self, amount: Decimal) -> None:
        """Set the available Quote_Asset balance used for sizing (Req 6.9/6.10)."""
        self._balance_state["available"] = Decimal(amount)

    @property
    def quote_balance(self) -> Decimal:
        """The current available Quote_Asset balance."""
        return self._balance_state["available"]

    def register_pair_mints(
        self, pair_id: str, token_mint: str, quote_mint: str
    ) -> None:
        """Record the (token, quote) mints for a pair (stop-loss exit orders)."""
        self._pair_mints[pair_id] = (token_mint, quote_mint)
        self._watched_mints.add(token_mint)
        self.orchestrator.register_mint(token_mint, pair_id)

    def _register_pair_mint(self, pair_id: str, token_address: str) -> None:
        """Register the watched mint for stream routing and derive the quote mint."""
        self._watched_mints.add(token_address)
        self.orchestrator.register_mint(token_address, pair_id)
        quote_mint = None
        pair = self.repositories.pairs.get(pair_id)
        if pair.is_ok():
            quote_mint = QUOTE_ASSET_MINTS.get(pair.value.quote_asset)
        self._pair_mints[pair_id] = (token_address, quote_mint)

    @property
    def stop_loss_requests(self) -> tuple[SellRequest, ...]:
        """The stop-loss sell requests raised so far (Req 7.5)."""
        return tuple(self._stop_loss_requests)

    @property
    def monitoring_only(self) -> bool:
        """True iff the Agent must not submit orders right now."""
        return not self.trading_allowed()


# ---------------------------------------------------------------------------
# Builder (general / fakes) - the core dependency-injected composition
# ---------------------------------------------------------------------------


def build_agent(
    *,
    providers: AgentProviders,
    config: Configuration | None = None,
    risk_profile: RiskProfile | None = None,
    repositories: AgentRepositories | None = None,
    secrets: AgentSecrets | None = None,
    initial_quote_balance: Decimal = Decimal(0),
    bot_window_minutes: int = 60,
    clock: Callable[[], datetime] = utc_now_seconds,
    notifier_sleep: Callable[[float], None] = _time.sleep,
) -> Agent:
    """Compose all components into a runnable :class:`Agent` (Task 19.1).

    The ``providers`` bundle injects the five external abstractions (in-memory
    fakes for tests, concrete adapters for production), the signer, the wallet
    verifier, and the optional streams client. Configuration is loaded at
    startup from the injected :class:`ConfigManager` - the latest persisted
    config, or documented defaults when none is persisted (Req 9.5/9.6) - unless
    an explicit ``config`` is supplied. The shared
    :class:`~dex_agent.models.InFlightRegistry` is wired into the Trade_Executor
    (Req 12.1-12.4) and the Risk_Profile's Per_Order_Size drives sizing (Req 6.9).
    The Agent boots monitoring-only (automated trading disabled) until
    :meth:`Agent.boot` runs recovery and the user authorizes a wallet + enables
    trading (Req 11.3).

    No real network / chain / signing / secret access occurs here: everything is
    behind interfaces and injected callables.
    """
    repos = repositories if repositories is not None else AgentRepositories.in_memory()
    secrets = secrets if secrets is not None else AgentSecrets()
    signer: Signer = providers.signer if providers.signer is not None else _InMemorySigner()
    verifier: Verifier = (
        providers.wallet_verifier
        if providers.wallet_verifier is not None
        else _deny_verifier
    )

    config_manager = ConfigManager(repos.config)
    if config is None:
        # Req 9.5/9.6: latest persisted configuration, or documented defaults.
        config = config_manager.load_at_startup().value
    else:
        config_manager._active = config  # noqa: SLF001 - wiring the active config

    risk_profile = risk_profile if risk_profile is not None else default_risk_profile()
    repos.risk_profile.save(risk_profile)

    # Mutable wiring state (monitoring-only gate, balance, mint maps).
    trading_state: dict = {"automated": bool(config.automated_trading_enabled)}
    balance_state: dict = {"available": Decimal(initial_quote_balance)}
    watched_mints: set = set()
    pair_mints: dict = {}
    stop_loss_requests: list = []
    # Lazy holders for circular references resolved during wiring.
    holders: dict = {}

    # -- shared closures (depend only on repositories) ---------------------
    def position_held(pair_id: str | None) -> bool:
        if pair_id is None:
            return False
        found = repos.positions.get(pair_id)
        return found.is_ok() and found.value.status == PositionStatus.OPEN

    def severity_for(token_address: str) -> Severity | None:
        latest = repos.security_eval.latest(token_address)
        if latest.is_ok():
            return latest.value.rating
        return None

    # -- Notifier (action layer) ------------------------------------------
    notifier = Notifier(
        channels=providers.channels,
        position_held=position_held,
        quiet_hours=config.quiet_hours,
        exit_alert_retries=config.exit_alert_retries,
        clock=clock,
        sleep=notifier_sleep,
    )

    def alert_sink(alert) -> None:
        notifier.send(alert)

    # -- analyzers --------------------------------------------------------
    security_inspector = SecurityInspector(
        providers.contract_inspector,
        repos.security_eval,
        clock=clock,
    )
    backend_analyzer = BackendAnalyzer(
        providers.chain,
        repos.wallet_analysis,
        window_minutes=bot_window_minutes,
        bot_pct_threshold=config.bot_pct_threshold,
        holder_conc_threshold=config.holder_conc_threshold,
        alert_sink=alert_sink,
        clock=clock,
    )
    metrics_tracker = MetricsTracker(repos.metrics)

    # -- decision layer ---------------------------------------------------
    signal_engine = SignalEngine(
        repos.signals,
        config,
        max_severity=risk_profile.max_acceptable_severity,
        position_held=position_held,
        alert_sink=alert_sink,
        clock=clock,
    )

    def on_stop_loss_sell(request: SellRequest) -> None:
        # Record the request (Req 7.5) and, when the trade venue + mints are
        # known and the gate is open, dispatch the full-position exit sell.
        stop_loss_requests.append(request)
        executor = holders.get("executor")
        mints = pair_mints.get(request.pair_id)
        if executor is None or mints is None:
            return
        _token_mint, quote_mint = mints
        if quote_mint is None:
            return
        executor.submit_exit(
            OrderRequest(
                pair_id=request.pair_id,
                kind=OrderKind.SELL,
                input_mint=request.token_address,
                output_mint=quote_mint,
                amount=request.quantity,
                max_slippage=config.slippage_tolerance,
            )
        )

    risk_manager = RiskManager(
        risk_profile,
        repos.positions,
        sell_requester=on_stop_loss_sell,
        profile_repo=repos.risk_profile,
        eval_interval_s=60,
        clock=clock,
    )

    # -- safety-critical layer --------------------------------------------
    authorization_manager = AuthorizationManager(
        repos.authorization,
        verifier,
        clock=clock,
    )

    in_flight = InFlightRegistry()

    def trading_gate() -> bool:
        return authorization_manager.trading_enabled()

    def automated_flag() -> bool:
        orch = holders.get("orch")
        recovery_ok = orch.trading_allowed() if orch is not None else True
        return bool(trading_state["automated"]) and recovery_ok

    trade_executor = TradeExecutor(
        venue=providers.venue,
        signer=signer,
        risk_manager=risk_manager,
        positions=repos.positions,
        orders=repos.orders,
        trading_enabled=trading_gate,
        automated_trading_enabled=automated_flag,
        severity_for=severity_for,
        available_quote_balance=lambda: balance_state["available"],
        max_slippage=config.slippage_tolerance,
        alert_sink=alert_sink,
        in_flight=in_flight,
        confirmation_timeout_s=config.confirmation_timeout_s,
        clock=clock,
    )
    holders["executor"] = trade_executor

    # -- control layer ----------------------------------------------------
    def admit(pair_id: str):
        return holders["orch"].add_pair(pair_id)

    data_ingestor = DataIngestor(
        providers.market,
        repos.watchlist,
        repos.pairs,
        token_repo=repos.tokens,
        security_inspector=security_inspector,
        metrics_tracker=metrics_tracker,
        stale_sink=alert_sink,
        admit=admit,
        clock=clock,
    )

    orchestrator = MonitoringOrchestrator(
        config=config,
        ingestor=data_ingestor,
        watchlist_repo=repos.watchlist,
        positions_repo=repos.positions,
        orders_repo=repos.orders,
        signal_repo=repos.signals,
        security=repos.security_eval,
        wallet_analyzer=backend_analyzer,
        metrics_tracker=metrics_tracker,
        signal_engine=signal_engine,
        authz=authorization_manager,
        venue=providers.venue,
        in_flight=in_flight,
        rate_limiter=providers.rate_limiter,
        alert_sink=alert_sink,
        position_held=lambda pid: position_held(pid),
        pair_repo=repos.pairs,
        clock=clock,
    )
    holders["orch"] = orchestrator

    # -- real-time streams intake (Req 5.3-5.5) ---------------------------
    webhook_intake = MoralisWebhookIntake(
        orchestrator.build_stream_sink(),
        watched_mints=watched_mints,
    )

    # -- audit ------------------------------------------------------------
    audit = AuditService(repos.audit, retention_days=config.retention_days)

    return Agent(
        config=config,
        risk_profile=risk_profile,
        config_manager=config_manager,
        repositories=repos,
        providers=providers,
        notifier=notifier,
        security_inspector=security_inspector,
        backend_analyzer=backend_analyzer,
        metrics_tracker=metrics_tracker,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        authorization_manager=authorization_manager,
        trade_executor=trade_executor,
        data_ingestor=data_ingestor,
        orchestrator=orchestrator,
        audit=audit,
        webhook_intake=webhook_intake,
        in_flight=in_flight,
        secrets=secrets,
        _trading_state=trading_state,
        _balance_state=balance_state,
        _watched_mints=watched_mints,
        _pair_mints=pair_mints,
        _stop_loss_requests=stop_loss_requests,
    )


# ---------------------------------------------------------------------------
# Builder (production) - concrete Solana adapters behind the interfaces
# ---------------------------------------------------------------------------


def build_production_agent(
    *,
    secrets: AgentSecrets,
    http_client,
    rpc_client,
    signer: Signer,
    webhook_url: str,
    risk_profile: RiskProfile | None = None,
    repositories: AgentRepositories | None = None,
    enable_dexscreener_fallback: bool = False,
    moralis_cu_per_minute: float = 40000.0,
    config: Configuration | None = None,
    initial_quote_balance: Decimal = Decimal(0),
    clock: Callable[[], datetime] = utc_now_seconds,
) -> Agent:
    """Wire the concrete Solana adapters and build a production :class:`Agent`.

    Composition (design "External Integrations"):

    * **MoralisAdapter** (PRIMARY) backs ``MarketDataProvider`` /
      ``ChainDataProvider`` and supplies security risk inputs, fronted by its
      per-provider **CU-budgeted** rate limiter
      (:meth:`ProviderRateLimiter.moralis`, charged via
      :func:`~dex_agent.providers.ratelimit.moralis_cu_for`).
    * **SolanaRpcAdapter** is the base on-chain fallback for chain reads, the
      **authoritative** SPL mint/freeze-authority source (so it is the primary
      ``ContractInspectorProvider``), and the order-confirmation polling path.
    * **DexScreenerAdapter** (market) and **GoPlusAdapter** (contract inspection)
      are wired only as **optional fallbacks**, disabled unless configured
      (DexScreener via ``enable_dexscreener_fallback``; GoPlus when
      ``secrets.goplus_api_key`` is present).
    * **JupiterAdapter** is the trade venue and **TelegramChannel** the
      notification channel.

    Secrets (Moralis API key - also used for Streams, Solana RPC URL, optional
    GoPlus key, Telegram bot token) come from the injected ``secrets`` and are
    never hard-coded or logged. The injected ``signer`` performs all signing;
    raw key material never crosses the venue boundary. The Streams webhook is
    provisioned at ``webhook_url`` (the publicly reachable HTTPS endpoint).
    """
    from dex_agent.providers.adapters import (
        DexScreenerAdapter,
        GoPlusAdapter,
        JupiterAdapter,
        MoralisAdapter,
        SolanaRpcAdapter,
        TelegramChannel,
    )
    from dex_agent.providers.ratelimit import (
        RateLimitedHttpClient,
        moralis_cu_for,
    )
    from dex_agent.providers.selection import (
        FallbackChainDataProvider,
        FallbackContractInspectorProvider,
        FallbackMarketDataProvider,
    )

    # Moralis fronted by its CU-budgeted rate limiter (Task 4.3 / 18.7).
    moralis_limiter = ProviderRateLimiter.moralis(
        cu_per_window=moralis_cu_per_minute, window_seconds=60.0, clock=_time.monotonic
    )
    moralis_http = RateLimitedHttpClient(
        http_client, moralis_limiter, cost_fn=moralis_cu_for
    )
    moralis = MoralisAdapter(moralis_http, secrets.moralis_api_key)

    # Solana RPC: authoritative authority + base chain fallback + confirmation.
    solana_rpc = SolanaRpcAdapter(rpc_client, clock=clock)

    # Market: Moralis primary, optional DexScreener fallback (disabled default).
    market_fallback = (
        DexScreenerAdapter(http_client, clock=clock)
        if enable_dexscreener_fallback
        else None
    )
    market: MarketDataProvider = FallbackMarketDataProvider(moralis, market_fallback)

    # Chain: Moralis primary, Solana RPC base fallback.
    chain: ChainDataProvider = FallbackChainDataProvider(moralis, solana_rpc)

    # Contract inspection: Solana RPC authoritative authority, optional GoPlus.
    goplus = (
        GoPlusAdapter(http_client, api_key=secrets.goplus_api_key)
        if secrets.goplus_enabled
        else None
    )
    contract_inspector: ContractInspectorProvider = FallbackContractInspectorProvider(
        solana_rpc, goplus
    )

    # Trade venue: Jupiter, with confirmation polled via Solana RPC. The signer
    # lives in the Trade_Executor; only a signed transaction crosses this seam.
    venue: TradeVenueProvider = JupiterAdapter(
        http_client,
        confirm_poller=solana_rpc.poll_signature,
        clock=clock,
    )

    # Notification channel: Telegram.
    telegram = TelegramChannel(
        http_client,
        bot_token=secrets.telegram_bot_token,
        chat_id=secrets.telegram_chat_id,
    )

    providers = AgentProviders(
        market=market,
        chain=chain,
        contract_inspector=contract_inspector,
        venue=venue,
        channels=[telegram],
        signer=signer,
        wallet_verifier=None,  # supply a real verifier to leave monitoring-only
        rate_limiter=moralis_limiter,
    )

    return build_agent(
        providers=providers,
        config=config,
        risk_profile=risk_profile,
        repositories=repositories,
        secrets=secrets,
        initial_quote_balance=initial_quote_balance,
        clock=clock,
    )


__all__ = [
    "Agent",
    "AgentSecrets",
    "AgentProviders",
    "AgentRepositories",
    "BootReport",
    "build_agent",
    "build_production_agent",
    "default_risk_profile",
    "QUOTE_ASSET_MINTS",
]
