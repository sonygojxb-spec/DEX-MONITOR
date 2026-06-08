"""Integration test 19.5: capacity smoke test for 200 concurrent loops.

Registers 200 pairs and asserts the active-pair registry stays responsive and
the 200-pair concurrency cap holds (Req 1.10).
"""

from __future__ import annotations

from dex_agent.control.orchestrator import CONCURRENCY_CAP
from dex_agent.errors import ConcurrencyLimitExceeded

from tests.integration.helpers import build_test_agent


def test_registry_holds_200_pairs_and_caps_the_201st():
    agent, _fakes, _clock = build_test_agent()
    agent.boot()

    # Admit exactly the cap (200) pairs; every admit under the cap succeeds.
    for i in range(CONCURRENCY_CAP):
        assert agent.orchestrator.add_pair(f"pair-{i}").is_ok()

    assert agent.orchestrator.active_count() == CONCURRENCY_CAP

    # The 201st pair is rejected without mutating the registry (Property 9).
    rejected = agent.orchestrator.add_pair("pair-200")
    assert rejected.is_err()
    assert isinstance(rejected.error, ConcurrencyLimitExceeded)
    assert agent.orchestrator.active_count() == CONCURRENCY_CAP

    # The registry stays responsive: membership queries are O(1) and accurate.
    assert agent.is_monitoring("pair-0") is True
    assert agent.is_monitoring("pair-199") is True
    assert agent.is_monitoring("pair-200") is False

    # Removing a pair frees exactly one slot, which can then be re-admitted.
    agent.remove_pair("pair-0")
    assert agent.orchestrator.active_count() == CONCURRENCY_CAP - 1
    assert agent.orchestrator.add_pair("pair-200").is_ok()
    assert agent.orchestrator.active_count() == CONCURRENCY_CAP
