"""GoPlus Security adapter - OPTIONAL contract-inspection fallback.

Design reference: "Per-Integration Details" -> GoPlus. Supplies Solana token
security signals (mint authority, freeze authority, transfer-fee/Token-2022
extensions, ownership/authority privileges, malicious flags) as a **corroborating
fallback** behind :class:`ContractInspectorProvider`, consulted only when the
primary sources (Solana RPC authority + Moralis risk inputs) are unavailable or
for cross-checking. **Disabled unless wired in configuration.**

Here we only wire the adapter and surface the **raw signals** mapped onto
:class:`SecurityInputs`; the full ``SecurityIssue`` semantics mapping is
implemented later in Task 7. The optional API key is injected from secrets/config.
The injected :class:`~dex_agent.providers.clients.HttpClient` keeps it testable.
"""

from __future__ import annotations

from typing import Any, Mapping

from dex_agent.errors import NotFound
from dex_agent.models import Network
from dex_agent.providers.adapters._common import (
    first_present,
    run_request,
    to_bool,
    to_decimal,
)
from dex_agent.providers.clients import HttpClient
from dex_agent.providers.interfaces import (
    ContractInspectorProvider,
    SecurityInputs,
)
from dex_agent.result import Err, Ok, Result

BASE_URL = "https://api.gopluslabs.io"
PROVIDER = "GoPlus"
# GoPlus Solana chain identifier used in the token-security path.
SOLANA_CHAIN_ID = "solana"


class GoPlusAdapter(ContractInspectorProvider):
    """Optional fallback :class:`ContractInspectorProvider` (disabled by default)."""

    def __init__(
        self,
        http: HttpClient,
        *,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        chain_id: str = SOLANA_CHAIN_ID,
    ) -> None:
        self._http = http
        self._api_key = api_key
        self._base = base_url.rstrip("/")
        self._chain_id = chain_id

    @property
    def _headers(self) -> Mapping[str, str]:
        headers = {"accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = self._api_key
        return headers

    def inspect_token(
        self, token_address: str, network: Network
    ) -> Result[SecurityInputs]:
        path = f"/api/v1/{self._chain_id}/token_security"
        result = run_request(
            lambda: self._http.request(
                "GET",
                f"{self._base}{path}",
                headers=self._headers,
                params={"contract_addresses": token_address},
            ),
            provider=PROVIDER,
        )
        if result.is_err():
            return result
        payload = result.value if isinstance(result.value, Mapping) else {}
        result_block = payload.get("result")
        row: Mapping[str, Any] | None = None
        if isinstance(result_block, Mapping):
            # keyed by address (case may differ) - take the matching or first
            row = result_block.get(token_address)
            if row is None and result_block:
                row = next(iter(result_block.values()), None)
        if not isinstance(row, Mapping):
            return Err(NotFound("no GoPlus signals for token", identifier=token_address))

        mint = row.get("mintable") if isinstance(row.get("mintable"), Mapping) else {}
        freeze = row.get("freezable") if isinstance(row.get("freezable"), Mapping) else {}
        mint_authority = first_present(mint, "authority") if mint else None
        freeze_authority = first_present(freeze, "authority") if freeze else None
        return Ok(
            SecurityInputs(
                token_address=token_address,
                mint_authority=mint_authority,
                freeze_authority=freeze_authority,
                has_transfer_fee_extension=to_bool(row.get("transfer_fee_upgradable"))
                or to_bool(row.get("transfer_fee")),
                possible_spam=to_bool(first_present(row, "is_honeypot", "honeypot")),
                score=to_decimal(row.get("trust_level")),
                signal_source="GoPlus",
                raw=dict(row),
            )
        )


__all__ = ["GoPlusAdapter", "BASE_URL", "SOLANA_CHAIN_ID"]
