"""Configuration layer: Config_Manager.

Re-exports the :class:`~dex_agent.config.manager.ConfigManager` together with
its parameter-range table, documented defaults, and typed validation/persistence
errors (design "Config_Manager", Requirements 9.1-9.7).
"""

from __future__ import annotations

from dex_agent.config.manager import (
    DEFAULTS,
    PARAM_RANGES,
    REASON_MISSING,
    REASON_NON_NUMERIC,
    REASON_OUT_OF_RANGE,
    ConfigManager,
    ConfigPersistenceError,
    ConfigValidationError,
    ParamRange,
)

__all__ = [
    "ConfigManager",
    "ParamRange",
    "PARAM_RANGES",
    "DEFAULTS",
    "ConfigValidationError",
    "ConfigPersistenceError",
    "REASON_MISSING",
    "REASON_NON_NUMERIC",
    "REASON_OUT_OF_RANGE",
]
