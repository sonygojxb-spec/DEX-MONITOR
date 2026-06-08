"""Injected HTTP / JSON-RPC client abstractions and in-memory fakes.

Every concrete adapter (see :mod:`dex_agent.providers.adapters`) takes an
injected transport client so the adapter stays testable and **never makes a
real network or chain call in tests**. Two transport shapes are needed:

* :class:`HttpClient` - a minimal request/response protocol used by the REST
  adapters (Moralis, DexScreener, GoPlus, Jupiter, Telegram).
* :class:`RpcClient` - a JSON-RPC ``call(method, params)`` protocol used by the
  :class:`~dex_agent.providers.adapters.solana_rpc.SolanaRpcAdapter`.

Transport-level failures are surfaced as the small exception taxonomy below
(:class:`ClientTimeout`, :class:`ClientError`, :class:`RateLimitExceeded`). The
adapters catch these and map them onto the typed ``Result`` errors from
:mod:`dex_agent.errors` (``TimedOut`` / ``ProviderError``) so callers never see
a raw transport exception.

The :class:`FakeHttpClient` / :class:`FakeRpcClient` here are *transport* fakes
used by the thin adapter unit tests (Task 4.4). They are distinct from the
*provider* fakes in :mod:`dex_agent.providers.fakes`, which implement the
provider interfaces directly for business-logic tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Transport exception taxonomy
# ---------------------------------------------------------------------------


class ClientError(Exception):
    """A transport-level error (connection refused, 5xx, malformed response)."""


class ClientTimeout(ClientError):
    """A transport request exceeded its configured timeout."""


class RateLimitExceeded(ClientError):
    """A request was rejected locally because the rate-limit budget is exhausted.

    Raised by :class:`~dex_agent.providers.ratelimit.RateLimitedHttpClient` when
    the per-provider budget cannot cover a request's cost. Adapters map this to
    a :class:`~dex_agent.errors.ProviderError`.
    """


# ---------------------------------------------------------------------------
# HTTP transport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HttpResponse:
    """A minimal HTTP response: status code, decoded JSON body, and headers."""

    status: int
    json: Any = None
    headers: Mapping[str, str] = field(default_factory=dict)

    def is_success(self) -> bool:
        """True for 2xx status codes."""
        return 200 <= self.status < 300


@runtime_checkable
class HttpClient(Protocol):
    """A minimal injectable HTTP client.

    Implementations issue ``method`` against ``url`` and return an
    :class:`HttpResponse`. They raise :class:`ClientTimeout` on timeout and
    :class:`ClientError` for other transport failures. The real implementation
    (wrapping e.g. ``httpx``/``requests``) is wired at deployment; tests inject
    :class:`FakeHttpClient`.
    """

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
        ...


# ---------------------------------------------------------------------------
# JSON-RPC transport
# ---------------------------------------------------------------------------


@runtime_checkable
class RpcClient(Protocol):
    """A minimal injectable JSON-RPC client (Solana RPC).

    ``call`` issues a single JSON-RPC method and returns the decoded ``result``
    object (the adapter parses it). Implementations raise :class:`ClientTimeout`
    on timeout and :class:`ClientError` for other transport / RPC-level errors.
    """

    def call(
        self,
        method: str,
        params: list[Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        ...


# ---------------------------------------------------------------------------
# In-memory transport fakes (for adapter unit tests)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecordedHttpCall:
    """A single recorded HTTP call made against a :class:`FakeHttpClient`."""

    method: str
    url: str
    headers: Mapping[str, str]
    params: Mapping[str, Any] | None
    json: Any
    timeout: float | None


# A handler matches a recorded call and yields a response (or raises).
_HttpPredicate = Callable[[str, str, Mapping[str, Any] | None, Any], bool]


class FakeHttpClient:
    """A scriptable, call-recording :class:`HttpClient` for adapter tests.

    Register outcomes with :meth:`stub` (a JSON body) or :meth:`fail` (raise a
    transport exception). Handlers are matched in registration order by a
    method + URL-substring predicate. Every call is appended to
    :attr:`calls` so tests can assert request batching, headers, params, and
    JSON bodies. No real network access ever occurs.
    """

    def __init__(self) -> None:
        self.calls: list[RecordedHttpCall] = []
        self._handlers: list[tuple[_HttpPredicate, object]] = []

    # -- scripting -------------------------------------------------------
    def stub(
        self,
        url_contains: str,
        json: Any,
        *,
        status: int = 200,
        method: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> "FakeHttpClient":
        """Return ``HttpResponse(status, json)`` for matching requests."""
        response = HttpResponse(status=status, json=json, headers=headers or {})
        self._handlers.append((self._predicate(method, url_contains), response))
        return self

    def fail(
        self,
        url_contains: str,
        exc: Exception,
        *,
        method: str | None = None,
    ) -> "FakeHttpClient":
        """Raise ``exc`` for matching requests (e.g. ``ClientTimeout``)."""
        self._handlers.append((self._predicate(method, url_contains), exc))
        return self

    @staticmethod
    def _predicate(method: str | None, url_contains: str) -> _HttpPredicate:
        def pred(m: str, url: str, params: Mapping[str, Any] | None, body: Any) -> bool:
            if method is not None and m.upper() != method.upper():
                return False
            return url_contains in url

        return pred

    # -- HttpClient protocol --------------------------------------------
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
        self.calls.append(
            RecordedHttpCall(
                method=method,
                url=url,
                headers=dict(headers or {}),
                params=dict(params) if params is not None else None,
                json=json,
                timeout=timeout,
            )
        )
        for predicate, outcome in self._handlers:
            if predicate(method, url, params, json):
                if isinstance(outcome, Exception):
                    raise outcome
                assert isinstance(outcome, HttpResponse)
                return outcome
        raise ClientError(f"FakeHttpClient: no stub registered for {method} {url}")


@dataclass(frozen=True)
class RecordedRpcCall:
    """A single recorded JSON-RPC call made against a :class:`FakeRpcClient`."""

    method: str
    params: list[Any] | None
    timeout: float | None


class FakeRpcClient:
    """A scriptable, call-recording :class:`RpcClient` for adapter tests.

    Register a result per RPC method with :meth:`stub` or an exception with
    :meth:`fail`. Calls are recorded in :attr:`calls`.
    """

    def __init__(self) -> None:
        self.calls: list[RecordedRpcCall] = []
        self._results: dict[str, object] = {}

    def stub(self, method: str, result: Any) -> "FakeRpcClient":
        """Return ``result`` for ``method`` calls."""
        self._results[method] = result
        return self

    def fail(self, method: str, exc: Exception) -> "FakeRpcClient":
        """Raise ``exc`` for ``method`` calls."""
        self._results[method] = exc
        return self

    def call(
        self,
        method: str,
        params: list[Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        self.calls.append(RecordedRpcCall(method=method, params=params, timeout=timeout))
        if method not in self._results:
            raise ClientError(f"FakeRpcClient: no stub registered for {method}")
        outcome = self._results[method]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


__all__ = [
    "ClientError",
    "ClientTimeout",
    "RateLimitExceeded",
    "HttpResponse",
    "HttpClient",
    "RpcClient",
    "RecordedHttpCall",
    "RecordedRpcCall",
    "FakeHttpClient",
    "FakeRpcClient",
]
