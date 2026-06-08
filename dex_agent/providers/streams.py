"""Moralis Solana Streams: stream management + webhook intake.

Design reference: "Rate Limits & Real-Time Strategy" and "Per-Integration
Details" -> Real-time (Moralis Solana Streams). Streams are the PRIMARY
low-latency mechanism for rug/dump and other time-critical events (Req 5.3/5.4
and the <=5s exit alert of Req 5.5), removing the need for tight polling.

This module provides three things:

1. :class:`MoralisStreamsManager` - creates/updates a stream via
   ``PUT /streams/solana`` (host ``https://api.moralis-streams.com``) filtered by
   the watched ``mintAddresses``, through an injected
   :class:`StreamClient` so it is testable with an in-memory fake.
2. Balance-delta computation from a transaction's ``preTokenBalances`` /
   ``postTokenBalances`` (the SPL snapshot deltas).
3. :class:`MoralisWebhookIntake` - the publicly-reachable webhook handler. It
   implements the **empty-body verification handshake** (HTTP 200), is
   **idempotent keyed on the transaction ``signature``** with dedupe, and
   **ALWAYS returns HTTP 200** (even for duplicates, already-processed events, or
   its own downstream errors) so Moralis does not spuriously retry. It computes
   balance deltas, classifies liquidity-removal (rug) / dump events, and hands
   them off through an injected **event sink** callback (the clean seam to the
   not-yet-built Signal_Engine / Backend_Analyzer).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from dex_agent.errors import ProviderError
from dex_agent.providers.adapters._common import (
    map_transport_error,
    to_decimal,
)
from dex_agent.result import Err, Ok, Result

STREAMS_BASE = "https://api.moralis-streams.com"
PROVIDER = "MoralisStreams"


# ---------------------------------------------------------------------------
# Stream management client
# ---------------------------------------------------------------------------


@runtime_checkable
class StreamClient(Protocol):
    """Injected client for the Moralis Streams management API.

    Implementations issue the ``PUT /streams/solana`` request (and address
    add/remove) against ``https://api.moralis-streams.com`` using the
    ``x-api-key`` header. Tests inject :class:`FakeStreamClient`.
    """

    def put_stream(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


class FakeStreamClient:
    """In-memory :class:`StreamClient` for tests; records created streams."""

    def __init__(self) -> None:
        self.created: list[Mapping[str, Any]] = []
        self._next_id = 0
        self._error: Exception | None = None

    def fail_with(self, exc: Exception) -> None:
        self._error = exc

    def put_stream(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if self._error is not None:
            raise self._error
        self._next_id += 1
        record = {"id": f"stream-{self._next_id}", "status": "active", **dict(payload)}
        self.created.append(record)
        return record


@dataclass(frozen=True)
class StreamHandle:
    """A created stream's identity and echoed configuration."""

    id: str
    webhook_url: str
    mint_addresses: tuple[str, ...]
    status: str
    raw: Mapping[str, Any] = field(default_factory=dict)


