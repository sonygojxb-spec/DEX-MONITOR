"""Jupiter adapter - trade venue (Quote + Swap).

Design reference: "Per-Integration Details" -> Jupiter, and "Signer / Key
Handling". Implements :class:`TradeVenueProvider`: the Quote API + Swap API
return a **serialized transaction to sign**, the user-configured slippage is
attached via Jupiter's native ``slippageBps`` parameter (Req 6.4), and on-chain
confirmation is polled via Solana RPC (Req 6.5/6.6).

**Signing is intentionally out of scope here (wired in Task 15.2).** The adapter
never holds key material and never receives a private key across this boundary:
:meth:`submit_order` accepts an already-signed serialized transaction on the
:class:`OrderRequest`, or - when an injected ``signer`` callback is provided -
asks it to sign the serialized transaction returned by the Swap API. Confirmation
polling delegates to an injected ``confirm_poller`` (typically
:meth:`SolanaRpcAdapter.poll_signature`) so this adapter performs no chain I/O of
its own beyond the Jupiter HTTP calls.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable, Mapping

from dex_agent.errors import ProviderError
from dex_agent.providers.adapters._common import (
    first_present,
    run_request,
    to_decimal,
)
from dex_agent.providers.clients import HttpClient
from dex_agent.providers.interfaces import (
    Confirmation,
    OrderRequest,
    SubmittedOrder,
    TradeVenueProvider,
)
from dex_agent.result import Err, Ok, Result

QUOTE_BASE = "https://quote-api.jup.ag"
PROVIDER = "Jupiter"

# An injected signer turns a serialized (unsigned) transaction into a signed one.
Signer = Callable[[str], str]
# An injected confirmation poller maps a tx id to a confirmation payload result.
ConfirmPoller = Callable[[str], Result]


def _slippage_bps(percent: Decimal) -> int:
    """Convert a slippage percent to Jupiter's basis-point parameter (Req 6.4)."""
    return int((percent * Decimal(100)).to_integral_value())


class JupiterAdapter(TradeVenueProvider):
    """Trade venue adapter over Jupiter Quote + Swap (signing wired in 15.2)."""

    def __init__(
        self,
        http: HttpClient,
        *,
        base_url: str = QUOTE_BASE,
        user_public_key: str | None = None,
        signer: Signer | None = None,
        confirm_poller: ConfirmPoller | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._http = http
        self._base = base_url.rstrip("/")
        self._user_public_key = user_public_key
        self._signer = signer
        self._confirm_poller = confirm_poller
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _get(self, path: str, params: Mapping[str, Any]) -> Result[Any]:
        return run_request(
            lambda: self._http.request(
                "GET", f"{self._base}{path}", headers={"accept": "application/json"}, params=params
            ),
            provider=PROVIDER,
        )

    def _post(self, path: str, json: Any) -> Result[Any]:
        return run_request(
            lambda: self._http.request(
                "POST", f"{self._base}{path}", headers={"accept": "application/json"}, json=json
            ),
            provider=PROVIDER,
        )

    def submit_order(self, order_request: OrderRequest) -> Result[SubmittedOrder]:
        # 1) Quote with the native slippage parameter (Req 6.4).
        quote_res = self._get(
            "/v6/quote",
            {
                "inputMint": order_request.input_mint,
                "outputMint": order_request.output_mint,
                "amount": str(order_request.amount),
                "slippageBps": _slippage_bps(order_request.max_slippage),
            },
        )
        if quote_res.is_err():
            return quote_res
        quote = quote_res.value

        # 2) Obtain the serialized swap transaction to sign.
        signed_tx = order_request.signed_transaction
        if signed_tx is None:
            swap_res = self._post(
                "/v6/swap",
                {
                    "quoteResponse": quote,
                    "userPublicKey": self._user_public_key,
                },
            )
            if swap_res.is_err():
                return swap_res
            swap = swap_res.value if isinstance(swap_res.value, Mapping) else {}
            serialized = first_present(swap, "swapTransaction", "swap_transaction")
            if serialized is None:
                return Err(ProviderError("Swap API returned no transaction", provider=PROVIDER))
            if self._signer is None:
                # Monitoring-only / no signer wired yet (Task 15.2): cannot submit.
                return Err(
                    ProviderError(
                        "no signer configured; cannot submit swap",
                        provider=PROVIDER,
                        context={"requires_signer": True},
                    )
                )
            signed_tx = self._signer(str(serialized))

        # 3) Broadcast the signed transaction.
        send_res = self._post("/v6/swap/send", {"signedTransaction": signed_tx})
        if send_res.is_err():
            return send_res
        body = send_res.value if isinstance(send_res.value, Mapping) else {}
        tx_id = first_present(body, "signature", "txid", "txId")
        if tx_id is None:
            return Err(ProviderError("send returned no signature", provider=PROVIDER))
        return Ok(
            SubmittedOrder(
                tx_id=str(tx_id),
                pair_id=order_request.pair_id,
                kind=order_request.kind,
                submitted_at=self._clock(),
                raw=dict(body),
            )
        )

    def poll_confirmation(
        self, tx_id: str, timeout: timedelta
    ) -> Result[Confirmation]:
        if self._confirm_poller is None:
            return Err(
                ProviderError("no confirmation poller configured", provider=PROVIDER)
            )
        poll = self._confirm_poller(tx_id)
        if poll.is_err():
            # Propagate TimedOut (not-yet-confirmed) / transport errors as-is.
            return poll
        tx = poll.value if isinstance(poll.value, Mapping) else {}
        meta = tx.get("meta") if isinstance(tx.get("meta"), Mapping) else {}
        if meta.get("err") is not None:
            return Err(
                ProviderError(
                    "transaction failed on-chain",
                    provider=PROVIDER,
                    context={"err": meta.get("err")},
                )
            )
        return Ok(
            Confirmation(
                tx_id=tx_id,
                confirmed=True,
                executed_price=to_decimal(first_present(tx, "executedPrice")),
                executed_qty=to_decimal(first_present(tx, "executedQty")),
                fee=to_decimal(meta.get("fee")),
                executed_slippage=to_decimal(first_present(tx, "executedSlippage")),
                confirmed_at=self._clock(),
                raw=dict(tx),
            )
        )


__all__ = ["JupiterAdapter", "QUOTE_BASE", "Signer", "ConfirmPoller"]
