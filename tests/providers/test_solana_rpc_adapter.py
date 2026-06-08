"""Unit tests for SolanaRpcAdapter authority detection (Task 4.4).

Verifies getAccountInfo -> SecurityIssue-input mapping (mintAuthority /
freezeAuthority / Token-2022 transfer-fee extension), holder/largest-account
mapping, state-hash change detection, confirmation polling, and error/timeout
typing - all via a mocked JSON-RPC client (no real chain calls).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from dex_agent.errors import TimedOut, Unverified
from dex_agent.models import Network
from dex_agent.providers import FakeRpcClient, SolanaRpcAdapter
from dex_agent.providers.adapters.solana_rpc import TOKEN_2022_PROGRAM
from dex_agent.providers.clients import ClientTimeout

SPL_TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


def _account_info(info: dict, *, owner: str = SPL_TOKEN_PROGRAM) -> dict:
    return {
        "value": {
            "owner": owner,
            "data": {"parsed": {"type": "mint", "info": info}, "program": "spl-token"},
        }
    }


def test_inspect_token_detects_active_mint_and_freeze_authority():
    rpc = FakeRpcClient().stub(
        "getAccountInfo",
        _account_info({"mintAuthority": "MINT_AUTH", "freezeAuthority": "FREEZE_AUTH", "supply": "1000"}),
    )
    result = SolanaRpcAdapter(rpc).inspect_token("MINT", Network.SOLANA)
    assert result.is_ok()
    inputs = result.value
    assert inputs.mint_authority == "MINT_AUTH"
    assert inputs.freeze_authority == "FREEZE_AUTH"
    assert inputs.authority_source == "SolanaRPC"
    assert inputs.has_transfer_fee_extension is False


def test_inspect_token_renounced_authorities_are_none():
    rpc = FakeRpcClient().stub(
        "getAccountInfo",
        _account_info({"mintAuthority": None, "freezeAuthority": None}),
    )
    inputs = SolanaRpcAdapter(rpc).inspect_token("MINT", Network.SOLANA).value
    assert inputs.mint_authority is None
    assert inputs.freeze_authority is None


def test_inspect_token_detects_token_2022_transfer_fee_extension():
    info = {
        "mintAuthority": None,
        "freezeAuthority": None,
        "extensions": [{"extension": "transferFeeConfig", "state": {}}],
    }
    rpc = FakeRpcClient().stub("getAccountInfo", _account_info(info, owner=TOKEN_2022_PROGRAM))
    inputs = SolanaRpcAdapter(rpc).inspect_token("MINT", Network.SOLANA).value
    assert inputs.has_transfer_fee_extension is True
    assert inputs.is_token_2022 is True


def test_fetch_contract_maps_artifact():
    rpc = FakeRpcClient().stub(
        "getAccountInfo",
        _account_info({"mintAuthority": "M", "freezeAuthority": None}),
    )
    art = SolanaRpcAdapter(rpc).fetch_contract("MINT", Network.SOLANA).value
    assert art.mint_authority == "M"
    assert art.freeze_authority is None
    assert art.network == Network.SOLANA


def test_unanalyzable_mint_is_unverified():
    rpc = FakeRpcClient().stub("getAccountInfo", {"value": None})
    result = SolanaRpcAdapter(rpc).inspect_token("MINT", Network.SOLANA)
    assert result.is_err() and isinstance(result.error, Unverified)


def test_rpc_timeout_maps_to_timed_out():
    rpc = FakeRpcClient().fail("getAccountInfo", ClientTimeout("slow"))
    result = SolanaRpcAdapter(rpc).fetch_contract("MINT", Network.SOLANA)
    assert result.is_err() and isinstance(result.error, TimedOut)


def test_state_hash_changes_with_authority_change():
    adapter_a = SolanaRpcAdapter(FakeRpcClient().stub("getAccountInfo", _account_info({"mintAuthority": "A"})))
    adapter_b = SolanaRpcAdapter(FakeRpcClient().stub("getAccountInfo", _account_info({"mintAuthority": "B"})))
    h_a = adapter_a.fetch_contract_state_hash("MINT").value
    h_b = adapter_b.fetch_contract_state_hash("MINT").value
    assert h_a.value != h_b.value
    # deterministic for identical state
    adapter_a2 = SolanaRpcAdapter(FakeRpcClient().stub("getAccountInfo", _account_info({"mintAuthority": "A"})))
    assert adapter_a2.fetch_contract_state_hash("MINT").value.value == h_a.value


def test_fetch_holder_distribution_from_largest_accounts():
    rpc = FakeRpcClient().stub(
        "getTokenLargestAccounts",
        {"value": [{"address": "ACC1", "uiTokenAmount": {"amount": "900"}}, {"address": "ACC2", "uiTokenAmount": {"amount": "100"}}]},
    )
    holders = SolanaRpcAdapter(rpc).fetch_holder_distribution("MINT").value
    assert [(h.wallet, h.balance) for h in holders] == [("ACC1", Decimal("900")), ("ACC2", Decimal("100"))]


def test_get_token_supply():
    rpc = FakeRpcClient().stub("getTokenSupply", {"value": {"amount": "123456", "decimals": 6}})
    assert SolanaRpcAdapter(rpc).get_token_supply("MINT").value == Decimal("123456")


def test_poll_signature_not_yet_confirmed_is_timed_out():
    rpc = FakeRpcClient().stub("getTransaction", None)
    result = SolanaRpcAdapter(rpc).poll_signature("sig")
    assert result.is_err() and isinstance(result.error, TimedOut)


def test_poll_signature_returns_confirmed_tx():
    rpc = FakeRpcClient().stub("getTransaction", {"meta": {"err": None, "fee": 5000}})
    result = SolanaRpcAdapter(rpc).poll_signature("sig")
    assert result.is_ok()
    assert result.value["meta"]["fee"] == 5000
