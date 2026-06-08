"""Provider-selection / fallback strategy (reusable wrappers).

Design reference: "Provider-selection / fallback strategy". Each abstraction
resolves to its PRIMARY adapter first (Moralis for market/chain reads and
security risk inputs); on a typed :class:`~dex_agent.errors.ProviderError`, a
:class:`~dex_agent.errors.TimedOut`, or a missing required field, it falls back
to the configured fallback adapter **behind the same interface** (DexScreener
for :class:`MarketDataProvider`, GoPlus for :class:`ContractInspectorProvider`,
Solana RPC for base :class:`ChainDataProvider` reads). Otherwise the primary's
result stands.

**Fallbacks are optional and disabled by default**: construct a wrapper with
``fallback=None`` (the default) and it always returns the primary's result.
These wrappers implement the same interfaces, so the Data_Ingestor (Task 18)
can depend on the interface and be handed either a bare adapter or a
fallback-wrapped one without code changes.

The default fallback predicate triggers on ``ProviderError`` / ``TimedOut``
(a missing required field surfaces from an adapter as a ``ProviderError``). A
``NotFound`` from the primary is treated as a definitive answer and does **not**
trigger fallback by default; pass ``fallback_on_not_found=True`` to also fall
back on ``NotFound`` (e.g. to cross-check pair resolution).
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, TypeVar

from dex_agent.errors import AgentError, NotFound, ProviderError, TimedOut
from dex_agent.models import HolderBalance, Network, PairSnapshot
from dex_agent.providers.interfaces import (
    ChainDataProvider,
    ChainTx,
    ContractArtifact,
    ContractInspectorProvider,
    DiscoveryFilters,
    MarketDataProvider,
    SecurityInputs,
    StateHash,
    TxWindow,
)
from dex_agent.result import Result

T = TypeVar("T")

# A predicate deciding whether a primary error warrants trying the fallback.
FallbackPredicate = Callable[[AgentError], bool]


def default_should_fallback(error: AgentError) -> bool:
    """Fall back on provider/transport failures and timeouts (design default)."""
    return isinstance(error, (ProviderError, TimedOut))


def _select(
    primary_call: Callable[[], Result[T]],
    fallback_call: Callable[[], Result[T]] | None,
    should_fallback: FallbackPredicate,
) -> Result[T]:
    """Run primary; on a fallbackable error try the fallback when configured."""
    result = primary_call()
    if result.is_ok():
        return result
    if fallback_call is not None and should_fallback(result.error):
        return fallback_call()
    return result


class FallbackMarketDataProvider(MarketDataProvider):
    """A :class:`MarketDataProvider` that fails over primary -> fallback."""

    def __init__(
        self,
        primary: MarketDataProvider,
        fallback: MarketDataProvider | None = None,
        *,
        should_fallback: FallbackPredicate = default_should_fallback,
        fallback_on_not_found: bool = False,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        base = should_fallback
        if fallback_on_not_found:
            self._should = lambda e: base(e) or isinstance(e, NotFound)
        else:
            self._should = base

    @property
    def fallback_enabled(self) -> bool:
        return self._fallback is not None

    def resolve_pairs(
        self, token_address: str, network: Network
    ) -> Result[list[PairSnapshot]]:
        return _select(
            lambda: self._primary.resolve_pairs(token_address, network),
            (lambda: self._fallback.resolve_pairs(token_address, network))
            if self._fallback
            else None,
            self._should,
        )

    def fetch_pair_snapshot(self, pair_id: str) -> Result[PairSnapshot]:
        return _select(
            lambda: self._primary.fetch_pair_snapshot(pair_id),
            (lambda: self._fallback.fetch_pair_snapshot(pair_id))
            if self._fallback
            else None,
            self._should,
        )

    def discover_recent_pairs(
        self, filters: DiscoveryFilters, since: datetime
    ) -> Result[list[PairSnapshot]]:
        return _select(
            lambda: self._primary.discover_recent_pairs(filters, since),
            (lambda: self._fallback.discover_recent_pairs(filters, since))
            if self._fallback
            else None,
            self._should,
        )


class FallbackChainDataProvider(ChainDataProvider):
    """A :class:`ChainDataProvider` that fails over primary -> fallback."""

    def __init__(
        self,
        primary: ChainDataProvider,
        fallback: ChainDataProvider | None = None,
        *,
        should_fallback: FallbackPredicate = default_should_fallback,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._should = should_fallback

    @property
    def fallback_enabled(self) -> bool:
        return self._fallback is not None

    def fetch_contract(
        self, token_address: str, network: Network
    ) -> Result[ContractArtifact]:
        return _select(
            lambda: self._primary.fetch_contract(token_address, network),
            (lambda: self._fallback.fetch_contract(token_address, network))
            if self._fallback
            else None,
            self._should,
        )

    def fetch_contract_state_hash(self, token_address: str) -> Result[StateHash]:
        return _select(
            lambda: self._primary.fetch_contract_state_hash(token_address),
            (lambda: self._fallback.fetch_contract_state_hash(token_address))
            if self._fallback
            else None,
            self._should,
        )

    def fetch_holder_distribution(
        self, token_address: str
    ) -> Result[list[HolderBalance]]:
        return _select(
            lambda: self._primary.fetch_holder_distribution(token_address),
            (lambda: self._fallback.fetch_holder_distribution(token_address))
            if self._fallback
            else None,
            self._should,
        )

    def fetch_transactions(
        self, pair_id: str, window: TxWindow
    ) -> Result[list[ChainTx]]:
        return _select(
            lambda: self._primary.fetch_transactions(pair_id, window),
            (lambda: self._fallback.fetch_transactions(pair_id, window))
            if self._fallback
            else None,
            self._should,
        )


class FallbackContractInspectorProvider(ContractInspectorProvider):
    """A :class:`ContractInspectorProvider` failing over primary -> fallback."""

    def __init__(
        self,
        primary: ContractInspectorProvider,
        fallback: ContractInspectorProvider | None = None,
        *,
        should_fallback: FallbackPredicate = default_should_fallback,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._should = should_fallback

    @property
    def fallback_enabled(self) -> bool:
        return self._fallback is not None

    def inspect_token(
        self, token_address: str, network: Network
    ) -> Result[SecurityInputs]:
        return _select(
            lambda: self._primary.inspect_token(token_address, network),
            (lambda: self._fallback.inspect_token(token_address, network))
            if self._fallback
            else None,
            self._should,
        )


__all__ = [
    "FallbackPredicate",
    "default_should_fallback",
    "FallbackMarketDataProvider",
    "FallbackChainDataProvider",
    "FallbackContractInspectorProvider",
]
