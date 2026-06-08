"""DEX Trading Agent.

Top-level package. Sub-packages:

* ``models``       - data models and enums
* ``providers``    - external provider interfaces, fakes, and adapters
* ``repositories`` - persistence abstractions and in-memory implementations
* ``analysis``     - Security_Inspector, Backend_Analyzer, Metrics_Tracker
* ``decision``     - Signal_Engine, Risk_Manager
* ``execution``    - Trade_Executor, Authorization_Manager
* ``control``      - Monitoring Orchestrator, Data_Ingestor
* ``notify``       - Notifier and notification channels
* ``config``       - Config_Manager
* ``audit``        - Audit / persistence service

The shared :class:`~dex_agent.result.Result` type and the typed error taxonomy
(:mod:`dex_agent.errors`) are used across all component boundaries.
"""

from __future__ import annotations

from dex_agent.errors import (
    AgentError,
    NotFound,
    ProviderError,
    TimedOut,
    Unverified,
)
from dex_agent.result import Err, Ok, Result, is_err, is_ok

__all__ = [
    "Result",
    "Ok",
    "Err",
    "is_ok",
    "is_err",
    "AgentError",
    "ProviderError",
    "TimedOut",
    "Unverified",
    "NotFound",
    # Runnable Agent assembly (Task 19.1)
    "Agent",
    "AgentSecrets",
    "AgentProviders",
    "AgentRepositories",
    "BootReport",
    "build_agent",
    "build_production_agent",
    "default_risk_profile",
]


def __getattr__(name: str):
    """Lazily expose the Agent assembly to avoid import cycles at package load.

    The :mod:`dex_agent.agent` module imports from many sub-packages; exposing
    its public names through ``__getattr__`` (PEP 562) keeps ``import dex_agent``
    cheap while still allowing ``from dex_agent import build_agent``.
    """
    _agent_exports = {
        "Agent",
        "AgentSecrets",
        "AgentProviders",
        "AgentRepositories",
        "BootReport",
        "build_agent",
        "build_production_agent",
        "default_risk_profile",
    }
    if name in _agent_exports:
        from dex_agent import agent as _agent_module

        return getattr(_agent_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
