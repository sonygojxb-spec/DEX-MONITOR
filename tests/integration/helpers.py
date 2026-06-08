"""Shared helpers for the Agent integration tests (Task 19).

Everything here is deterministic and in-memory: a :class:`ManualClock`, a
key-free :class:`FakeSigner`, a passing/denying wallet verifier, an
auto-confirming venue fake, and a :func:`build_test_agent` factory that composes
the Agent entirely from the in-memory provider fakes. No real network / chain /
signing / secret access occurs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from dex_agent.agent import AgentProviders, AgentRepositories, build_agent
from dex_agent.execution import Signer
from dex_agent.models import (
    Configuration,
    PairSnapshot,
    PerOrderSize,
    RiskProfile,
    Severity,
    TimeWindow,
)
from dex_agent.providers.fakes import (
    FakeChainDataProvider,
    FakeContractInspectorProvider,
    FakeMarketDataProvider,
    FakeNotificationChannel,
    FakeTradeVenueProvider,
)
from dex_agent.providers.interfaces import Confirmation, SecurityInputs
from dex_agent.result import Err, Ok, Result

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

QUOTE_MINT = "So11111111111111111111111111111111111111112"  # SOL
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


class ManualClock:
    """A controllable second-precision UTC clock for cadence/timing tests."""

    def __init__(self, start: datetime = NOW) -> None:
        self._now = start

    def __call__(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now = self._now + timedelta(seconds=seconds)

    @property
    def now(self) -> datetime:
        return self._now


class FakeSigner(Signer):
    """A key-free signer that records invocations (no real cryptography)."""

    def __init__(self) -> None:
        self.sign_calls: list[str] = []

    @property
    def public_key(self) -> str:
        return "FakePubKey1111"

    def sign_transaction(self, serialized_tx: str) -> str:
        self.sign_calls.append(serialized_tx)
        return f"signed:{serialized_tx}"


def passing_verifier(wallet_id: str) -> Result[str]:
    """A wallet verifier that always authorizes (test fake)."""
    return Ok(wallet_id)


def denying_verifier(wallet_id: str) -> Result[str]:
    """A wallet verifier that always refuses (test fake)."""
    from dex_agent.errors import Unverified

    return Err(Unverified("denied", subject=wallet_id))


class AutoConfirmVenue(FakeTradeVenueProvider):
    """A venue fake that auto-confirms any submitted tx with scripted fields."""

    def __init__(
        self,
        *,
        confirmed: bool = True,
        executed_slippage: Decimal = Decimal(0),
        executed_price: Decimal = Decimal(2),
        executed_qty: Decimal = Decimal(5),
        fee: Decimal = Decimal("0.01"),
        now: datetime = NOW,
    ) -> None:
        super().__init__(now=now)
        self._confirmed = confirmed
        self._executed_slippage = executed_slippage
        self._executed_price = executed_price
        self._executed_qty = executed_qty
        self._fee = fee

    def poll_confirmation(self, tx_id, timeout):
        self.record("poll_confirmation", tx_id, timeout)
        err = self._next_error("poll_confirmation")
        if err is not None:
            return Err(err)
        return Ok(
            Confirmation(
                tx_id=tx_id,
                confirmed=self._confirmed,
                executed_price=self._executed_price,
                executed_qty=self._executed_qty,
                fee=self._fee,
                executed_slippage=self._executed_slippage,
                confirmed_at=self._now,
            )
        )


def make_config(
    *,
    refresh_interval_s: int = 30,
    signal_interval_s: int = 15,
    discovery_scan_interval_s: int = 60,
    rugpull_threshold: Decimal = Decimal(50),
    dump_threshold: Decimal = Decimal(2),
    bot_pct_threshold: Decimal = Decimal(50),
    quiet_hours: TimeWindow | None = None,
    automated_trading_enabled: bool = False,
) -> Configuration:
    return Configuration(
        discovery_scan_interval_s=discovery_scan_interval_s,
        measurement_period_s=300,
        bot_pct_threshold=bot_pct_threshold,
        holder_conc_threshold=Decimal(50),
        rugpull_threshold=rugpull_threshold,
        dump_threshold=dump_threshold,
        entry_threshold=Decimal(50),
        slippage_tolerance=Decimal(1),
        refresh_interval_s=refresh_interval_s,
        signal_interval_s=signal_interval_s,
        confirmation_timeout_s=60,
        exit_alert_retries=3,
        retention_days=30,
        automated_trading_enabled=automated_trading_enabled,
        quiet_hours=quiet_hours,
    )


def make_profile(
    *,
    per_order_size: PerOrderSize | None = None,
    max_position_per_token: Decimal = Decimal(100000),
    max_total_exposure: Decimal = Decimal(1000000),
    max_acceptable_severity: Severity = Severity.CRITICAL,
    stop_loss_pct: Decimal = Decimal(20),
) -> RiskProfile:
    return RiskProfile(
        per_order_size=per_order_size or PerOrderSize.fixed_quote(Decimal(10)),
        max_position_per_token=max_position_per_token,
        max_total_exposure=max_total_exposure,
        max_acceptable_severity=max_acceptable_severity,
        stop_loss_pct=stop_loss_pct,
    )


def make_snapshot(
    pair_id: str,
    *,
    price: Decimal = Decimal(2),
    liquidity: Decimal = Decimal(100000),
    market_cap: Decimal = Decimal(500000),
    fdv: Decimal = Decimal(600000),
    buy_count: int = 10,
    sell_count: int = 5,
    buy_volume: Decimal = Decimal(1000),
    sell_volume: Decimal = Decimal(500),
    fetched_at: datetime = NOW,
    is_stale: bool = False,
) -> PairSnapshot:
    return PairSnapshot(
        pair_id=pair_id,
        price=price,
        liquidity=liquidity,
        market_cap=market_cap,
        fdv=fdv,
        buy_count=buy_count,
        sell_count=sell_count,
        buy_volume=buy_volume,
        sell_volume=sell_volume,
        fetched_at=fetched_at,
        is_stale=is_stale,
    )


def clean_security_inputs(token_address: str) -> SecurityInputs:
    """Security inputs with no active authorities -> Severity.NONE rating."""
    return SecurityInputs(
        token_address=token_address,
        mint_authority=None,
        freeze_authority=None,
        has_transfer_fee_extension=False,
        authority_source="solana_rpc",
        possible_spam=False,
    )


class TestFakes:
    """Bundle of the in-memory provider fakes used to drive a test Agent."""

    def __init__(self) -> None:
        self.market = FakeMarketDataProvider()
        self.chain = FakeChainDataProvider()
        self.inspector = FakeContractInspectorProvider()
        self.venue = AutoConfirmVenue()
        self.channel = FakeNotificationChannel(name="test")
        self.signer = FakeSigner()


def build_test_agent(
    *,
    fakes: TestFakes | None = None,
    config: Configuration | None = None,
    risk_profile: RiskProfile | None = None,
    repositories: AgentRepositories | None = None,
    verifier=passing_verifier,
    clock: ManualClock | None = None,
    initial_quote_balance: Decimal = Decimal(0),
):
    """Compose an :class:`Agent` from in-memory fakes (no real I/O).

    Returns ``(agent, fakes, clock)`` so tests can script provider responses and
    advance the controllable clock.
    """
    fakes = fakes or TestFakes()
    clock = clock or ManualClock()
    providers = AgentProviders(
        market=fakes.market,
        chain=fakes.chain,
        contract_inspector=fakes.inspector,
        venue=fakes.venue,
        channels=[fakes.channel],
        signer=fakes.signer,
        wallet_verifier=verifier,
    )
    agent = build_agent(
        providers=providers,
        config=config,
        risk_profile=risk_profile,
        repositories=repositories,
        initial_quote_balance=initial_quote_balance,
        clock=clock,
        notifier_sleep=lambda _s: None,  # never sleep on real time in tests
    )
    return agent, fakes, clock
