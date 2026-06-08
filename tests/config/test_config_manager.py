"""Tests for the Config_Manager (Task 5).

Covers the design's Correctness Properties:

* Property 29 - configuration validation accepts exactly in-range numeric values
  (subtask 5.2, Req 9.1, 9.2, 9.3, 9.7);
* Property 30 - configuration persistence round-trip and latest-wins
  (subtask 5.3, Req 9.4, 9.5);
* Property 31 - documented defaults fall within their allowed ranges
  (subtask 5.4, Req 9.6);

plus a unit test for the persistence-failure indication (subtask 5.5, Req 9.7)
and a handful of example-based checks for the validation/persistence contract.
"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.config import (
    DEFAULTS,
    PARAM_RANGES,
    ConfigManager,
    ConfigPersistenceError,
    ConfigValidationError,
    ParamRange,
)
from dex_agent.config.manager import (
    REASON_MISSING,
    REASON_NON_NUMERIC,
    REASON_OUT_OF_RANGE,
)
from dex_agent.models import Configuration
from dex_agent.repositories import InMemoryConfigRepository
from dex_agent.repositories.interfaces import ConfigRepository
from dex_agent.result import Err, Ok, Result

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

NON_NUMERIC_VALUES = ["", "12", "abc", True, False, [1], {"a": 1}, (), object()]


def valid_value(name: str, pr: ParamRange) -> st.SearchStrategy[object]:
    """An in-range numeric value of the parameter's type."""
    if pr.integer:
        return st.integers(min_value=int(pr.low), max_value=int(pr.high))
    return st.decimals(
        min_value=pr.low,
        max_value=pr.high,
        allow_nan=False,
        allow_infinity=False,
        places=4,
    )


def below_range(pr: ParamRange) -> st.SearchStrategy[object]:
    """A numeric value strictly below ``pr.low``."""
    if pr.integer:
        return st.integers(min_value=int(pr.low) - 100000, max_value=int(pr.low) - 1)
    return st.decimals(
        min_value=pr.low - Decimal(1000),
        max_value=pr.low - Decimal("0.01"),
        allow_nan=False,
        allow_infinity=False,
        places=4,
    )


def above_range(pr: ParamRange) -> st.SearchStrategy[object]:
    """A numeric value strictly above ``pr.high``."""
    if pr.integer:
        return st.integers(min_value=int(pr.high) + 1, max_value=int(pr.high) + 100000)
    return st.decimals(
        min_value=pr.high + Decimal("0.01"),
        max_value=pr.high + Decimal(1000),
        allow_nan=False,
        allow_infinity=False,
        places=4,
    )


@st.composite
def valid_inputs(draw: st.DrawFn) -> dict[str, object]:
    """A fully valid candidate: every parameter numeric and in range."""
    return {name: draw(valid_value(name, pr)) for name, pr in PARAM_RANGES.items()}


@st.composite
def candidate(draw: st.DrawFn) -> tuple[dict[str, object], set[str]]:
    """A candidate mapping plus the set of parameters that make it invalid.

    With ~50% probability the candidate is fully valid (empty invalid set);
    otherwise at least one parameter is corrupted (out of range, non-numeric, or
    missing) so both the accept and reject branches of validation are exercised.
    """
    values: dict[str, object] = {
        name: draw(valid_value(name, pr)) for name, pr in PARAM_RANGES.items()
    }
    invalid: set[str] = set()

    if not draw(st.booleans()):
        to_corrupt = draw(
            st.lists(
                st.sampled_from(list(PARAM_RANGES)),
                min_size=1,
                unique=True,
            )
        )
        for name in to_corrupt:
            pr = PARAM_RANGES[name]
            mode = draw(
                st.sampled_from(["out_low", "out_high", "non_numeric", "missing"])
            )
            if mode == "out_low":
                values[name] = draw(below_range(pr))
            elif mode == "out_high":
                values[name] = draw(above_range(pr))
            elif mode == "non_numeric":
                values[name] = draw(st.sampled_from(NON_NUMERIC_VALUES))
            else:  # missing
                values.pop(name, None)
            invalid.add(name)

    return values, invalid


