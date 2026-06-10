"""In-memory provider fakes for property, unit, and integration tests.

Design reference: "Testing Strategy" - external providers MUST be replaced with
in-memory fakes so input variation is cheap and trade-execution safety can be
exercised at scale without real network/chain calls. These fakes implement the
provider interfaces in :mod:`dex_agent.providers.interfaces` directly (they are
*not* transport fakes - that is :mod:`dex_agent.providers.clients`).

Every fake supports:

* **Scriptable responses** - seed the data it should return per key.
* **Injectable failures / timeouts** - queue or pin a typed error for a method
  (or a specific key) so callers can exercise ``ProviderError`` / ``TimedOut`` /
  ``Unverified`` / ``NotFound`` paths deterministically.
* **Recorded calls** - every method appends a ``(method, args)`` tuple to
  ``calls`` so tests can assert how the provider was used (e.g. batching).

Business logic depends only on the interfaces, so these fakes are drop-in
substitutes for the concrete adapters.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Deque

from dex_agent.errors import AgentError, NotFound, ProviderError
from dex_agent.models import HolderBalance, Network, PairSnapshot, Severity
from dex_agent.providers.interfaces import (
    Alert,
    ChainDataProvider,
    ChainTx,
    Confirmation,
    ContractArtifact,
    ContractInspectorProvider,
    DeliveryResult,
    DiscoveryFilters,
    MarketDataProvider,
    NotificationChannel,
    OrderRequest,
    SecurityInputs,
    StateHash,
    SubmittedOrder,
    TradeVenueProvider,
    TxWindow,
)
from dex_agent.result import Err, Ok, Result


@dataclass
class _Recorder:
    """Mixin-style helper that records calls and serves queued failures."""

    calls: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)
    # method-name -> queue of errors to raise (one per call) before succeeding
    _failures: dict[str, Deque[AgentError]] = field(default_factory=dict)
    # method-name -> sticky error returned on every call until cleared
    _sticky: dict[str, AgentError] = field(default_factory=dict)

    def record(self, method: str, *args: Any) -> None:
        self.calls.append((method, args))

    def fail_next(self, method: str, error: AgentError) -> None:
        """Queue ``error`` to be returned on the next call to ``method``."""
        self._failures.setdefault(method, deque()).append(error)

    def fail_always(self, method: str, error: AgentError) -> None:
        """Return ``error`` on every call to ``method`` until cleared."""
        self._sticky[method] = error

    def clear_failures(self, method: str | None = None) -> None:
        """Clear queued/sticky failures for ``method`` (or all when ``None``)."""
        if method is None:
            self._failures.clear()
            self._sticky.clear()
        else:
            self._failures.pop(method, None)
            self._sticky.pop(method, None)

    def _next_error(self, method: str) -> AgentError | None:
        if method in self._sticky:
            return self._sticky[method]
        queue = self._failures.get(method)
        if queue:
            return queue.popleft()
        return None


class FakeMarketDataProvider(_Recorder, MarketDataProvider):
    """Scriptable in-memory :class:`MarketDataProvider`."""

    def __init__(self) -> None:
        super().__init__()
        self._pairs_by_token: dict[str, list[PairSnapshot]] = {}
        self._snapshots: dict[str, PairSnapshot] = {}
        self._discoveries: list[PairSnapshot] = []

    # -- scripting -------------------------------------------------------
    def set_pairs(self, token_address: str, pairs: list[PairSnapshot]) -> None:
        self._pairs_by_token[token_address] = list(pairs)

    def set_snapshot(self, snapshot: PairSnapshot) -> None:
        self._snapshots[snapshot.pair_id] = snapshot

    def set_discoveries(self, pairs: list[PairSnapshot]) -> None:
        self._discoveries = list(pairs)

    # -- MarketDataProvider ---------------------------------------------
    def resolve_pairs(
        self, token_address: str, network: Network
    ) -> Result[list[PairSnapshot]]:
        self.record("resolve_pairs", token_address, network)
        err = self._next_error("resolve_pairs")
        if err is not None:
            return Err(err)
        pairs = self._pairs_by_token.get(token_address)
        if not pairs:
            return Err(NotFound("no pairs for token", identifier=token_address))
        return Ok(list(pairs))

    def fetch_pair_snapshot(self, pair_id: str, *, token_address: str | None = None) -> Result[PairSnapshot]:
        self.record("fetch_pair_snapshot", pair_id)
        err = self._next_error("fetch_pair_snapshot")
        if err is not None:
            return Err(err)
        snapshot = self._snapshots.get(pair_id)
        if snapshot is None:
            return Err(ProviderError("no snapshot", provider="fake", context={"pair_id": pair_id}))
        return Ok(snapshot)

    def discover_recent_pairs(
        self, filters: DiscoveryFilters, since: datetime
    ) -> Result[list[PairSnapshot]]:
        self.record("discover_recent_pairs", filters, since)
        err = self._next_error("discover_recent_pairs")
        if err is not None:
            return Err(err)
        fresh = [p for p in self._discoveries if p.fetched_at >= since]
        return Ok(fresh)


class FakeChainDataProvider(_Recorder, ChainDataProvider):
    """Scriptable in-memory :class:`ChainDataProvider`."""

    def __init__(self) -> None:
        super().__init__()
        self._contracts: dict[str, ContractArtifact] = {}
        self._state_hashes: dict[str, StateHash] = {}
        self._holders: dict[str, list[HolderBalance]] = {}
        self._transactions: dict[str, list[ChainTx]] = {}

    # -- scripting -------------------------------------------------------
    def set_contract(self, artifact: ContractArtifact) -> None:
        self._contracts[artifact.token_address] = artifact

    def set_state_hash(self, token_address: str, state_hash: StateHash) -> None:
        self._state_hashes[token_address] = state_hash

    def set_holders(self, token_address: str, holders: list[HolderBalance]) -> None:
        self._holders[token_address] = list(holders)

    def set_transactions(self, pair_id: str, txs: list[ChainTx]) -> None:
        self._transactions[pair_id] = list(txs)

    # -- ChainDataProvider ----------------------------------------------
    def fetch_contract(
        self, token_address: str, network: Network
    ) -> Result[ContractArtifact]:
        self.record("fetch_contract", token_address, network)
        err = self._next_error("fetch_contract")
        if err is not None:
            return Err(err)
        artifact = self._contracts.get(token_address)
        if artifact is None:
            return Err(ProviderError("no contract", provider="fake", context={"addr": token_address}))
        return Ok(artifact)

    def fetch_contract_state_hash(self, token_address: str) -> Result[StateHash]:
        self.record("fetch_contract_state_hash", token_address)
        err = self._next_error("fetch_contract_state_hash")
        if err is not None:
            return Err(err)
        state_hash = self._state_hashes.get(token_address)
        if state_hash is None:
            return Err(ProviderError("no state hash", provider="fake"))
        return Ok(state_hash)

    def fetch_holder_distribution(
        self, token_address: str
    ) -> Result[list[HolderBalance]]:
        self.record("fetch_holder_distribution", token_address)
        err = self._next_error("fetch_holder_distribution")
        if err is not None:
            return Err(err)
        return Ok(list(self._holders.get(token_address, [])))

    def fetch_transactions(
        self, pair_id: str, window: TxWindow
    ) -> Result[list[ChainTx]]:
        self.record("fetch_transactions", pair_id, window)
        err = self._next_error("fetch_transactions")
        if err is not None:
            return Err(err)
        txs = [
            t
            for t in self._transactions.get(pair_id, [])
            if window.start <= t.block_time <= window.end
        ]
        return Ok(txs)


class FakeContractInspectorProvider(_Recorder, ContractInspectorProvider):
    """Scriptable in-memory :class:`ContractInspectorProvider`."""

    def __init__(self) -> None:
        super().__init__()
        self._inputs: dict[str, SecurityInputs] = {}

    def set_inputs(self, inputs: SecurityInputs) -> None:
        self._inputs[inputs.token_address] = inputs

    def inspect_token(
        self, token_address: str, network: Network
    ) -> Result[SecurityInputs]:
        self.record("inspect_token", token_address, network)
        err = self._next_error("inspect_token")
        if err is not None:
            return Err(err)
        inputs = self._inputs.get(token_address)
        if inputs is None:
            return Err(ProviderError("no security inputs", provider="fake"))
        return Ok(inputs)


class FakeTradeVenueProvider(_Recorder, TradeVenueProvider):
    """Scriptable in-memory :class:`TradeVenueProvider`.

    Seed confirmations per ``tx_id`` and a deterministic tx-id sequence; queue
    typed failures to exercise submission failure (Req 6.7) and confirmation
    timeout (Req 6.6) paths without a real venue.
    """

    def __init__(self, *, now: datetime | None = None) -> None:
        super().__init__()
        self._now = now or datetime(2025, 1, 1)
        self._tx_seq = 0
        self._confirmations: dict[str, Confirmation] = {}
        self.submitted: list[SubmittedOrder] = []

    def set_confirmation(self, tx_id: str, confirmation: Confirmation) -> None:
        self._confirmations[tx_id] = confirmation

    def _next_tx_id(self) -> str:
        self._tx_seq += 1
        return f"faketx-{self._tx_seq}"

    def submit_order(self, order_request: OrderRequest) -> Result[SubmittedOrder]:
        self.record("submit_order", order_request)
        err = self._next_error("submit_order")
        if err is not None:
            return Err(err)
        submitted = SubmittedOrder(
            tx_id=self._next_tx_id(),
            pair_id=order_request.pair_id,
            kind=order_request.kind,
            submitted_at=self._now,
        )
        self.submitted.append(submitted)
        return Ok(submitted)

    def poll_confirmation(
        self, tx_id: str, timeout: timedelta
    ) -> Result[Confirmation]:
        self.record("poll_confirmation", tx_id, timeout)
        err = self._next_error("poll_confirmation")
        if err is not None:
            return Err(err)
        confirmation = self._confirmations.get(tx_id)
        if confirmation is None:
            return Err(ProviderError("no confirmation scripted", provider="fake"))
        return Ok(confirmation)


class FakeNotificationChannel(_Recorder, NotificationChannel):
    """Scriptable in-memory :class:`NotificationChannel`.

    Records delivered alerts; queue failures to exercise the Notifier retry /
    final-status policy (Req 8.4/8.5).
    """

    def __init__(self, *, name: str = "fake") -> None:
        super().__init__()
        self.name = name
        self.delivered: list[Alert] = []

    def deliver(self, alert: Alert) -> Result[DeliveryResult]:
        self.record("deliver", alert)
        err = self._next_error("deliver")
        if err is not None:
            return Err(err)
        self.delivered.append(alert)
        return Ok(DeliveryResult(channel=self.name, delivered=True))


__all__ = [
    "FakeMarketDataProvider",
    "FakeChainDataProvider",
    "FakeContractInspectorProvider",
    "FakeTradeVenueProvider",
    "FakeNotificationChannel",
]
