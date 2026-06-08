"""Concrete Solana provider adapters behind the provider interfaces.

Design reference: "External Integrations" / "Per-Integration Details". Each
adapter implements one or more interfaces from
:mod:`dex_agent.providers.interfaces` and takes an **injected** transport client
(:class:`~dex_agent.providers.clients.HttpClient` /
:class:`~dex_agent.providers.clients.RpcClient`) so it never makes a real
network/chain call in tests.

* :class:`~dex_agent.providers.adapters.moralis.MoralisAdapter` - PRIMARY market,
  chain, and security-risk-input source (two hosts, ``X-API-Key``).
* :class:`~dex_agent.providers.adapters.solana_rpc.SolanaRpcAdapter` - base
  on-chain fallback and the authoritative SPL mint/freeze authority source.
* :class:`~dex_agent.providers.adapters.dexscreener.DexScreenerAdapter` - OPTIONAL
  market-data fallback (disabled unless configured).
* :class:`~dex_agent.providers.adapters.goplus.GoPlusAdapter` - OPTIONAL
  contract-inspection fallback (disabled unless configured).
* :class:`~dex_agent.providers.adapters.jupiter.JupiterAdapter` - trade venue
  (Quote+Swap; signing wired later in Task 15.2).
* :class:`~dex_agent.providers.adapters.telegram.TelegramChannel` - notification
  channel.
"""

from __future__ import annotations

from dex_agent.providers.adapters.dexscreener import DexScreenerAdapter
from dex_agent.providers.adapters.goplus import GoPlusAdapter
from dex_agent.providers.adapters.jupiter import JupiterAdapter
from dex_agent.providers.adapters.moralis import MoralisAdapter
from dex_agent.providers.adapters.solana_rpc import SolanaRpcAdapter
from dex_agent.providers.adapters.telegram import TelegramChannel

__all__ = [
    "MoralisAdapter",
    "SolanaRpcAdapter",
    "DexScreenerAdapter",
    "GoPlusAdapter",
    "JupiterAdapter",
    "TelegramChannel",
]
