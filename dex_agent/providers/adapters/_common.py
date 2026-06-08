"""Shared helpers for the concrete adapters.

Centralizes the two things every REST adapter needs:

* **Transport-error mapping** - translate the transport exception taxonomy
  (:mod:`dex_agent.providers.clients`) and non-2xx responses onto the typed
  ``Result`` errors (:class:`~dex_agent.errors.TimedOut` /
  :class:`~dex_agent.errors.ProviderError`). Provider responses are untrusted
  input (design "Security Considerations" item 7), so parsing is defensive.
* **Lenient scalar coercion** - parse decimals/ints/bools/timestamps from JSON
  values that may be strings, numbers, or missing, without raising.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping

from dex_agent.errors import ProviderError, TimedOut
from dex_agent.providers.clients import (
    ClientError,
    ClientTimeout,
    HttpResponse,
    RateLimitExceeded,
)
from dex_agent.result import Err, Ok, Result


def to_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    """Coerce ``value`` to :class:`~decimal.Decimal`, or ``default`` on failure."""
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    """Coerce ``value`` to ``int``, or ``default`` on failure."""
    if value is None:
        return default
    try:
        return int(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return default


def to_bool(value: Any, default: bool | None = None) -> bool | None:
    """Coerce a JSON bool/str/number to ``bool``, or ``default`` when absent."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def parse_timestamp(value: Any, default: datetime | None = None) -> datetime:
    """Parse an ISO-8601 string or unix-epoch (s) into a tz-aware UTC datetime."""
    fallback = default or datetime.now(timezone.utc)
    if value is None:
        return fallback
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return fallback
    if isinstance(value, str):
        text = value.strip()
        # numeric epoch as string
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            pass
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return fallback
    return fallback


def map_transport_error(exc: Exception, *, provider: str) -> Result[Any]:
    """Map a transport exception onto a typed ``Result`` error."""
    if isinstance(exc, ClientTimeout):
        return Err(TimedOut(f"{provider} request timed out", timeout_s=None))
    if isinstance(exc, RateLimitExceeded):
        return Err(ProviderError(str(exc), provider=provider, context={"rate_limited": True}))
    if isinstance(exc, ClientError):
        return Err(ProviderError(str(exc), provider=provider))
    return Err(ProviderError(f"{provider} transport error: {exc}", provider=provider))


def check_response(response: HttpResponse, *, provider: str) -> Result[Any]:
    """Return ``Ok(json)`` for a 2xx response, else ``Err(ProviderError)``."""
    if not response.is_success():
        return Err(
            ProviderError(
                f"{provider} returned HTTP {response.status}",
                provider=provider,
                context={"status": response.status},
            )
        )
    return Ok(response.json)


def as_list(payload: Any, *keys: str) -> list[Any]:
    """Return a list from ``payload`` directly, or from the first present key.

    Handles the common API shapes where results are either a bare JSON array or
    wrapped under a key such as ``result`` / ``pairs`` / ``data``.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, Mapping):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def first_present(mapping: Mapping[str, Any], *keys: str) -> Any:
    """Return the value of the first present, non-``None`` key in ``mapping``."""
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def run_request(
    call: Callable[[], HttpResponse], *, provider: str
) -> Result[Any]:
    """Execute ``call``, mapping transport errors + non-2xx to typed errors."""
    try:
        response = call()
    except Exception as exc:  # noqa: BLE001 - mapped to typed Result errors
        return map_transport_error(exc, provider=provider)
    return check_response(response, provider=provider)


__all__ = [
    "to_decimal",
    "to_int",
    "to_bool",
    "parse_timestamp",
    "map_transport_error",
    "check_response",
    "as_list",
    "first_present",
    "run_request",
]
