"""Unit tests for the ``Severity`` ordering and ``max_by_ordinal`` helper.

Covers subtask 2.3: Severity ordering and ``max_by_ordinal`` edge cases (empty,
single, ties). Requirements 2.1, 2.7.
"""

from __future__ import annotations

import itertools

from dex_agent.models import SEVERITY_ORDER, Severity, max_by_ordinal


def test_severity_ordinals_match_design():
    assert Severity.NONE == 0
    assert Severity.LOW == 1
    assert Severity.MEDIUM == 2
    assert Severity.HIGH == 3
    assert Severity.CRITICAL == 4


def test_severity_is_totally_ordered_ascending():
    assert (
        Severity.NONE
        < Severity.LOW
        < Severity.MEDIUM
        < Severity.HIGH
        < Severity.CRITICAL
    )


def test_severity_order_tuple_is_sorted_by_ordinal():
    assert list(SEVERITY_ORDER) == sorted(SEVERITY_ORDER, key=lambda s: s.value)
    # index == ordinal
    for index, severity in enumerate(SEVERITY_ORDER):
        assert severity.value == index


def test_max_by_ordinal_empty_defaults_to_none():
    assert max_by_ordinal([]) is Severity.NONE
    assert max_by_ordinal(iter(())) is Severity.NONE


def test_max_by_ordinal_single_returns_that_value():
    for severity in SEVERITY_ORDER:
        assert max_by_ordinal([severity]) is severity


def test_max_by_ordinal_returns_highest():
    assert max_by_ordinal([Severity.LOW, Severity.CRITICAL, Severity.MEDIUM]) is (
        Severity.CRITICAL
    )
    assert max_by_ordinal([Severity.NONE, Severity.LOW]) is Severity.LOW


def test_max_by_ordinal_ties_return_the_tied_value():
    assert max_by_ordinal([Severity.HIGH, Severity.HIGH]) is Severity.HIGH
    assert (
        max_by_ordinal([Severity.MEDIUM, Severity.MEDIUM, Severity.MEDIUM])
        is Severity.MEDIUM
    )


def test_max_by_ordinal_is_order_independent():
    severities = [Severity.LOW, Severity.HIGH, Severity.MEDIUM]
    for permutation in itertools.permutations(severities):
        assert max_by_ordinal(list(permutation)) is Severity.HIGH


def test_max_by_ordinal_all_none():
    assert max_by_ordinal([Severity.NONE, Severity.NONE]) is Severity.NONE
