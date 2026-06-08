"""Sanity tests for the shared Result type and typed error taxonomy.

These confirm the test harness (pytest + Hypothesis, default profile
max_examples=100) is wired correctly and exercise the foundational Result/error
types introduced in task 1.1.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent import (
    Err,
    NotFound,
    Ok,
    ProviderError,
    Result,
    TimedOut,
    Unverified,
    is_err,
    is_ok,
)


# --------------------------------------------------------------------------
# Unit tests: specific behaviors and edge cases
# --------------------------------------------------------------------------


def test_ok_holds_value_and_reports_ok():
    r: Result[int] = Ok(42)
    assert r.is_ok() is True
    assert r.is_err() is False
    assert is_ok(r) is True
    assert is_err(r) is False
    assert r.value == 42
    assert r.unwrap() == 42


def test_err_holds_error_and_reports_err():
    err = NotFound("missing", identifier="abc")
    r: Result = Err(err)
    assert r.is_err() is True
    assert r.is_ok() is False
    assert is_err(r) is True
    assert r.error is err


def test_ok_has_no_error_attribute():
    r: Result[int] = Ok(1)
    try:
        _ = r.error
    except AttributeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Ok.error should raise AttributeError")


def test_err_has_no_value_attribute():
    r: Result = Err(TimedOut("slow", timeout_s=30.0))
    try:
        _ = r.value
    except AttributeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Err.value should raise AttributeError")


def test_map_transforms_ok_and_skips_err():
    assert Ok(2).map(lambda x: x * 3).unwrap() == 6
    err = ProviderError("boom", provider="moralis")
    assert Err(err).map(lambda x: x * 3).error is err


def test_and_then_chains_on_ok_and_short_circuits_on_err():
    def half(x: int) -> Result[float]:
        return Ok(x / 2)

    assert Ok(10).and_then(half).unwrap() == 5.0
    err = NotFound("nope")
    assert Err(err).and_then(half).error is err


def test_map_err_transforms_error_only_on_err():
    err = Unverified("unreadable", subject="mint")
    replaced = Err(err).map_err(lambda e: NotFound("remapped"))
    assert isinstance(replaced.error, NotFound)
    # map_err is a no-op on Ok
    assert Ok(5).map_err(lambda e: NotFound("x")).unwrap() == 5


def test_unwrap_or_returns_default_on_err():
    assert Ok(7).unwrap_or(0) == 7
    assert Err(TimedOut("t")).unwrap_or(0) == 0


def test_err_unwrap_raises_the_typed_error():
    err = ProviderError("down", provider="jupiter")
    try:
        Err(err).unwrap()
    except ProviderError as raised:
        assert raised is err
    else:  # pragma: no cover
        raise AssertionError("Err.unwrap should raise the carried error")


def test_error_taxonomy_carries_context():
    pe = ProviderError("rate limited", provider="moralis", context={"status": 429})
    assert pe.provider == "moralis"
    assert pe.context["status"] == 429
    assert pe.message == "rate limited"
    assert TimedOut("x", timeout_s=5.0).timeout_s == 5.0
    assert Unverified("x", subject="s").subject == "s"
    assert NotFound("x", identifier="i").identifier == "i"


def test_errors_are_immutable():
    pe = ProviderError("frozen")
    try:
        pe.detail = "mutated"  # type: ignore[misc]
    except Exception:
        pass
    else:  # pragma: no cover
        raise AssertionError("frozen dataclass error should not be mutable")


# --------------------------------------------------------------------------
# Property-based tests (confirm Hypothesis harness works)
# --------------------------------------------------------------------------


@given(st.integers())
def test_property_ok_is_always_ok_and_roundtrips(value: int):
    r: Result[int] = Ok(value)
    assert r.is_ok() and not r.is_err()
    assert r.unwrap() == value
    # mapping with identity preserves the value
    assert r.map(lambda x: x).unwrap() == value


@given(st.text())
def test_property_err_is_always_err_and_preserves_error(detail: str):
    err = ProviderError(detail)
    r: Result = Err(err)
    assert r.is_err() and not r.is_ok()
    assert r.error is err
    # mapping the success channel is a no-op on Err
    assert r.map(lambda x: x).error is err


@settings(max_examples=100)
@given(st.integers(), st.integers())
def test_property_and_then_associativity_on_ok(a: int, b: int):
    # (Ok(a).and_then(f)) where f adds b equals Ok(a + b)
    result = Ok(a).and_then(lambda x: Ok(x + b))
    assert result.unwrap() == a + b
