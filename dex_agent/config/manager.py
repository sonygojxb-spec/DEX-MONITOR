"""Config_Manager: parameter validation, defaults, persistence, startup load.

Design reference: "Config_Manager" (Requirements 9.1-9.7). The manager:

* validates that every configurable parameter is **numeric** and within its
  documented inclusive range (``PARAM_RANGES``) - rejecting non-numeric/missing
  (Req 9.3) and out-of-range (Req 9.2) inputs while **retaining the active
  configuration** and identifying the offending parameter;
* persists a valid configuration and makes it the active one (Req 9.4);
* loads the most recently persisted configuration at startup (Req 9.5), falling
  back to documented ``DEFAULTS`` when none exists (Req 9.6); and
* tolerates persistence failure by keeping the active configuration, continuing
  to operate, and surfacing a persistence-failure indication (Req 9.7).

Outcomes are reported with the shared :class:`~dex_agent.result.Result` type
(Task 1). Validation/persistence failures are carried as typed errors that
subclass :class:`~dex_agent.errors.AgentError` (the Task 1 error base) so the
offending parameter and allowed range travel with the ``Err``.

``stop_loss_pct`` appears in the design's conceptual range table but is a
:class:`~dex_agent.models.RiskProfile` parameter (governed by the Risk_Manager),
not a :class:`~dex_agent.models.Configuration` field; it is therefore not part
of this manager's ``PARAM_RANGES``, which mirrors exactly the numeric parameters
the ``Configuration`` model carries so that ``save`` / ``load`` round-trip
consistently.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from dex_agent.errors import AgentError
from dex_agent.models import Configuration, TimeWindow, utc_now
from dex_agent.repositories.interfaces import ConfigRepository
from dex_agent.result import Err, Ok, Result

# ---------------------------------------------------------------------------
# Parameter ranges (design "Config_Manager" PARAM_RANGES)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParamRange:
    """An inclusive numeric range for a configurable parameter.

    ``integer`` records whether the parameter is integer-typed (intervals,
    timeouts, counts, retention days) or decimal-typed (percent thresholds,
    slippage). Range bounds are stored as :class:`~decimal.Decimal` so integer
    and decimal parameters share one comparison path.
    """

    low: Decimal
    high: Decimal
    integer: bool

    def contains(self, value: Decimal) -> bool:
        """True iff ``value`` lies within ``[low, high]`` inclusive."""
        return self.low <= value <= self.high


def _ints(low: int, high: int) -> ParamRange:
    return ParamRange(Decimal(low), Decimal(high), integer=True)


def _dec(low: str, high: str) -> ParamRange:
    return ParamRange(Decimal(low), Decimal(high), integer=False)


# Insertion order matters: validation reports the *first* offending parameter,
# so this mirrors the design's PARAM_RANGES listing order.
PARAM_RANGES: dict[str, ParamRange] = {
    "refresh_interval_s": _ints(5, 300),          # Data_Refresh_Interval
    "signal_interval_s": _ints(1, 300),           # Signal_Computation_Interval
    "discovery_scan_interval_s": _ints(30, 300),  # discovery scan cadence
    "measurement_period_s": _ints(60, 86400),     # single Measurement_Period
    "bot_pct_threshold": _dec("0", "100"),
    "holder_conc_threshold": _dec("0", "100"),
    "rugpull_threshold": _dec("0", "100"),
    "dump_threshold": _dec("0.1", "100"),
    "entry_threshold": _dec("0", "100"),
    "slippage_tolerance": _dec("0.01", "100"),
    "confirmation_timeout_s": _ints(10, 600),
    "exit_alert_retries": _ints(1, 10),
    "retention_days": _ints(30, 3650),
}

# ---------------------------------------------------------------------------
# Documented defaults (design "Config_Manager" DEFAULTS; Req 9.6)
# ---------------------------------------------------------------------------
#
# Every numeric default below lies within its PARAM_RANGES entry (verified by
# Property 31). Defaults that the Configuration model already documents
# (refresh_interval_s, signal_interval_s, confirmation_timeout_s,
# exit_alert_retries, retention_days, automated_trading_enabled) are repeated
# here so the documented default set is complete and self-contained.

DEFAULTS: dict[str, object] = {
    "refresh_interval_s": 30,
    "signal_interval_s": 15,
    "discovery_scan_interval_s": 60,
    "measurement_period_s": 3600,
    "bot_pct_threshold": Decimal("50"),
    "holder_conc_threshold": Decimal("50"),
    "rugpull_threshold": Decimal("50"),
    "dump_threshold": Decimal("50"),
    "entry_threshold": Decimal("50"),
    "slippage_tolerance": Decimal("1"),
    "confirmation_timeout_s": 60,
    "exit_alert_retries": 3,
    "retention_days": 30,
    # Non-numeric (not range-validated) configuration fields.
    "automated_trading_enabled": False,
    "quiet_hours": None,
}

# Reasons a parameter can be rejected (used by ConfigValidationError).
REASON_MISSING = "missing"
REASON_NON_NUMERIC = "non_numeric"
REASON_OUT_OF_RANGE = "out_of_range"


@dataclass(frozen=True)
class ConfigValidationError(AgentError):
    """A configuration parameter was missing, non-numeric, or out of range.

    Carries the offending ``parameter`` and the ``reason`` so callers can surface
    a message identifying the parameter and (for out-of-range) its allowed range
    (Req 9.2, 9.3).
    """

    parameter: str
    reason: str
    allowed_low: Decimal | None = None
    allowed_high: Decimal | None = None

    @property
    def message(self) -> str:
        if self.reason == REASON_OUT_OF_RANGE:
            return (
                f"parameter '{self.parameter}' is out of range; "
                f"allowed range is [{self.allowed_low}, {self.allowed_high}]"
            )
        if self.reason == REASON_NON_NUMERIC:
            return f"parameter '{self.parameter}' must be a numeric value"
        return f"parameter '{self.parameter}' is required and was missing"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"ConfigValidationError({self.message})"


@dataclass(frozen=True)
class ConfigPersistenceError(AgentError):
    """Persisting a valid configuration failed (Req 9.7).

    The active configuration is retained and the agent continues operating; this
    error is the surfaced persistence-failure indication.
    """

    detail: str = ""

    @property
    def message(self) -> str:
        base = "failed to persist configuration"
        return f"{base}: {self.detail}" if self.detail else base

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"ConfigPersistenceError({self.message})"


def _coerce_numeric(value: object, prange: ParamRange) -> Decimal | None:
    """Return ``value`` as a :class:`Decimal` if it is a valid numeric for
    ``prange``, else ``None``.

    ``bool`` is rejected (it is not a meaningful numeric configuration value even
    though Python treats it as an ``int``). Integer-typed parameters accept only
    ``int``; decimal-typed parameters accept ``int``, ``float`` (via its string
    form to avoid binary-float drift), or ``Decimal``.
    """
    if isinstance(value, bool):
        return None
    if prange.integer:
        if not isinstance(value, int):
            return None
        return Decimal(value)
    # decimal-typed parameter
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return None


class ConfigManager:
    """Validates, persists, and loads the agent :class:`Configuration`.

    The repository is injected (design "Conventions"): any
    :class:`~dex_agent.repositories.interfaces.ConfigRepository` works, and tests
    use the in-memory implementation. The manager holds the *active*
    configuration in memory; only a successful ``save`` or ``load_at_startup``
    changes it.
    """

    PARAM_RANGES = PARAM_RANGES
    DEFAULTS = DEFAULTS

    def __init__(
        self,
        repo: ConfigRepository,
        *,
        active: Configuration | None = None,
    ) -> None:
        self._repo = repo
        self._active = active
        self._persistence_healthy = True

    # -- introspection -----------------------------------------------------

    @property
    def active(self) -> Configuration | None:
        """The currently active configuration (``None`` before any load/save)."""
        return self._active

    @property
    def persistence_healthy(self) -> bool:
        """False after a persistence failure was surfaced (Req 9.7)."""
        return self._persistence_healthy

    @classmethod
    def default_configuration(cls) -> Configuration:
        """Build a :class:`Configuration` from the documented ``DEFAULTS`` (Req 9.6).

        Deterministic (no timestamp) so two builds compare equal.
        """
        return cls._build_configuration(DEFAULTS, DEFAULTS, saved_at=None)

    # -- save (Req 9.1-9.4, 9.7) ------------------------------------------

    def save(self, inputs: Mapping[str, object]) -> Result[Configuration]:
        """Validate and persist a candidate configuration.

        Returns ``Ok(config)`` when every parameter is numeric and in range and
        persistence succeeds; the new config becomes active (Req 9.4). Returns
        ``Err(ConfigValidationError)`` identifying the first offending parameter
        on a missing/non-numeric (Req 9.3) or out-of-range (Req 9.2) input, and
        ``Err(ConfigPersistenceError)`` on persistence failure (Req 9.7). On any
        ``Err`` the active configuration is retained unchanged.
        """
        validated: dict[str, object] = {}
        for name, prange in PARAM_RANGES.items():
            if name not in inputs or inputs[name] is None:
                return Err(ConfigValidationError(parameter=name, reason=REASON_MISSING))
            number = _coerce_numeric(inputs[name], prange)
            if number is None:
                return Err(
                    ConfigValidationError(parameter=name, reason=REASON_NON_NUMERIC)
                )
            if not prange.contains(number):
                return Err(
                    ConfigValidationError(
                        parameter=name,
                        reason=REASON_OUT_OF_RANGE,
                        allowed_low=prange.low,
                        allowed_high=prange.high,
                    )
                )
            validated[name] = int(number) if prange.integer else number

        config = self._build_configuration(validated, inputs, saved_at=utc_now())

        try:
            self._repo.save(config)
        except Exception as exc:  # persistence failure -> retain active (Req 9.7)
            self._persistence_healthy = False
            return Err(ConfigPersistenceError(detail=str(exc)))

        self._active = config
        self._persistence_healthy = True
        return Ok(config)

    # -- startup load (Req 9.5, 9.6) --------------------------------------

    def load_at_startup(self) -> Result[Configuration]:
        """Load the most recently persisted configuration, or documented defaults.

        Returns ``Ok`` with the latest persisted configuration (Req 9.5) or, when
        none exists, a configuration built from ``DEFAULTS`` (Req 9.6). A
        persistence read failure is tolerated by falling back to defaults and
        marking persistence unhealthy (Req 9.7).
        """
        try:
            latest = self._repo.latest()
        except Exception:
            self._persistence_healthy = False
            config = self.default_configuration()
            self._active = config
            return Ok(config)

        if latest.is_ok():
            self._active = latest.value
            return Ok(latest.value)

        # No persisted configuration -> documented defaults.
        config = self.default_configuration()
        self._active = config
        return Ok(config)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _build_configuration(
        validated: Mapping[str, object],
        inputs: Mapping[str, object],
        *,
        saved_at: object | None,
    ) -> Configuration:
        """Assemble a :class:`Configuration` from validated numeric values plus
        the non-numeric fields (carried through from ``inputs``/``DEFAULTS``).
        """
        automated = inputs.get(
            "automated_trading_enabled", DEFAULTS["automated_trading_enabled"]
        )
        quiet_hours = inputs.get("quiet_hours", DEFAULTS["quiet_hours"])
        return Configuration(
            discovery_scan_interval_s=int(validated["discovery_scan_interval_s"]),
            measurement_period_s=int(validated["measurement_period_s"]),
            bot_pct_threshold=Decimal(validated["bot_pct_threshold"]),
            holder_conc_threshold=Decimal(validated["holder_conc_threshold"]),
            rugpull_threshold=Decimal(validated["rugpull_threshold"]),
            dump_threshold=Decimal(validated["dump_threshold"]),
            entry_threshold=Decimal(validated["entry_threshold"]),
            slippage_tolerance=Decimal(validated["slippage_tolerance"]),
            refresh_interval_s=int(validated["refresh_interval_s"]),
            signal_interval_s=int(validated["signal_interval_s"]),
            confirmation_timeout_s=int(validated["confirmation_timeout_s"]),
            exit_alert_retries=int(validated["exit_alert_retries"]),
            retention_days=int(validated["retention_days"]),
            automated_trading_enabled=bool(automated),
            quiet_hours=quiet_hours if isinstance(quiet_hours, TimeWindow) else None,
            saved_at=saved_at,  # type: ignore[arg-type]
        )


__all__ = [
    "ParamRange",
    "PARAM_RANGES",
    "DEFAULTS",
    "ConfigManager",
    "ConfigValidationError",
    "ConfigPersistenceError",
    "REASON_MISSING",
    "REASON_NON_NUMERIC",
    "REASON_OUT_OF_RANGE",
]
