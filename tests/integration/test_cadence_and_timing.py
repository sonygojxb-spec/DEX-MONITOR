"""Integration test 19.4: cadence and timing behaviors.

Exercises, against faked providers and a controllable clock, the configured
cadences and timing-sensitive behaviors:

* discovery / refresh cadence (Req 1.5, 1.7),
* contract re-evaluation on state change (Req 2.2, 2.10),
* signal cadence (Req 5.1),
* severity and bot-percentage alert timing (Req 3.5, 8.2),
* exit-signal alert timing for held positions (Req 5.5),
* stop-loss evaluation cadence (Req 7.5).
"""

from __future__ import annotations

from decimal import Decimal

from dex_agent.control.orchestrator import MIN_REFRESH_INTERVAL_S
from dex_agent.decision import SignalInputs
from dex_agent.models import (
    ExitClass,
    Network,
    Position,
    PositionStatus,
    SignalType,
    Token,
    WatchlistEntry,
    WatchlistSource,
    make_trading_pair,
)
from dex_agent.notify import build_severity_alert
from dex_agent.models import Severity
from dex_agent.providers.interfaces import ChainTx, DiscoveryFilters, SecurityInputs

from tests.integration.helpers import (
    NOW,
    ManualClock,
    build_test_agent,
    clean_security_inputs,
    make_config,
    make_snapshot,
)

TOKEN = "TokenMint333"
PAIR = "pair-cad"


def _token(address: str = TOKEN) -> Token:
    return Token(
        address=address,
        network=Network.SOLANA,
        symbol="TKN",
        name="Token",
        total_supply=Decimal(1_000_000),
    )


def test_refresh_cadence_honors_min_floor():
    # Req 1.7: the effective market-data poll interval honors the >=5s floor and
    # reflects the configured Data_Refresh_Interval when no limiter constrains it.
    agent, _fakes, _clock = build_test_agent(config=make_config(refresh_interval_s=30))
    assert agent.config.refresh_interval_s == 30
    interval = agent.orchestrator.effective_poll_interval_s()
    assert interval >= MIN_REFRESH_INTERVAL_S
    assert interval == 30


def test_discovery_cadence_adds_only_recent_matching_pairs():
    # Req 1.5/1.6: discovery adds exactly the pairs first listed within 24h that
    # match the filters; older candidates are excluded.
    clock = ManualClock()
    agent, fakes, _clock = build_test_agent(
        config=make_config(discovery_scan_interval_s=60), clock=clock
    )
    assert 30 <= agent.config.discovery_scan_interval_s <= 300

    recent = make_trading_pair(
        id="recent",
        token=_token("recentMint"),
        quote_asset="SOL",
        dex="orca",
        created_at=NOW,
    ).value
    from datetime import timedelta

    old = make_trading_pair(
        id="old",
        token=_token("oldMint"),
        quote_asset="SOL",
        dex="orca",
        created_at=NOW - timedelta(hours=48),  # first listed > 24h ago
    ).value

    agent.repositories.pairs.add(recent)
    agent.repositories.pairs.add(old)
    fakes.market.set_discoveries(
        [make_snapshot("recent", fetched_at=NOW), make_snapshot("old", fetched_at=NOW)]
    )

    outcome = agent.data_ingestor.discovery_scan(
        DiscoveryFilters(quote_assets=frozenset({"SOL"}))
    )
    assert outcome.is_ok()
    assert "recent" in outcome.value.added
    assert "old" not in outcome.value.added


def test_contract_reevaluation_on_state_change():
    # Req 2.10: a contract state change re-evaluates and records a fresh rating.
    clock = ManualClock()
    agent, fakes, _clock = build_test_agent(clock=clock)
    token = _token()

    fakes.inspector.set_inputs(clean_security_inputs(TOKEN))
    first = agent.security_inspector.evaluate(token)
    assert first.rating is Severity.NONE

    clock.advance(10)
    # State change: an active freeze authority now appears -> Critical (Req 2.5).
    fakes.inspector.set_inputs(
        SecurityInputs(
            token_address=TOKEN,
            freeze_authority="someAuthority",
            authority_source="solana_rpc",
        )
    )
    second = agent.security_inspector.on_state_change(token)
    assert second.rating is Severity.CRITICAL
    assert second.evaluated_at > first.evaluated_at
    assert agent.repositories.security_eval.latest(TOKEN).value.rating is Severity.CRITICAL


