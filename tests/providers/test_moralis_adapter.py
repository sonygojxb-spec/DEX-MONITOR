"""Unit tests for MoralisAdapter with a mocked HTTP client (Task 4.4).

Verifies response-to-model mapping across BOTH hosts (solana-gateway + deep-
index), the X-API-Key auth header, the chain=solana param on deep-index calls,
batch-metadata coalescing (POST <=100), and error/timeout typing. No real
network calls occur - the injected FakeHttpClient serves all responses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from dex_agent.errors import NotFound, ProviderError, TimedOut
from dex_agent.models import Network
from dex_agent.providers import FakeHttpClient, MoralisAdapter, TxWindow
from dex_agent.providers.clients import ClientTimeout, HttpResponse

FIXED_NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _adapter(http: FakeHttpClient) -> MoralisAdapter:
    return MoralisAdapter(http, api_key="secret-key", clock=lambda: FIXED_NOW)


def test_resolve_pairs_maps_solana_gateway_response_and_sends_api_key():
    http = FakeHttpClient().stub(
        "/token/mainnet/TOKEN/pairs",
        [
            {
                "pairAddress": "PAIR1",
                "usdPrice": "2.5",
                "liquidityUsd": "1000.0",
                "marketCap": "50000",
                "fullyDilutedValue": "60000",
            }
        ],
    )
    result = _adapter(http).resolve_pairs("TOKEN", Network.SOLANA)
    assert result.is_ok()
    snap = result.value[0]
    assert snap.pair_id == "PAIR1"
    assert snap.price == Decimal("2.5")
    assert snap.liquidity == Decimal("1000.0")
    assert snap.market_cap == Decimal("50000")
    assert snap.fdv == Decimal("60000")
    assert snap.fetched_at == FIXED_NOW
    # auth header present on the call
    call = http.calls[0]
    assert call.headers.get("X-API-Key") == "secret-key"
    assert "solana-gateway.moralis.io" in call.url


def test_resolve_pairs_empty_is_not_found():
    http = FakeHttpClient().stub("/pairs", [])
    result = _adapter(http).resolve_pairs("TOKEN", Network.SOLANA)
    assert result.is_err() and isinstance(result.error, NotFound)


def test_fetch_pair_snapshot_combines_deep_index_analytics_and_price():
    http = FakeHttpClient()
    http.stub(
        "/tokens/MINT/analytics",
        {
            "totalLiquidityUsd": "1234",
            "totalFullyDilutedValuation": "9999",
            "totalBuyVolume": {"24h": "500"},
            "totalSellVolume": {"24h": "200"},
            "totalBuys": {"24h": "10"},
            "totalSells": {"24h": "4"},
        },
    )
    http.stub("/token/mainnet/MINT/price", {"usdPrice": "0.42"})
    result = _adapter(http).fetch_pair_snapshot("MINT")
    assert result.is_ok()
    snap = result.value
    assert snap.price == Decimal("0.42")
    assert snap.liquidity == Decimal("1234")
    assert snap.fdv == Decimal("9999")
    assert snap.buy_volume == Decimal("500")
    assert snap.sell_volume == Decimal("200")
    assert snap.buy_count == 10 and snap.sell_count == 4
    # deep-index call carries chain=solana
    analytics_call = next(c for c in http.calls if "/analytics" in c.url)
    assert "deep-index.moralis.io" in analytics_call.url
    assert analytics_call.params.get("chain") == "solana"


def test_fetch_contract_maps_metadata_risk_fields_authority_unset():
    http = FakeHttpClient().stub(
        "/token/mainnet/TOKEN/metadata",
        {
            "isVerifiedContract": True,
            "possibleSpam": False,
            "score": "73",
            "metaplex": {"updateAuthority": "UPAUTH", "isMutable": True},
        },
    )
    result = _adapter(http).fetch_contract("TOKEN", Network.SOLANA)
    assert result.is_ok()
    art = result.value
    # Moralis is NOT authoritative for mint/freeze authority
    assert art.mint_authority is None and art.freeze_authority is None
    assert art.update_authority == "UPAUTH"
    assert art.is_mutable is True
    assert art.is_verified is True
    assert art.possible_spam is False
    assert art.score == Decimal("73")


def test_fetch_holder_distribution_maps_top_holders():
    http = FakeHttpClient().stub(
        "/token/mainnet/TOKEN/top-holders",
        {"result": [{"ownerAddress": "W1", "balance": "100"}, {"ownerAddress": "W2", "balance": "50"}]},
    )
    result = _adapter(http).fetch_holder_distribution("TOKEN")
    assert result.is_ok()
    assert [(h.wallet, h.balance) for h in result.value] == [("W1", Decimal("100")), ("W2", Decimal("50"))]


def test_fetch_transactions_maps_swaps_and_filters_window():
    http = FakeHttpClient().stub(
        "/token/mainnet/MINT/swaps",
        {
            "result": [
                {
                    "transactionHash": "sig1",
                    "walletAddress": "W1",
                    "transactionType": "BUY",
                    "bought": {"amount": "5"},
                    "sold": {"amount": "0"},
                    "blockTimestamp": "2025-01-01T12:00:00Z",
                },
                {
                    "transactionHash": "sig2",
                    "walletAddress": "W2",
                    "transactionType": "SELL",
                    "blockTimestamp": "2025-01-02T00:00:00Z",
                },
            ]
        },
    )
    window = TxWindow(
        start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end=datetime(2025, 1, 1, 23, 59, tzinfo=timezone.utc),
    )
    result = _adapter(http).fetch_transactions("MINT", window)
    assert result.is_ok()
    txs = result.value
    assert len(txs) == 1  # sig2 is outside the window
    assert txs[0].signature == "sig1"
    assert txs[0].tx_type == "buy"
    assert txs[0].bought_amount == Decimal("5")


def test_inspect_token_merges_metadata_and_token_score():
    http = FakeHttpClient()
    http.stub(
        "/token/mainnet/TOKEN/metadata",
        {"possibleSpam": True, "metaplex": {"updateAuthority": "UA", "isMutable": False}},
    )
    http.stub("/tokens/TOKEN/score", {"score": "12"})
    result = _adapter(http).inspect_token("TOKEN", Network.SOLANA)
    assert result.is_ok()
    inputs = result.value
    assert inputs.signal_source == "Moralis"
    assert inputs.possible_spam is True
    assert inputs.update_authority == "UA"
    assert inputs.score == Decimal("12")  # token score overrides metadata score
    # authority fields are not set by Moralis
    assert inputs.mint_authority is None and inputs.authority_source is None


def test_fetch_metadata_batch_chunks_and_posts_within_100():
    # 150 addresses -> 2 POST batch calls (100 + 50)
    addresses = [f"A{i}" for i in range(150)]
    http = FakeHttpClient()
    calls_bodies: list[list[str]] = []
    real_request = http.request

    def dynamic_request(method, url, *, headers=None, params=None, json=None, timeout=None):
        if method == "POST" and "/metadata" in url:
            calls_bodies.append(list(json["addresses"]))
            return HttpResponse(200, [{"mint": a, "score": "1"} for a in json["addresses"]])
        return real_request(method, url, headers=headers, params=params, json=json, timeout=timeout)

    http.request = dynamic_request  # type: ignore[assignment]

    result = _adapter(http).fetch_metadata_batch(addresses, Network.SOLANA)
    assert result.is_ok()
    assert len(result.value) == 150
    assert [len(b) for b in calls_bodies] == [100, 50]
    assert all(len(b) <= 100 for b in calls_bodies)


def test_timeout_maps_to_timed_out_error():
    http = FakeHttpClient().fail("/pairs", ClientTimeout("slow"))
    result = _adapter(http).resolve_pairs("TOKEN", Network.SOLANA)
    assert result.is_err() and isinstance(result.error, TimedOut)


def test_non_2xx_maps_to_provider_error():
    http = FakeHttpClient().stub("/token/mainnet/TOKEN/metadata", {"msg": "nope"}, status=500)
    result = _adapter(http).fetch_contract("TOKEN", Network.SOLANA)
    assert result.is_err() and isinstance(result.error, ProviderError)
    assert result.error.context.get("status") == 500