class MoralisStreamsManager:
    """Creates / updates the Solana stream filtered by watched mints."""

    def __init__(
        self,
        client: StreamClient,
        *,
        api_key: str,
        webhook_url: str,
        tag: str = "dex-trading-agent",
        network: str = "mainnet",
        description: str = "DEX Trading Agent watched mints",
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._webhook_url = webhook_url
        self._tag = tag
        self._network = network
        self._description = description

    def create_stream(self, mint_addresses: list[str]) -> Result[StreamHandle]:
        """Create the stream via ``PUT /streams/solana`` (Req 5.3/5.4 wiring)."""
        payload = {
            "webhookUrl": self._webhook_url,
            "tag": self._tag,
            "network": self._network,
            "description": self._description,
            "mintAddresses": list(mint_addresses),
        }
        try:
            record = self._client.put_stream(payload)
        except Exception as exc:  # noqa: BLE001 - mapped to typed Result error
            return map_transport_error(exc, provider=PROVIDER)
        if not isinstance(record, Mapping) or "id" not in record:
            return Err(ProviderError("stream create returned no id", provider=PROVIDER))
        return Ok(
            StreamHandle(
                id=str(record["id"]),
                webhook_url=self._webhook_url,
                mint_addresses=tuple(mint_addresses),
                status=str(record.get("status", "")),
                raw=dict(record),
            )
        )


# ---------------------------------------------------------------------------
# Balance-delta computation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BalanceDelta:
    """A per-account SPL balance change derived from pre/postTokenBalances."""

    mint: str
    owner: str | None
    pre_amount: Decimal
    post_amount: Decimal

    @property
    def delta(self) -> Decimal:
        return self.post_amount - self.pre_amount


def _balance_key(entry: Mapping[str, Any]) -> tuple[Any, Any, Any]:
    return (entry.get("accountIndex"), entry.get("mint"), entry.get("owner"))


def _amount_of(entry: Mapping[str, Any]) -> Decimal:
    ui = entry.get("uiTokenAmount")
    if isinstance(ui, Mapping):
        return to_decimal(ui.get("amount"), Decimal(0)) or Decimal(0)
    return to_decimal(entry.get("amount"), Decimal(0)) or Decimal(0)


def compute_balance_deltas(transaction: Mapping[str, Any]) -> list[BalanceDelta]:
    """Compute per-account balance deltas from pre/postTokenBalances.

    Pairs entries by ``(accountIndex, mint, owner)``; an account present in only
    one of the snapshots is treated as having a zero balance on the missing
    side. The result captures exact token movement without replaying
    instructions (per the Streams design note).
    """
    pre = transaction.get("preTokenBalances") or []
    post = transaction.get("postTokenBalances") or []
    pre_by = {_balance_key(e): e for e in pre if isinstance(e, Mapping)}
    post_by = {_balance_key(e): e for e in post if isinstance(e, Mapping)}
    deltas: list[BalanceDelta] = []
    for key in {*pre_by, *post_by}:
        _, mint, owner = key
        pre_entry = pre_by.get(key)
        post_entry = post_by.get(key)
        pre_amt = _amount_of(pre_entry) if pre_entry else Decimal(0)
        post_amt = _amount_of(post_entry) if post_entry else Decimal(0)
        if pre_amt == post_amt:
            continue
        deltas.append(
            BalanceDelta(
                mint=str(mint) if mint is not None else "",
                owner=str(owner) if owner is not None else None,
                pre_amount=pre_amt,
                post_amount=post_amt,
            )
        )
    return deltas


# ---------------------------------------------------------------------------
# Stream events + intake
# ---------------------------------------------------------------------------


class StreamEventKind(Enum):
    """Classification of a stream transaction for downstream routing."""

    LIQUIDITY_REMOVAL = "LIQUIDITY_REMOVAL"  # rug candidate (Req 5.3)
    DUMP = "DUMP"  # large sell-side outflow candidate (Req 5.4)
    ACTIVITY = "ACTIVITY"  # generic swap/transfer activity (bot/sniper heuristics)


@dataclass(frozen=True)
class StreamEvent:
    """A normalized stream event handed off to the Signal_Engine / analyzer.

    ``kind`` is a tentative classification; the Signal_Engine (Task 12) applies
    the authoritative threshold predicates. ``net_by_mint`` is the summed delta
    per mint, useful for both rug/dump routing and bot/sniper heuristics.
    """

    signature: str
    kind: StreamEventKind
    deltas: tuple[BalanceDelta, ...]
    net_by_mint: Mapping[str, Decimal]
    block_time: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)


# The clean handoff seam: an injected callback consuming classified events.
EventSink = Callable[[StreamEvent], None]


@dataclass(frozen=True)
class WebhookResponse:
    """The HTTP response the intake hands back. ``status_code`` is always 200."""

    status_code: int
    body: Mapping[str, Any]


