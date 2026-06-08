"""External provider interfaces, in-memory fakes, and concrete Solana adapters.

This sub-package implements the design's "Data Ingestion Strategy" and "External
Integrations": all external data acquisition, trade execution, and notification
sits behind the interfaces in :mod:`~dex_agent.providers.interfaces`, which
business logic depends on exclusively. Three families of implementation are
provided:

* **In-memory fakes** (:mod:`~dex_agent.providers.fakes`) - scriptable,
  failure-injectable, call-recording substitutes used by property / unit /
  integration tests so trade-execution safety is exercised without network or
  chain calls.
* **Concrete adapters** (:mod:`~dex_agent.providers.adapters`) - the Solana
  wiring: ``MoralisAdapter`` (PRIMARY), ``SolanaRpcAdapter`` (authority +
  base fallback), optional ``DexScreenerAdapter`` / ``GoPlusAdapter`` fallbacks,
  ``JupiterAdapter`` (trade venue), and ``TelegramChannel``. Each takes an
  injected HTTP/RPC client (:mod:`~dex_agent.providers.clients`).
* **Cross-cutting concerns** - the provider-selection / fallback wrappers
  (:mod:`~dex_agent.providers.selection`), the per-provider CU/token-bucket rate
  limiter (:mod:`~dex_agent.providers.ratelimit`), and the Moralis Solana Streams
  webhook intake (:mod:`~dex_agent.providers.streams`).
"""

from __future__ import annotations

from dex_agent.providers.adapters import (
    DexScreenerAdapter,
    GoPlusAdapter,
    JupiterAdapter,
    MoralisAdapter,
    SolanaRpcAdapter,
    TelegramChannel,
)
from dex_agent.providers.clients import (
    ClientError,
    ClientTimeout,
    FakeHttpClient,
    FakeRpcClient,
    HttpClient,
    HttpResponse,
    RateLimitExceeded,
    RpcClient,
)
from dex_agent.providers.fakes import (
    FakeChainDataProvider,
    FakeContractInspectorProvider,
    FakeMarketDataProvider,
    FakeNotificationChannel,
    FakeTradeVenueProvider,
)
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
from dex_agent.providers.ratelimit import (
    DEXSCREENER_RPM,
    MORALIS_CU_COSTS,
    ProviderRateLimiter,
    RateLimitedHttpClient,
    TokenBucket,
    moralis_cu_for,
)
from dex_agent.providers.selection import (
    FallbackChainDataProvider,
    FallbackContractInspectorProvider,
    FallbackMarketDataProvider,
    default_should_fallback,
)
from dex_agent.providers.streams import (
    BalanceDelta,
    EventSink,
    FakeStreamClient,
    MoralisStreamsManager,
    MoralisWebhookIntake,
    StreamClient,
    StreamEvent,
    StreamEventKind,
    StreamHandle,
    WebhookResponse,
    compute_balance_deltas,
)

__all__ = [
    # interfaces
    "MarketDataProvider",
    "ChainDataProvider",
    "ContractInspectorProvider",
    "TradeVenueProvider",
    "NotificationChannel",
    # interface DTOs
    "DiscoveryFilters",
    "ContractArtifact",
    "StateHash",
    "TxWindow",
    "ChainTx",
    "SecurityInputs",
    "OrderRequest",
    "SubmittedOrder",
    "Confirmation",
    "Alert",
    "DeliveryResult",
    # transport clients
    "HttpClient",
    "RpcClient",
    "HttpResponse",
    "FakeHttpClient",
    "FakeRpcClient",
    "ClientError",
    "ClientTimeout",
    "RateLimitExceeded",
    # provider fakes
    "FakeMarketDataProvider",
    "FakeChainDataProvider",
    "FakeContractInspectorProvider",
    "FakeTradeVenueProvider",
    "FakeNotificationChannel",
    # concrete adapters
    "MoralisAdapter",
    "SolanaRpcAdapter",
    "DexScreenerAdapter",
    "GoPlusAdapter",
    "JupiterAdapter",
    "TelegramChannel",
    # rate limiting
    "TokenBucket",
    "ProviderRateLimiter",
    "RateLimitedHttpClient",
    "MORALIS_CU_COSTS",
    "DEXSCREENER_RPM",
    "moralis_cu_for",
    # provider selection / fallback
    "FallbackMarketDataProvider",
    "FallbackChainDataProvider",
    "FallbackContractInspectorProvider",
    "default_should_fallback",
    # streams
    "StreamClient",
    "FakeStreamClient",
    "StreamHandle",
    "MoralisStreamsManager",
    "BalanceDelta",
    "compute_balance_deltas",
    "StreamEvent",
    "StreamEventKind",
    "EventSink",
    "WebhookResponse",
    "MoralisWebhookIntake",
]