# ---------------------------------------------------------------------------
# Property 29 (subtask 5.2): validation accepts exactly in-range numeric values
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(candidate())
def test_property_29_validation_accepts_exactly_in_range_numeric(
    case: tuple[dict[str, object], set[str]],
) -> None:
    # Feature: dex-trading-agent, Property 29: Configuration validation accepts exactly in-range numeric values
    # Validates: Requirements 9.1, 9.2, 9.3, 9.7
    inputs, invalid = case
    active = ConfigManager.default_configuration()
    manager = ConfigManager(InMemoryConfigRepository(), active=active)

    result = manager.save(inputs)

    if not invalid:
        # Every parameter numeric and in range -> save succeeds and applies.
        assert result.is_ok()
        assert manager.active is result.value
        assert manager.active is not active
    else:
        # Rejected: active configuration retained unchanged and the offending
        # parameter is identified (and is one of the actually-invalid params).
        assert result.is_err()
        err = result.error
        assert isinstance(err, ConfigValidationError)
        assert err.parameter in invalid
        assert err.reason in (REASON_MISSING, REASON_NON_NUMERIC, REASON_OUT_OF_RANGE)
        assert manager.active is active


# ---------------------------------------------------------------------------
# Property 30 (subtask 5.3): persistence round-trip and latest-wins
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(st.lists(valid_inputs(), max_size=6))
def test_property_30_persistence_round_trip_and_latest_wins(
    sequence: list[dict[str, object]],
) -> None:
    # Feature: dex-trading-agent, Property 30: Configuration persistence round-trip and latest-wins
    # Validates: Requirements 9.4, 9.5
    repo = InMemoryConfigRepository()
    writer = ConfigManager(repo)

    expected = ConfigManager.default_configuration()
    for inputs in sequence:
        result = writer.save(inputs)
        assert result.is_ok()
        expected = result.value  # most recently persisted wins

    # A fresh manager loading from the same repository observes the latest
    # persisted configuration (Req 9.5); with no saves it observes defaults.
    reader = ConfigManager(repo)
    loaded = reader.load_at_startup()
    assert loaded.is_ok()
    assert loaded.value == expected
    assert reader.active == expected


# ---------------------------------------------------------------------------
# Property 31 (subtask 5.4): documented defaults fall within allowed ranges
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(st.sampled_from(list(PARAM_RANGES)))
def test_property_31_defaults_within_allowed_ranges(name: str) -> None:
    # Feature: dex-trading-agent, Property 31: Documented defaults fall within their allowed ranges
    # Validates: Requirements 9.6
    pr = PARAM_RANGES[name]
    assert name in DEFAULTS, f"no documented default for {name}"
    default_value = Decimal(DEFAULTS[name])  # type: ignore[arg-type]
    assert pr.contains(default_value), (
        f"default {default_value} for '{name}' outside [{pr.low}, {pr.high}]"
    )


def test_default_configuration_builds_and_is_in_range() -> None:
    """The default Configuration is constructible and every numeric field is in
    range (Req 9.6), and the build is deterministic."""
    config = ConfigManager.default_configuration()
    assert isinstance(config, Configuration)
    assert config == ConfigManager.default_configuration()
    field_values = {
        "refresh_interval_s": config.refresh_interval_s,
        "signal_interval_s": config.signal_interval_s,
        "discovery_scan_interval_s": config.discovery_scan_interval_s,
        "measurement_period_s": config.measurement_period_s,
        "bot_pct_threshold": config.bot_pct_threshold,
        "holder_conc_threshold": config.holder_conc_threshold,
        "rugpull_threshold": config.rugpull_threshold,
        "dump_threshold": config.dump_threshold,
        "entry_threshold": config.entry_threshold,
        "slippage_tolerance": config.slippage_tolerance,
        "confirmation_timeout_s": config.confirmation_timeout_s,
        "exit_alert_retries": config.exit_alert_retries,
        "retention_days": config.retention_days,
    }
    for name, value in field_values.items():
        assert PARAM_RANGES[name].contains(Decimal(value))


