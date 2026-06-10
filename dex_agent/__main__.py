"""Entry point for the DEX Trading Agent.

Run with:  python -m dex_agent

Starts the agent in MONITORING-ONLY mode (no wallet, no trading).
Reads secrets from a local .env file. Press Ctrl+C to stop.
"""

import os
from datetime import timedelta
from typing import Any, Mapping

import httpx
from dotenv import load_dotenv

load_dotenv()  # load secrets from .env

from dex_agent.agent import AgentSecrets, build_production_agent
from dex_agent.control.data_ingestor import DiscoveryFilters
from dex_agent.providers.clients import (
    ClientError,
    ClientTimeout,
    HttpResponse,
)

# ---------------------------------------------------------------------------
# Concrete transport clients (implement the project's HttpClient / RpcClient
# protocols using httpx, synchronously, as the adapters expect).
# ---------------------------------------------------------------------------

class HttpxClient:
    """Synchronous HttpClient implementation backed by httpx."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        try:
            resp = self._client.request(
                method,
                url,
                headers=dict(headers) if headers else None,
                params=dict(params) if params else None,
                json=json,
                timeout=timeout if timeout is not None else httpx.USE_CLIENT_DEFAULT,
            )
        except httpx.TimeoutException as e:
            raise ClientTimeout(str(e)) from e
        except httpx.HTTPError as e:
            raise ClientError(str(e)) from e

        try:
            body = resp.json()
        except Exception:
            body = None
        return HttpResponse(status=resp.status_code, json=body, headers=dict(resp.headers))

    def close(self) -> None:
        self._client.close()

class SolanaRpcClient:
    """Synchronous JSON-RPC RpcClient implementation backed by httpx."""

    def __init__(self, url: str, timeout: float = 30.0) -> None:
        self._url = url
        self._client = httpx.Client(timeout=timeout)
        self._id = 0

    def call(
        self,
        method: str,
        params: list[Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": method,
            "params": params or [],
        }
        try:
            resp = self._client.post(
                self._url,
                json=payload,
                timeout=timeout if timeout is not None else httpx.USE_CLIENT_DEFAULT,
            )
        except httpx.TimeoutException as e:
            raise ClientTimeout(str(e)) from e
        except httpx.HTTPError as e:
            raise ClientError(str(e)) from e

        if not (200 <= resp.status_code < 300):
            raise ClientError(f"RPC HTTP {resp.status_code}")
        try:
            data = resp.json()
        except Exception as e:
            raise ClientError(f"RPC malformed response: {e}") from e
        if isinstance(data, dict) and data.get("error"):
            raise ClientError(f"RPC error: {data['error']}")
        return data.get("result") if isinstance(data, dict) else None

    def close(self) -> None:
        self._client.close()

class NoOpSigner:
    """Monitoring-only signer: refuses to sign, so trading is impossible."""

    @property
    def public_key(self) -> str:
        return "NoOpSigner_MonitoringOnly"

    def sign_transaction(self, serialized_tx: str) -> str:
        raise RuntimeError(
            "Trading is disabled (monitoring-only mode). No signer configured."
        )

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"Missing required environment variable: {name}. "
            f"Set it in your .env file before running."
        )
    return value

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_agent() -> None:
    import time

    secrets = AgentSecrets(
        moralis_api_key=_require("MORALIS_API_KEY"),
        solana_rpc_url=_require("SOLANA_RPC_URL"),
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
        goplus_api_key=os.environ.get("GOPLUS_API_KEY", "").strip(),
    )

    http_client = HttpxClient(timeout=30.0)
    rpc_client = SolanaRpcClient(secrets.solana_rpc_url, timeout=30.0)

    try:
        agent = build_production_agent(
            secrets=secrets,
            http_client=http_client,
            rpc_client=rpc_client,
            signer=NoOpSigner(),
            webhook_url=os.environ.get("WEBHOOK_URL", "http://localhost:8080/webhook"),
            enable_dexscreener_fallback=True,
        )

        boot = agent.boot()
        print("=" * 56)
        print(" DEX Trading Agent  (MONITORING-ONLY)")
        print("=" * 56)
        print(f"  Solana RPC      : {secrets.solana_rpc_url}")
        print(f"  Moralis         : configured")
        print(f"  Telegram        : configured")
        print(f"  GoPlus fallback : {'configured' if secrets.goplus_api_key else 'off'}")
        print(f"  Trading         : DISABLED (no signer)")
        print(f"  monitoring_only : {boot.monitoring_only}")
        print(f"  recovery_ok     : {boot.recovery_ok}")
        print(f"  refresh={boot.config.refresh_interval_s}s  "
              f"signal={boot.config.signal_interval_s}s  "
              f"discovery={boot.config.discovery_scan_interval_s}s")
        print("-" * 56)
        print(" Running. Press Ctrl+C to stop.")
        print("-" * 56)
        
        # --- Seed the watchlist with specific tokens (comma-separated mints in SEED_TOKENS) ---
        from dex_agent.agent import Network
        seed = os.environ.get("SEED_TOKENS", "").strip()
        if seed:
            for mint in [m.strip() for m in seed.split(",") if m.strip()]:
                try:
                    res = agent.add_token(mint, Network.SOLANA)
                    if res.is_ok():
                        print(f"  seed add {mint[:8]}…: ok (pair={res.value.pair_id})")
                    else:
                        print(f"  seed add {mint[:8]}…: {res.error}")
                except Exception as e:
                    print(f"  seed add {mint[:8]}… error: {e!r}")
            print(f"  active pairs after seeding: {agent.orchestrator.active_count()}")

        orchestrator = agent.orchestrator
        data_ingestor = agent.data_ingestor
        refresh_interval = boot.config.refresh_interval_s
        discovery_interval = boot.config.discovery_scan_interval_s

        discovery_filters = DiscoveryFilters(
            exchange="pumpfun",
            # quote_assets / min_liquidity removed to widen the match
            max_age=timedelta(hours=24),
        )

        ticks_per_discovery = max(1, discovery_interval // refresh_interval)

        tick_count = 0
        while True:
            tick_count += 1

            # Periodic discovery scan
            if (tick_count - 1) % ticks_per_discovery == 0:
                try:
                    result = data_ingestor.discovery_scan(discovery_filters)
                    if result.is_ok():
                        outcome = result.value
                        print(f"[tick {tick_count}] discovery scan done | "
                              f"scanned={outcome.scanned} added={len(outcome.added)} | "
                              f"active pairs: {orchestrator.active_count()}")
                    else:
                        print(f"[tick {tick_count}] discovery error: {result.error}")
                except Exception as e:
                    print(f"[tick {tick_count}] discovery error: {e!r}")

            # Tick every active pair
            try:
                active = list(orchestrator.active_pairs())
            except Exception as e:
                print(f"[tick {tick_count}] could not list active pairs: {e!r}")
                active = []

            for pair_id in active:
                try:
                    orchestrator.tick(pair_id)
                except Exception as e:
                    print(f"[tick {tick_count}] tick error {pair_id}: {e!r}")

            if active:
                print(f"[tick {tick_count}] ticked {len(active)} pair(s)")
            elif tick_count <= 3:
                print(f"[tick {tick_count}] no active pairs yet; waiting for discovery...")

            time.sleep(refresh_interval)

    finally:
        http_client.close()
        rpc_client.close()

def main() -> None:
    try:
        run_agent()
    except KeyboardInterrupt:
        print("\nAgent stopped by user.")

if __name__ == "__main__":
    main()