class MoralisWebhookIntake:
    """Idempotent, always-200 Moralis Solana Streams webhook handler.

    Args:
        sink: the event-sink callback (handoff to Signal_Engine / analyzer).
        watched_mints: optional set of mints of interest; when provided, only
            deltas/events for these mints drive rug/dump classification.
        rug_drop_threshold_pct: a watched mint's net negative delta exceeding
            this percentage of its pre-balance is tentatively flagged
            ``LIQUIDITY_REMOVAL`` (the Signal_Engine confirms, Req 5.3).
        seen: optional pre-seeded dedupe store (set of signatures).
    """

    def __init__(
        self,
        sink: EventSink,
        *,
        watched_mints: set[str] | None = None,
        rug_drop_threshold_pct: Decimal = Decimal(50),
        seen: set[str] | None = None,
    ) -> None:
        self._sink = sink
        self._watched = watched_mints
        self._rug_threshold = rug_drop_threshold_pct
        self._seen: set[str] = seen if seen is not None else set()

    @property
    def processed_signatures(self) -> set[str]:
        return set(self._seen)

    def handle(self, payload: Mapping[str, Any] | None) -> WebhookResponse:
        """Handle one webhook POST. Always returns HTTP 200.

        * Empty / no-``transactions`` body -> verification handshake (200).
        * Each transaction is deduped on ``signature``; duplicates are skipped
          but still yield 200.
        * A failure inside the event sink is swallowed (still 200) so Moralis
          does not retry our own downstream error.
        """
        # Verification handshake: Moralis posts an empty body to verify the URL.
        if not payload or "transactions" not in payload:
            return WebhookResponse(200, {"ok": True, "verification": True})

        transactions = payload.get("transactions") or []
        block = payload.get("block") if isinstance(payload.get("block"), Mapping) else {}
        block_time = self._block_time(block)

        processed = 0
        duplicates = 0
        sink_errors = 0
        for tx in transactions:
            if not isinstance(tx, Mapping):
                continue
            signature = tx.get("signature")
            if not signature:
                continue
            signature = str(signature)
            if signature in self._seen:
                duplicates += 1
                continue
            # Mark processed BEFORE dispatch so a downstream error cannot cause a
            # reprocessing on retry (idempotency keyed on signature).
            self._seen.add(signature)
            event = self._build_event(signature, tx, block_time)
            try:
                self._sink(event)
                processed += 1
            except Exception:  # noqa: BLE001 - never propagate; always return 200
                sink_errors += 1

        return WebhookResponse(
            200,
            {
                "ok": True,
                "processed": processed,
                "duplicates": duplicates,
                "sink_errors": sink_errors,
            },
        )

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _block_time(block: Mapping[str, Any]) -> datetime | None:
        bt = block.get("blockTime")
        if bt is None:
            return None
        try:
            return datetime.fromtimestamp(float(bt), tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None

    def _build_event(
        self, signature: str, tx: Mapping[str, Any], block_time: datetime | None
    ) -> StreamEvent:
        deltas = compute_balance_deltas(tx)
        net_by_mint: dict[str, Decimal] = {}
        pre_by_mint: dict[str, Decimal] = {}
        for d in deltas:
            net_by_mint[d.mint] = net_by_mint.get(d.mint, Decimal(0)) + d.delta
            pre_by_mint[d.mint] = pre_by_mint.get(d.mint, Decimal(0)) + d.pre_amount
        kind = self._classify(net_by_mint, pre_by_mint)
        return StreamEvent(
            signature=signature,
            kind=kind,
            deltas=tuple(deltas),
            net_by_mint=net_by_mint,
            block_time=block_time,
            raw=dict(tx),
        )

    def _classify(
        self, net_by_mint: Mapping[str, Decimal], pre_by_mint: Mapping[str, Decimal]
    ) -> StreamEventKind:
        """Tentatively classify the event for routing (Signal_Engine confirms).

        A large net negative movement of a watched mint relative to its
        pre-balance is a liquidity-removal (rug) candidate; any other net
        negative movement is a dump candidate; otherwise generic activity that
        still feeds the bot/sniper heuristics.
        """
        mints = net_by_mint.keys()
        if self._watched is not None:
            mints = [m for m in mints if m in self._watched]
        worst_kind = StreamEventKind.ACTIVITY
        for mint in mints:
            net = net_by_mint.get(mint, Decimal(0))
            if net >= 0:
                continue
            pre = pre_by_mint.get(mint, Decimal(0))
            if pre > 0:
                drop_pct = (-net) / pre * Decimal(100)
                if drop_pct >= self._rug_threshold:
                    return StreamEventKind.LIQUIDITY_REMOVAL
            worst_kind = StreamEventKind.DUMP
        return worst_kind


__all__ = [
    "STREAMS_BASE",
    "StreamClient",
    "FakeStreamClient",
    "StreamHandle",
    "MoralisStreamsManager",
    "BalanceDelta",
    "compute_balance_deltas",
    "StreamEventKind",
    "StreamEvent",
    "EventSink",
    "WebhookResponse",
    "MoralisWebhookIntake",
]
