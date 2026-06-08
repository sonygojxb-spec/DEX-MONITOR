"""Solana RPC adapter - base on-chain fallback + authoritative authority source.

Design reference: "Per-Integration Details" -> Solana RPC, and "Solana Security
Semantics". This adapter is the **authoritative source for SPL mint/freeze
authority** (and Token-2022 transfer-fee extension), and the base on-chain
fallback for holders/supply/tx reads and order-confirmation polling. It issues
JSON-RPC calls through the injected
:class:`~dex_agent.providers.clients.RpcClient` - never a real node in tests.

Authority mapping (authoritative inputs for the Security_Inspector, Task 7):

* active (non-null) ``mintAuthority``   -> ``MINTABLE``
* active (non-null) ``freezeAuthority`` -> ``TRANSFER_DISABLE`` (forces Critical)
* Token-2022 ``transferFeeConfig`` extension present -> ``FEE_MODIFIABLE``

It implements :class:`ChainDataProvider` (mint state, holders, tx stream,
state-hash for change detection) and :class:`ContractInspectorProvider`
(authoritative authority inputs), plus :class:`TradeVenueProvider`-style
confirmation polling via :meth:`poll_signature` reused by the Jupiter adapter.
"""

from __future__ import annotations

import hashlib
import json as _json
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from dex_agent.errors import ProviderError, TimedOut, Unverified
from dex_agent.models import HolderBalance, Network
from dex_agent.providers.adapters._common import (
    map_transport_error,
    to_decimal,
)
from dex_agent.providers.clients import RpcClient
from dex_agent.providers.interfaces import (
    ChainDataProvider,
    ChainTx,
    ContractArtifact,
    ContractInspectorProvider,
    SecurityInputs,
    StateHash,
    TxWindow,
)
from dex_agent.result import Err, Ok, Result

PROVIDER = "SolanaRPC"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


