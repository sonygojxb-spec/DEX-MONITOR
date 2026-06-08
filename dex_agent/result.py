"""The shared ``Result`` type: a success value or a typed error.

Every cross-component operation returns an explicit ``Result`` instead of
throwing. A ``Result`` is one of:

* ``Ok(value)``  - the operation succeeded and carries a success value.
* ``Err(error)`` - the operation failed and carries a typed error
  (see :mod:`dex_agent.errors`).

The type is a frozen, immutable discriminated union. Pattern-matching and the
``is_ok`` / ``is_err`` predicates let callers branch deterministically. Because
results are values rather than exceptions, no failure path needs to perform
partial state mutation: a component computes a ``Result`` and the caller decides
what to persist.

Example::

    def fetch(pair_id: str) -> Result[Snapshot]:
        if pair_id not in store:
            return Err(NotFound("no such pair", identifier=pair_id))
        return Ok(store[pair_id])

    r = fetch("abc")
    if r.is_ok():
        use(r.value)
    else:
        handle(r.error)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, NoReturn, TypeVar, Union

from dex_agent.errors import AgentError

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E", bound=AgentError)


@dataclass(frozen=True)
class Ok(Generic[T]):
    """A successful result carrying a ``value``."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    @property
    def error(self) -> NoReturn:
        raise AttributeError("Ok result has no error")

    def map(self, fn: Callable[[T], U]) -> "Result[U]":
        """Transform the success value, leaving errors untouched."""
        return Ok(fn(self.value))

    def map_err(self, fn: Callable[[AgentError], AgentError]) -> "Result[T]":
        """No-op on success."""
        return self

    def and_then(self, fn: Callable[[T], "Result[U]"]) -> "Result[U]":
        """Chain another result-returning operation on the success value."""
        return fn(self.value)

    def unwrap(self) -> T:
        """Return the success value."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value


@dataclass(frozen=True)
class Err(Generic[E]):
    """A failed result carrying a typed ``error``."""

    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    @property
    def value(self) -> NoReturn:
        raise AttributeError("Err result has no value")

    def map(self, fn: Callable[..., object]) -> "Err[E]":
        """No-op on failure; the error is propagated unchanged."""
        return self

    def map_err(self, fn: Callable[[E], AgentError]) -> "Result":
        """Transform the carried error."""
        return Err(fn(self.error))

    def and_then(self, fn: Callable[..., object]) -> "Err[E]":
        """No-op on failure; short-circuits the chain."""
        return self

    def unwrap(self) -> NoReturn:
        """Raise the carried error (boundary use only)."""
        raise self.error

    def unwrap_or(self, default: T) -> T:
        return default


# A Result is the discriminated union of Ok and Err.
Result = Union[Ok[T], Err[E]]


def is_ok(result: "Result") -> bool:
    """Free-function predicate mirroring ``result.is_ok()``."""
    return isinstance(result, Ok)


def is_err(result: "Result") -> bool:
    """Free-function predicate mirroring ``result.is_err()``."""
    return isinstance(result, Err)


__all__ = [
    "Result",
    "Ok",
    "Err",
    "is_ok",
    "is_err",
]
