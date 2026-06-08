"""Integration test 19.2: watchlist add -> monitoring begins (Req 1.1, 1.3).

Adds a resolvable token via a faked market provider, asserts monitoring starts,
and that removing the pair stops monitoring while the collected data is retained.
"""

from __future__ import annotations

from decimal import Decimal

from dex_agent.models import Network

from tests.integration.helpers import (
    build_test_agent,
    clean_security_inputs,
    make_snapshot,
)

TOKEN = "TokenMint111"
PAIR = "pair-abc"


def test_watchlist_add_begins_monitoring_and_remove_stops_it():
    agent, fakes, _clock = build_test_agent()

    # Default config is loaded at startup (defaults when none persisted, Req 9.5/9.6).
    assert agent.config.refresh_interval_s == 30
    assert agent.config.automated_trading_enabled is False

    # Boot: monitoring-only, recovery runs before any trade-affecting op.
    report = agent.boot()
    assert report.recovery_ok is True
    assert agent.trading_allowed() is False  # monitoring-only at boot (Req 11.3)

    # Seed the faked market provider so the token resolves to a pair, and the
    # inspector so the security evaluation on add succeeds.
    fakes.market.set_pairs(TOKEN, [make_snapshot(PAIR)])
    fakes.inspector.set_inputs(clean_security_inputs(TOKEN))

    # Adding a resolvable token begins monitoring its pair (Req 1.1).
    result = agent.add_token(TOKEN, Network.SOLANA)
    assert result.is_ok()
    assert result.value.pair_id == PAIR
    assert agent.is_monitoring(PAIR) is True
    assert PAIR in agent.orchestrator.active_pairs()

    # A security evaluation was triggered and recorded for the token (Req 1.1).
    assert agent.repositories.security_eval.latest(TOKEN).is_ok()

    # Removing the pair stops monitoring (Req 1.3) ...
    agent.remove_pair(PAIR)
    assert agent.is_monitoring(PAIR) is False
    assert PAIR not in agent.orchestrator.active_pairs()

    # ... while the collected data is retained (the watchlist entry persists,
    # only deactivated; Req 1.4).
    entry = agent.repositories.watchlist.get(PAIR)
    assert entry.is_ok()
    assert entry.value.active is False


def test_unresolvable_token_is_rejected_and_not_monitored():
    agent, fakes, _clock = build_test_agent()
    agent.boot()

    # No pairs seeded for the token -> resolution fails, naming the token (Req 1.2).
    result = agent.add_token("UnknownMint", Network.SOLANA)
    assert result.is_err()
    assert result.error.identifier == "UnknownMint"
    assert agent.orchestrator.active_count() == 0
