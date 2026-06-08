"""Unit tests for the Moralis Solana Streams intake (Task 4.5 + 4.4).

Covers stream creation via the injected client, balance-delta computation from
pre/postTokenBalances, the empty-body verification handshake (HTTP 200),
signature-keyed idempotent dedupe that ALWAYS returns 200 (including on the
intake's own downstream errors), and rug/dump classification routed to the
injected event sink.
"""

from __future__ import annotations

from decimal import Decimal

from dex_agent.errors import ProviderError
from dex_agent.providers import (
    FakeStreamClient,
    MoralisStreamsManager,
    MoralisWebhookIntake,
    StreamEvent,
    StreamEventKind,
    compute_balance_deltas,
)
from dex_agent.providers.clients import ClientError


# ---------------------------------------------------------------------------
# Stream management
# ---------------------------------------------------------------------------


def test_create_stream_puts_filtered_by_mint_addresses():
    client = FakeStreamClient()
    manager = MoralisStreamsManager(
        client, api_key="k", webhook_url="https://hook.example/webhook"
    )
    result = manager.create_stream(["MINT_A", "MINT_B"])
    assert result.is_ok()
    handle = result.value
    assert handle.id == "stream-1"
    assert handle.mint_addresses == ("MINT_A", "MINT_B")
    created = client.created[0]
    assert created["webhookUrl"] == "https://hook.example/webhook"
    assert created["mintAddresses"] == ["MINT_A", "MINT_B"]
    assert created["network"] == "mainnet"


def test_create_stream_transport_error_is_typed():
    client = FakeStreamClient()
    client.fail_with(ClientError("boom"))
    manager = MoralisStreamsManager(client, api_key="k", webhook_url="https://h/w")
    result = manager.create_stream(["M"])
    assert result.is_err() and isinstance(result.error, ProviderError)


# ---------------------------------------------------------------------------
# Balance-delta computation
# ---------------------------------------------------------------------------


def _balance(idx, mint, owner, amount):
    return {
        "accountIndex": idx,
        "mint": mint,
        "owner": owner,
        "uiTokenAmount": {"amount": str(amount)},
    }


def test_compute_balance_deltas_pairs_pre_and_post():
    tx = {
        "preTokenBalances": [_balance(1, "MINT", "POOL", 1000), _balance(2, "MINT", "BUYER", 0)],
        "postTokenBalances": [_balance(1, "MINT", "POOL", 400), _balance(2, "MINT", "BUYER", 600)],
    }
    deltas = compute_balance_deltas(tx)
    by_owner = {d.owner: d.delta for d in deltas}
    assert by_owner["POOL"] == Decimal("-600")
    assert by_owner["BUYER"] == Decimal("600")


def test_compute_balance_deltas_account_only_in_post():
    tx = {
        "preTokenBalances": [],
        "postTokenBalances": [_balance(3, "MINT", "NEW", 50)],
    }
    deltas = compute_balance_deltas(tx)
    assert len(deltas) == 1 and deltas[0].delta == Decimal("50")


# ---------------------------------------------------------------------------
# Webhook intake
# ---------------------------------------------------------------------------


def test_verification_handshake_empty_body_returns_200():
    events: list[StreamEvent] = []
    intake = MoralisWebhookIntake(events.append)
    resp = intake.handle({})
    assert resp.status_code == 200
    assert resp.body.get("verification") is True
    assert events == []


def test_verification_handshake_none_body_returns_200():
    intake = MoralisWebhookIntake(lambda e: None)
    assert intake.handle(None).status_code == 200


def test_intake_processes_and_emits_event():
    events: list[StreamEvent] = []
    intake = MoralisWebhookIntake(events.append)
    payload = {
        "block": {"blockTime": 1743436800},
        "transactions": [
            {
                "signature": "SIG1",
                "preTokenBalances": [_balance(1, "MINT", "POOL", 1000)],
                "postTokenBalances": [_balance(1, "MINT", "POOL", 990)],
            }
        ],
    }
    resp = intake.handle(payload)
    assert resp.status_code == 200
    assert resp.body["processed"] == 1
    assert len(events) == 1
    assert events[0].signature == "SIG1"
    assert events[0].net_by_mint["MINT"] == Decimal("-10")


def test_intake_dedupes_on_signature_and_still_returns_200():
    events: list[StreamEvent] = []
    intake = MoralisWebhookIntake(events.append)
    payload = {
        "transactions": [
            {"signature": "DUP", "preTokenBalances": [], "postTokenBalances": []}
        ]
    }
    first = intake.handle(payload)
    second = intake.handle(payload)  # duplicate delivery
    assert first.status_code == 200 and second.status_code == 200
    assert first.body["processed"] == 1
    assert second.body["processed"] == 0 and second.body["duplicates"] == 1
    assert len(events) == 1  # processed exactly once
    assert "DUP" in intake.processed_signatures


def test_intake_always_200_even_when_sink_raises():
    def bad_sink(event):
        raise RuntimeError("downstream boom")

    intake = MoralisWebhookIntake(bad_sink)
    payload = {
        "transactions": [
            {"signature": "S", "preTokenBalances": [], "postTokenBalances": []}
        ]
    }
    resp = intake.handle(payload)
    assert resp.status_code == 200
    assert resp.body["sink_errors"] == 1
    # signature marked processed so a retry will not re-run the failing sink
    assert "S" in intake.processed_signatures


def test_intake_classifies_liquidity_removal_for_watched_mint():
    events: list[StreamEvent] = []
    intake = MoralisWebhookIntake(
        events.append, watched_mints={"MINT"}, rug_drop_threshold_pct=Decimal(50)
    )
    payload = {
        "transactions": [
            {
                "signature": "RUG",
                "preTokenBalances": [_balance(1, "MINT", "POOL", 1000)],
                "postTokenBalances": [_balance(1, "MINT", "POOL", 100)],  # -90%
            }
        ]
    }
    intake.handle(payload)
    assert events[0].kind is StreamEventKind.LIQUIDITY_REMOVAL


def test_intake_classifies_dump_for_smaller_outflow():
    events: list[StreamEvent] = []
    intake = MoralisWebhookIntake(
        events.append, watched_mints={"MINT"}, rug_drop_threshold_pct=Decimal(50)
    )
    payload = {
        "transactions": [
            {
                "signature": "DUMP",
                "preTokenBalances": [_balance(1, "MINT", "SELLER", 1000)],
                "postTokenBalances": [_balance(1, "MINT", "SELLER", 800)],  # -20%
            }
        ]
    }
    intake.handle(payload)
    assert events[0].kind is StreamEventKind.DUMP