def test_signal_cadence_produces_entry_signal():
    # Req 5.1: the Signal_Engine computes an entry signal from current metrics.
    agent, _fakes, _clock = build_test_agent(config=make_config(signal_interval_s=15))
    assert 1 <= agent.config.signal_interval_s <= 300

    outcome = agent.signal_engine.compute(
        SignalInputs(
            pair_id=PAIR,
            severity=Severity.NONE,
            bot_pct=Decimal(0),
            holder_concentration=Decimal(0),
            curr_liquidity=Decimal(100000),
            buy_volume=Decimal(1000),
            sell_volume=Decimal(100),
        )
    )
    assert outcome.skipped is False
    assert outcome.entry is not None
    assert agent.repositories.signals.latest(PAIR, SignalType.ENTRY).is_ok()


def test_bot_percentage_alert_timing():
    # Req 3.5: when bot_pct exceeds the threshold a bot alert is dispatched.
    clock = ManualClock()
    agent, fakes, _clock = build_test_agent(
        config=make_config(bot_pct_threshold=Decimal(50)), clock=clock
    )
    pair = make_trading_pair(
        id=PAIR, token=_token(), quote_asset="SOL", dex="orca", created_at=NOW
    ).value
    agent.repositories.pairs.add(pair)

    # A single wallet with 5 swaps in the window classifies as a BOT (100%).
    txs = [
        ChainTx(
            signature=f"sig-{i}",
            wallet_address="botwallet",
            tx_type="buy",
            bought_amount=Decimal(1),
            sold_amount=None,
            block_time=NOW,
        )
        for i in range(5)
    ]
    fakes.chain.set_transactions(TOKEN, txs)

    result = agent.backend_analyzer.analyze(pair)
    assert result.is_ok()
    assert result.value.bot_tx_percentage > Decimal(50)
    assert any(
        a.title == "Bot activity threshold exceeded" for a in fakes.channel.delivered
    )


def test_severity_alert_always_delivered():
    # Req 8.2: High/Critical severity alerts are dispatched to enabled channels.
    agent, fakes, _clock = build_test_agent()
    agent.notifier.send(build_severity_alert(pair_id=PAIR, severity=Severity.CRITICAL))
    assert any(a.severity is Severity.CRITICAL for a in fakes.channel.delivered)


def test_exit_signal_alert_for_held_position():
    # Req 5.5: a rug-pull exit signal for a held position dispatches an exit alert.
    clock = ManualClock()
    agent, fakes, _clock = build_test_agent(
        config=make_config(rugpull_threshold=Decimal(50)), clock=clock
    )
    # A held position for the pair gates the exit alert.
    agent.repositories.positions.upsert(
        Position(
            pair_id=PAIR,
            token_address=TOKEN,
            quantity=Decimal(5),
            avg_entry_price=Decimal(2),
            notional_cost=Decimal(10),
            opened_at=NOW,
            status=PositionStatus.OPEN,
        )
    )

    outcome = agent.signal_engine.compute(
        SignalInputs(
            pair_id=PAIR,
            severity=Severity.NONE,
            bot_pct=Decimal(0),
            holder_concentration=Decimal(0),
            curr_liquidity=Decimal(10000),
            buy_volume=Decimal(1000),
            sell_volume=Decimal(100),
            prev_liquidity=Decimal(100000),  # 90% liquidity drop -> rug pull
        )
    )
    assert outcome.exit is not None
    assert outcome.exit.exit_class is ExitClass.RUG_PULL
    exit_alerts = [a for a in fakes.channel.delivered if a.is_exit_signal]
    assert exit_alerts, "expected a held-position exit alert"


def test_stop_loss_evaluation_cadence():
    # Req 7.5: stop-loss is evaluated at <=60s cadence and requests a full sell
    # when the unrealized loss reaches the configured percentage.
    agent, _fakes, _clock = build_test_agent()
    assert agent.risk_manager.eval_interval_s <= 60.0

    agent.repositories.positions.upsert(
        Position(
            pair_id=PAIR,
            token_address=TOKEN,
            quantity=Decimal(5),
            avg_entry_price=Decimal(10),
            notional_cost=Decimal(50),
            opened_at=NOW,
            status=PositionStatus.OPEN,
        )
    )
    # Current price is 50% below entry; stop-loss (20%) triggers a full-position sell.
    requests = agent.risk_manager.monitor_stop_loss(lambda _pid: Decimal(5))
    assert len(requests) == 1
    assert requests[0].pair_id == PAIR
    assert requests[0].quantity == Decimal(5)
