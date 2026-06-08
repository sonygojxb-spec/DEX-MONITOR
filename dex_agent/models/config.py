"""Configuration model.

Design reference: "Data Models" -> "Config". Covers :class:`TimeWindow` and
:class:`Configuration`. Parameter range/validation logic and the full
``DEFAULTS`` table live in the Config_Manager (Task 5); this module defines the
data shape only. The few fields the design documents a default for carry that
default here; the remaining parameters are required so the model never invents
an undocumented domain value.

The interval fields are deliberately distinct (design note "DISTINCT from
refresh_interval_s"):

* ``refresh_interval_s``        - Data_Refresh_Interval ``[5, 300]``, default 30.
* ``signal_interval_s``         - Signal_Computation_Interval ``[1, 300]``, default 15.
* ``discovery_scan_interval_s`` - discovery scan cadence ``[30, 300]``.
* ``measurement_period_s``      - single Measurement_Period ``[60, 86400]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal


@dataclass(frozen=True)
class TimeWindow:
    """A wall-clock window (e.g. quiet hours) bounded by start/end times."""

    start: time
    end: time


@dataclass(frozen=True)
class Configuration:
    """User-configurable parameters governing monitoring and trading.

    Fields with a design-documented default carry it (``refresh_interval_s``,
    ``signal_interval_s``, ``confirmation_timeout_s``, ``exit_alert_retries``,
    ``retention_days``, ``automated_trading_enabled``). The remaining
    parameters have a documented *range* but no documented default, so they are
    required here; the Config_Manager supplies concrete defaults (Task 5). Range
    validation and rejection of non-numeric/out-of-range inputs are the
    Config_Manager's responsibility (Requirement 9.x).
    """

    # --- required: documented range, no documented default ---
    discovery_scan_interval_s: int          # [30, 300]
    measurement_period_s: int               # [60, 86400]
    bot_pct_threshold: Decimal              # [0, 100]
    holder_conc_threshold: Decimal          # [0, 100]
    rugpull_threshold: Decimal              # [0, 100]
    dump_threshold: Decimal                 # [0.1, 100]
    entry_threshold: Decimal                # [0, 100]
    slippage_tolerance: Decimal             # [0.01, 100]

    # --- documented defaults ---
    refresh_interval_s: int = 30            # [5, 300], default 30
    signal_interval_s: int = 15             # [1, 300], default 15
    confirmation_timeout_s: int = 60        # [10, 600], default 60
    exit_alert_retries: int = 3             # [1, 10], default 3
    retention_days: int = 30                # [30, 3650], default 30
    automated_trading_enabled: bool = False  # default false
    quiet_hours: TimeWindow | None = None
    saved_at: datetime | None = None


__all__ = [
    "TimeWindow",
    "Configuration",
]