class SolanaRpcAdapter(ChainDataProvider, ContractInspectorProvider):
    """Authoritative SPL authority source and base on-chain fallback."""

    def __init__(
        self,
        rpc: RpcClient,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._rpc = rpc
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # -- internal helpers ------------------------------------------------
    def _call(self, method: str, params: list[Any]) -> Result[Any]:
        try:
            result = self._rpc.call(method, params)
        except Exception as exc:  # noqa: BLE001 - mapped to typed Result errors
            return map_transport_error(exc, provider=PROVIDER)
        return Ok(result)

    @staticmethod
    def _parsed_mint(account_info: Any) -> Mapping[str, Any] | None:
        """Extract the jsonParsed SPL mint ``info`` block from getAccountInfo."""
        if not isinstance(account_info, Mapping):
            return None
        value = account_info.get("value")
        if not isinstance(value, Mapping):
            return None
        data = value.get("data")
        if not isinstance(data, Mapping):
            return None
        parsed = data.get("parsed")
        if not isinstance(parsed, Mapping):
            return None
        info = parsed.get("info")
        return info if isinstance(info, Mapping) else None

    @staticmethod
    def _has_transfer_fee_extension(info: Mapping[str, Any]) -> bool:
        extensions = info.get("extensions")
        if not isinstance(extensions, list):
            return False
        for ext in extensions:
            if isinstance(ext, Mapping) and ext.get("extension") in {
                "transferFeeConfig",
                "transferFeeAmount",
            }:
                return True
        return False

    @staticmethod
    def _is_token_2022(account_info: Any) -> bool:
        if not isinstance(account_info, Mapping):
            return False
        value = account_info.get("value")
        if isinstance(value, Mapping):
            return value.get("owner") == TOKEN_2022_PROGRAM
        return False

    def _read_mint(self, token_address: str) -> Result[Mapping[str, Any]]:
        result = self._call(
            "getAccountInfo", [token_address, {"encoding": "jsonParsed"}]
        )
        if result.is_err():
            return result
        info = self._parsed_mint(result.value)
        if info is None:
            return Err(
                Unverified(
                    "SPL mint account unanalyzable or unavailable",
                    subject=token_address,
                )
            )
        return Ok({"info": info, "raw": result.value})

    # -- ChainDataProvider ----------------------------------------------
    def fetch_contract(
        self, token_address: str, network: Network
    ) -> Result[ContractArtifact]:
        read = self._read_mint(token_address)
        if read.is_err():
            return read
        info = read.value["info"]
        return Ok(
            ContractArtifact(
                token_address=token_address,
                network=network,
                mint_authority=info.get("mintAuthority"),
                freeze_authority=info.get("freezeAuthority"),
                has_transfer_fee_extension=self._has_transfer_fee_extension(info),
                is_token_2022=self._is_token_2022(read.value["raw"]),
                raw=dict(info),
            )
        )

    def fetch_contract_state_hash(self, token_address: str) -> Result[StateHash]:
        read = self._read_mint(token_address)
        if read.is_err():
            return read
        info = read.value["info"]
        canonical = _json.dumps(info, sort_keys=True, default=str)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return Ok(StateHash(value=digest))

    def fetch_holder_distribution(
        self, token_address: str
    ) -> Result[list[HolderBalance]]:
        result = self._call("getTokenLargestAccounts", [token_address])
        if result.is_err():
            return result
        value = result.value
        rows = value.get("value") if isinstance(value, Mapping) else value
        holders: list[HolderBalance] = []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                wallet = row.get("address")
                amount = to_decimal(
                    (row.get("uiTokenAmount") or {}).get("amount")
                    if isinstance(row.get("uiTokenAmount"), Mapping)
                    else row.get("amount"),
                    to_decimal("0"),
                )
                if wallet is not None:
                    holders.append(
                        HolderBalance(wallet=str(wallet), balance=amount or to_decimal("0"))
                    )
        return Ok(holders)

    def fetch_transactions(
        self, pair_id: str, window: TxWindow
    ) -> Result[list[ChainTx]]:
        sig_result = self._call("getSignaturesForAddress", [pair_id, {"limit": 1000}])
        if sig_result.is_err():
            return sig_result
        signatures = sig_result.value if isinstance(sig_result.value, list) else []
        txs: list[ChainTx] = []
        for entry in signatures:
            if not isinstance(entry, Mapping):
                continue
            block_time = entry.get("blockTime")
            when = (
                datetime.fromtimestamp(float(block_time), tz=timezone.utc)
                if block_time is not None
                else window.start
            )
            if not (window.start <= when <= window.end):
                continue
            txs.append(
                ChainTx(
                    signature=str(entry.get("signature") or ""),
                    wallet_address=str(pair_id),
                    tx_type="",
                    bought_amount=None,
                    sold_amount=None,
                    block_time=when,
                    raw=dict(entry),
                )
            )
        return Ok(txs)

    # -- ContractInspectorProvider (authoritative authority) ------------
    def inspect_token(
        self, token_address: str, network: Network
    ) -> Result[SecurityInputs]:
        read = self._read_mint(token_address)
        if read.is_err():
            return read
        info = read.value["info"]
        return Ok(
            SecurityInputs(
                token_address=token_address,
                mint_authority=info.get("mintAuthority"),
                freeze_authority=info.get("freezeAuthority"),
                has_transfer_fee_extension=self._has_transfer_fee_extension(info),
                is_token_2022=self._is_token_2022(read.value["raw"]),
                authority_source="SolanaRPC",
                raw=dict(info),
            )
        )

    # -- supply + confirmation polling ----------------------------------
    def get_token_supply(self, token_address: str) -> Result[Any]:
        """``getTokenSupply`` total supply (for concentration math, Req 3.6)."""
        result = self._call("getTokenSupply", [token_address])
        if result.is_err():
            return result
        value = result.value
        amount = value.get("value") if isinstance(value, Mapping) else value
        if isinstance(amount, Mapping):
            return Ok(to_decimal(amount.get("amount"), to_decimal("0")))
        return Ok(to_decimal(amount, to_decimal("0")))

    def poll_signature(self, tx_id: str) -> Result[Mapping[str, Any]]:
        """Poll ``getTransaction`` for a confirmed transaction (Req 6.5/6.6).

        Returns ``Ok(tx)`` once the transaction is found, ``Err(TimedOut)`` when
        the node reports it not-yet-found (``null`` result), or a transport
        error. The retry/backoff loop and overall timeout are owned by the
        Trade_Executor (Task 15); this is a single poll.
        """
        result = self._call(
            "getTransaction",
            [tx_id, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
        )
        if result.is_err():
            return result
        if result.value is None:
            return Err(TimedOut("transaction not yet confirmed", timeout_s=None))
        if isinstance(result.value, Mapping):
            return Ok(result.value)
        return Err(ProviderError("unexpected getTransaction result", provider=PROVIDER))


__all__ = ["SolanaRpcAdapter", "TOKEN_2022_PROGRAM"]
