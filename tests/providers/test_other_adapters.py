"""Unit tests for the DexScreener, GoPlus, Jupiter, and Telegram adapters (4.4).

All use a mocked HTTP client; no real network calls. Covers response mapping,
the slippage-bps conversion, the no-signer guard, confirmation polling, and
error typing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from dex_agent.errors import ProviderError
from dex_agent.models import Network, OrderKind
from dex_agent.providers import (
    Alert,
    DexScreenerAdapter,
    FakeHttpClient,
    GoPlusAdapter,
    JupiterAdapter,
    OrderRequest,
    TelegramChannel,
)
from dex_agent.result import Ok

FIXED_NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# DexScreener (optional market-data fallback)
# ---------------------------------------------------------------------------


def test_dexscreener_resolve_pairs_maps_response():
    http = FakeHttpClient().stub(
        "/tokens/v1/solana/TOKEN",
        {
            "pairs": [
                {
                    "pairAddress": "P1",
                    "priceUsd": "0.01",
                    "liquidity": {"usd": "5000"},
                    "marketCap": "100000",
                    "fdv": "120000",
                    "txns": {"h24": {"buys": 12, "sells": 8}},
                    "volume": {"h24": "777"},
                }
            ]
        },
    )
    adapter = DexScreenerAdapter(http, clock=lambda: FIXED_NOW)
    result = adapter.resolve_pairs("TOKEN", Network.SOLANA)
    assert result.is_ok()
    snap = result.value[0]
    assert snap.pair_id == "P1"
    assert snap.price == Decimal("0.01")
    assert snap.liquidity == Decimal("5000")
    assert snap.buy_count == 12 and snap.sell_count == 8
    assert snap.buy_volume == Decimal("777")


# ---------------------------------------------------------------------------
# GoPlus (optional contract-inspection fallback)
# ---------------------------------------------------------------------------


def test_goplus_inspect_token_maps_raw_signals():
    http = FakeHttpClient().stub(
        "/api/v1/solana/token_security",
        {
            "result": {
                "TOKEN": {
                    "mintable": {"authority": "MINT_AUTH", "status": "1"},
                    "freezable": {"authority": "FREEZE_AUTH", "status": "1"},
                    "transfer_fee": "1",
                }
            }
        },
    )
    adapter = GoPlusAdapter(http, api_key="k")
    result = adapter.inspect_token("TOKEN", Network.SOLANA)
    assert result.is_ok()
    inputs = result.value
    assert inputs.signal_source == "GoPlus"
    assert inputs.mint_authority == "MINT_AUTH"
    assert inputs.freeze_authority == "FREEZE_AUTH"
    assert inputs.has_transfer_fee_extension is True


def test_goplus_sends_api_key_header():
    http = FakeHttpClient().stub("/token_security", {"result": {"T": {}}})
    GoPlusAdapter(http, api_key="secret").inspect_token("T", Network.SOLANA)
    assert http.calls[0].headers.get("Authorization") == "secret"


# ---------------------------------------------------------------------------
# Jupiter (trade venue)
# ---------------------------------------------------------------------------


def _order(slippage: str = "1") -> OrderRequest:
    return OrderRequest(
        pair_id="P",
        kind=OrderKind.BUY,
        input_mint="So11111111111111111111111111111111111111112",
        output_mint="MINT",
        amount=Decimal("1000000"),
        max_slippage=Decimal(slippage),
    )


def test_jupiter_submit_without_signer_is_rejected():
    http = FakeHttpClient()
    http.stub("/v6/quote", {"outAmount": "999"})
    http.stub("/v6/swap", {"swapTransaction": "BASE64TX"})
    adapter = JupiterAdapter(http, user_public_key="PUBKEY")  # no signer wired (Task 15.2)
    result = adapter.submit_order(_order())
    assert result.is_err() and isinstance(result.error, ProviderError)
    assert result.error.context.get("requires_signer") is True


def test_jupiter_submit_with_signer_sends_slippage_bps_and_returns_txid():
    http = FakeHttpClient()
    http.stub("/v6/quote", {"outAmount": "999"})
    http.stub("/v6/swap/send", {"signature": "SIG123"})
    http.stub("/v6/swap", {"swapTransaction": "UNSIGNED"})
    adapter = JupiterAdapter(
        http,
        user_public_key="PUBKEY",
        signer=lambda tx: f"signed::{tx}",
        clock=lambda: FIXED_NOW,
    )
    result = adapter.submit_order(_order(slippage="1"))  # 1% -> 100 bps
    assert result.is_ok()
    assert result.value.tx_id == "SIG123"
    quote_call = next(c for c in http.calls if "/v6/quote" in c.url)
    assert quote_call.params.get("slippageBps") == 100
    send_call = next(c for c in http.calls if "/swap/send" in c.url)
    assert send_call.json["signedTransaction"] == "signed::UNSIGNED"


def test_jupiter_poll_confirmation_uses_injected_poller():
    http = FakeHttpClient()
    poller_calls = []

    def poller(tx_id):
        poller_calls.append(tx_id)
        return Ok({"meta": {"err": None, "fee": 5000}, "executedPrice": "1.23"})

    adapter = JupiterAdapter(http, confirm_poller=poller, clock=lambda: FIXED_NOW)
    result = adapter.poll_confirmation("SIG123", timedelta(seconds=60))
    assert result.is_ok()
    conf = result.value
    assert conf.confirmed is True
    assert conf.fee == Decimal("5000")
    assert conf.executed_price == Decimal("1.23")
    assert poller_calls == ["SIG123"]


# ---------------------------------------------------------------------------
# Telegram (notification channel)
# ---------------------------------------------------------------------------


def test_telegram_delivers_via_send_message():
    http = FakeHttpClient().stub("/sendMessage", {"ok": True, "result": {"message_id": 1}})
    channel = TelegramChannel(http, bot_token="BOTTOKEN", chat_id="123")
    result = channel.deliver(Alert(title="Alert", body="rug detected"))
    assert result.is_ok()
    call = http.calls[0]
    assert "/botBOTTOKEN/sendMessage" in call.url
    assert call.json["chat_id"] == "123"
    assert "rug detected" in call.json["text"]


def test_telegram_api_error_is_provider_error():
    http = FakeHttpClient().stub(
        "/sendMessage", {"ok": False, "error_code": 400, "description": "bad chat"}
    )
    channel = TelegramChannel(http, bot_token="T", chat_id="x")
    result = channel.deliver(Alert(title="t", body="b"))
    assert result.is_err() and isinstance(result.error, ProviderError)
