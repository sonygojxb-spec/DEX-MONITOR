"""Unit tests for the in-memory provider fakes (Task 4.1).

Verifies scriptable responses, injectable failures/timeouts, and recorded
calls for each provider fake, plus that the fakes satisfy their interfaces.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from dex_agent.errors import NotFound, ProviderError, TimedOut
from dex_agent.models import HolderBalance, Network, OrderKind, PairSnapshot
from dex_agent.providers import (
    Alert,
    ChainDataProvider,
    ContractInspectorProvider,
    FakeChainDataProvider,
    FakeContractInspectorProvider,
    FakeMarketDataProvider,
    FakeNotificationChannel,
    FakeTradeVenueProvider,
    MarketDataProvider,
    NotificationChannel,
    OrderRequest,
    SecurityInputs,
    TradeVenueProvider,
    TxWindow,
)
from dex_agent.providers.interfaces import ChainTx, ContractArtifact, Confirmation


def _snapshot(pair_id: str) -> PairSnapshot:
    return PairSnapshot(
        pair_id=pair_id,
        price=Decimal("1.5"),
        liquidity=Decimal("1000"),
        market_cap=Decimal("5000"),
        fdv=Decimal("6000"),
        buy_count=3,
        sell_count=2,
        buy_volume=Decimal("300"),
        sell_volume=Decimal("200"),
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def test_market_fake_is_interface_and_scriptable():
    fake = FakeMarketDataProvider()
    assert isinstance(fake, MarketDataProvider)
    snap = _snapshot("pair-1")
    fake.set_pairs("tokenA", [snap])
    fake.set_snapshot(snap)

    pairs = fake.resolve_pairs("tokenA", Network.SOLANA)
    assert pairs.is_ok() and pairs.value == [snap]
    got = fake.fetch_pair_snapshot("pair-1")
    assert got.is_ok() and got.value == snap
    # calls recorded
    assert ("resolve_pairs", ("tokenA", Network.SOLANA)) in fake.calls


def test_market_fake_not_found_when_no_pairs():
    fake = FakeMarketDataProvider()
    result = fake.resolve_pairs("missing", Network.SOLANA)
    assert result.is_err() and isinstance(result.error, NotFound)


def test_fake_fail_next_then_succeeds():
    fake = FakeMarketDataProvider()
    fake.set_snapshot(_snapshot("p"))
    fake.fail_next("fetch_pair_snapshot", TimedOut("boom", timeout_s=1.0))
    first = fake.fetch_pair_snapshot("p")
    assert first.is_err() and isinstance(first.error, TimedOut)
    # next call recovers (queue drained)
    second = fake.fetch_pair_snapshot("p")
    assert second.is_ok()


def test_fake_fail_always_until_cleared():
    fake = FakeMarketDataProvider()
    fake.set_snapshot(_snapshot("p"))
    fake.fail_always("fetch_pair_snapshot", ProviderError("down", provider="fake"))
    assert fake.fetch_pair_snapshot("p").is_err()
    assert fake.fetch_pair_snapshot("p").is_err()
    fake.clear_failures("fetch_pair_snapshot")
    assert fake.fetch_pair_snapshot("p").is_ok()


def test_chain_fake_transactions_filtered_by_window():
    fake = FakeChainDataProvider()
    assert isinstance(fake, ChainDataProvider)
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    txs = [
        ChainTx("s1", "w1", "buy", Decimal("1"), None, base),
        ChainTx("s2", "w2", "sell", None, Decimal("1"), base + timedelta(hours=2)),
    ]
    fake.set_transactions("pair-1", txs)
    window = TxWindow(start=base, end=base + timedelta(hours=1))
    got = fake.fetch_transactions("pair-1", window)
    assert got.is_ok() and [t.signature for t in got.value] == ["s1"]


def test_chain_fake_contract_and_holders():
    fake = FakeChainDataProvider()
    artifact = ContractArtifact(token_address="t", network=Network.SOLANA, mint_authority="m")
    fake.set_contract(artifact)
    fake.set_holders("t", [HolderBalance("w", Decimal("10"))])
    assert fake.fetch_contract("t", Network.SOLANA).value is artifact
    assert fake.fetch_holder_distribution("t").value[0].wallet == "w"
    # unknown contract -> ProviderError
    assert fake.fetch_contract("other", Network.SOLANA).is_err()


def test_inspector_fake():
    fake = FakeContractInspectorProvider()
    assert isinstance(fake, ContractInspectorProvider)
    inputs = SecurityInputs(token_address="t", mint_authority="m", authority_source="SolanaRPC")
    fake.set_inputs(inputs)
    assert fake.inspect_token("t", Network.SOLANA).value is inputs
    assert fake.inspect_token("none", Network.SOLANA).is_err()


def test_trade_venue_fake_submit_and_confirm():
    fake = FakeTradeVenueProvider()
    assert isinstance(fake, TradeVenueProvider)
    req = OrderRequest(
        pair_id="p",
        kind=OrderKind.BUY,
        input_mint="SOL",
        output_mint="MINT",
        amount=Decimal("1"),
        max_slippage=Decimal("1"),
    )
    submitted = fake.submit_order(req)
    assert submitted.is_ok()
    tx_id = submitted.value.tx_id
    conf = Confirmation(
        tx_id=tx_id,
        confirmed=True,
        executed_price=Decimal("1"),
        executed_qty=Decimal("1"),
        fee=Decimal("0.01"),
        executed_slippage=Decimal("0.2"),
        confirmed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    fake.set_confirmation(tx_id, conf)
    assert fake.poll_confirmation(tx_id, timedelta(seconds=60)).value is conf


def test_trade_venue_fake_injected_submission_failure():
    fake = FakeTradeVenueProvider()
    fake.fail_next("submit_order", ProviderError("venue down", provider="fake"))
    req = OrderRequest("p", OrderKind.BUY, "SOL", "MINT", Decimal("1"), Decimal("1"))
    assert fake.submit_order(req).is_err()


def test_notification_fake_delivers_and_fails():
    fake = FakeNotificationChannel(name="tg")
    assert isinstance(fake, NotificationChannel)
    alert = Alert(title="hi", body="there")
    assert fake.deliver(alert).is_ok()
    assert fake.delivered == [alert]
    fake.fail_next("deliver", TimedOut("slow"))
    assert fake.deliver(alert).is_err()