# ---------------------------------------------------------------------------
# Subtask 5.5: persistence-failure indication (Req 9.7)
# ---------------------------------------------------------------------------


class FailingConfigRepository(ConfigRepository):
    """A ConfigRepository whose ``save`` always raises (simulates IO failure)."""

    def save(self, configuration: Configuration) -> Configuration:
        raise RuntimeError("disk unavailable")

    def latest(self) -> Result[Configuration]:
        return Err(RuntimeError("disk unavailable"))  # type: ignore[arg-type]


def _valid_input() -> dict[str, object]:
    return {name: DEFAULTS[name] for name in PARAM_RANGES}


def test_persistence_failure_retains_active_and_surfaces_indication() -> None:
    """Req 9.7: when persistence fails the active config is retained, the manager
    continues operating, and a persistence-failure indication is surfaced."""
    active = ConfigManager.default_configuration()
    manager = ConfigManager(FailingConfigRepository(), active=active)
    assert manager.persistence_healthy is True

    result = manager.save(_valid_input())

    assert result.is_err()
    assert isinstance(result.error, ConfigPersistenceError)
    # Active configuration retained unchanged.
    assert manager.active is active
    # Persistence-failure indication surfaced; manager keeps operating.
    assert manager.persistence_healthy is False


def test_successful_save_clears_persistence_indication_and_applies() -> None:
    """A valid save against a healthy repo persists, applies, and reports healthy."""
    repo = InMemoryConfigRepository()
    manager = ConfigManager(repo)

    result = manager.save(_valid_input())

    assert isinstance(result, Ok)
    assert manager.persistence_healthy is True
    assert manager.active == result.value
    assert repo.latest().value == result.value


def test_validation_identifies_out_of_range_with_allowed_range() -> None:
    """Req 9.2: out-of-range rejection identifies the parameter and its range."""
    repo = InMemoryConfigRepository()
    active = ConfigManager.default_configuration()
    manager = ConfigManager(repo, active=active)

    bad = _valid_input()
    bad["refresh_interval_s"] = 4  # below [5, 300]
    result = manager.save(bad)

    assert isinstance(result, Err)
    err = result.error
    assert isinstance(err, ConfigValidationError)
    assert err.parameter == "refresh_interval_s"
    assert err.reason == REASON_OUT_OF_RANGE
    assert err.allowed_low == Decimal(5)
    assert err.allowed_high == Decimal(300)
    assert "refresh_interval_s" in err.message
    assert manager.active is active


def test_validation_identifies_non_numeric_and_missing() -> None:
    """Req 9.3: non-numeric and missing values are rejected by parameter name."""
    repo = InMemoryConfigRepository()
    manager = ConfigManager(repo, active=ConfigManager.default_configuration())

    non_numeric = _valid_input()
    non_numeric["slippage_tolerance"] = "lots"
    r1 = manager.save(non_numeric)
    assert isinstance(r1, Err)
    assert r1.error.parameter == "slippage_tolerance"
    assert r1.error.reason == REASON_NON_NUMERIC

    missing = _valid_input()
    del missing["entry_threshold"]
    r2 = manager.save(missing)
    assert isinstance(r2, Err)
    assert r2.error.parameter == "entry_threshold"
    assert r2.error.reason == REASON_MISSING


def test_load_at_startup_returns_defaults_when_empty() -> None:
    """Req 9.6: with no persisted configuration, startup load returns defaults."""
    manager = ConfigManager(InMemoryConfigRepository())
    loaded = manager.load_at_startup()
    assert isinstance(loaded, Ok)
    assert loaded.value == ConfigManager.default_configuration()
