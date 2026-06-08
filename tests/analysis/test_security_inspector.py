"""Tests for the Security_Inspector (Task 7).

Covers the design's Correctness Properties for security inspection:

* Property 1 - severity rating is always a member of the ordered set
  (subtask 7.3, Req 2.1);
* Property 2 - overall severity equals the maximum contributing severity
  (subtask 7.4, Req 2.5, 2.7, 2.4);
* Property 3 - unverified or unretrievable contracts rate High
  (subtask 7.5, Req 2.9);

plus unit tests for issue-record completeness and timestamp formatting
(subtask 7.6, Req 2.6, 2.8) and the Solana security-semantics mapping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.analysis import ISSUE_SEVERITY, SecurityInspector
from dex_agent.errors import ProviderError, TimedOut, Unverified
from dex_agent.models import (
    SEVERITY_ORDER,
    Network,
    SecurityIssueType,
    Severity,
    Token,
    max_by_ordinal,
)
from dex_agent.providers.fakes import FakeContractInspectorProvider
from dex_agent.providers.interfaces import SecurityInputs
from dex_agent.repositories import InMemorySecurityEvalRepository

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

ADDRESSES = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12
)
OPTIONAL_AUTHORITY = st.one_of(st.none(), st.text(min_size=1, max_size=8))


def make_token(address: str) -> Token:
    return Token(
        address=address,
        network=Network.SOLANA,
        symbol="TKN",
        name="Token",
        total_supply=Decimal(1_000_000),
    )


@st.composite
def security_inputs(draw: st.DrawFn, address: str) -> SecurityInputs:
    """Arbitrary security inputs spanning every authority/signal combination."""
    return SecurityInputs(
        token_address=address,
        mint_authority=draw(OPTIONAL_AUTHORITY),
        freeze_authority=draw(OPTIONAL_AUTHORITY),
        has_transfer_fee_extension=draw(st.booleans()),
        is_token_2022=draw(st.booleans()),
        authority_source="solana-rpc",
        update_authority=draw(OPTIONAL_AUTHORITY),
        is_mutable=draw(st.one_of(st.none(), st.booleans())),
        is_verified=draw(st.one_of(st.none(), st.booleans())),
        possible_spam=draw(st.one_of(st.none(), st.booleans())),
        score=draw(
            st.one_of(
                st.none(),
                st.integers(min_value=0, max_value=100).map(Decimal),
            )
        ),
    )


def build_inspector(
    inputs: SecurityInputs | None = None,
    error: Exception | None = None,
    *,
    address: str,
    repository: InMemorySecurityEvalRepository | None = None,
    adverse_score_below: Decimal | None = None,
) -> SecurityInspector:
    """Wire a SecurityInspector over a fake provider scripted with ``inputs``/``error``."""
    provider = FakeContractInspectorProvider()
    if error is not None:
        provider.fail_always("inspect_token", error)
    if inputs is not None:
        provider.set_inputs(inputs)
    return SecurityInspector(
        provider,
        repository,
        adverse_score_below=adverse_score_below,
    )


# ---------------------------------------------------------------------------
# Property 1 (subtask 7.3): severity rating is always a member of the set
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(data=st.data(), address=ADDRESSES)
def test_property_1_rating_is_member_of_ordered_set(
    data: st.DataObject, address: str
) -> None:
    # Feature: dex-trading-agent, Property 1: Severity rating is always a member of the ordered set
    # Validates: Requirements 2.1
    scenario = data.draw(st.sampled_from(["ok", "provider_error", "timeout", "unverified"]))
    if scenario == "ok":
        inspector = build_inspector(
            data.draw(security_inputs(address)), address=address
        )
    else:
        error = {
            "provider_error": ProviderError("boom", provider="fake"),
            "timeout": TimedOut("slow", timeout_s=30.0),
            "unverified": Unverified("no mint", subject=address),
        }[scenario]
        inspector = build_inspector(error=error, address=address)

    evaluation = inspector.evaluate(make_token(address))

    assert evaluation.rating in SEVERITY_ORDER
    assert isinstance(evaluation.rating, Severity)


# ---------------------------------------------------------------------------
# Property 2 (subtask 7.4): overall severity == max contributing severity
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(data=st.data(), address=ADDRESSES)
def test_property_2_overall_equals_max_contributing(
    data: st.DataObject, address: str
) -> None:
    # Feature: dex-trading-agent, Property 2: Overall severity equals the maximum contributing severity
    # Validates: Requirements 2.5, 2.7, 2.4
    inputs = data.draw(security_inputs(address))
    inspector = build_inspector(inputs, address=address)

    evaluation = inspector.evaluate(make_token(address))

    expected = max_by_ordinal(issue.severity for issue in evaluation.issues)
    assert evaluation.rating == expected
    # Empty issue set -> rating is None (lowest) (Req 2.7).
    if not evaluation.issues:
        assert evaluation.rating == Severity.NONE
    # An arbitrary transfer-disable privilege (active freeze authority) forces
    # Critical (Req 2.5, 2.4).
    if inputs.freeze_authority is not None:
        assert evaluation.rating == Severity.CRITICAL
        assert any(
            issue.type == SecurityIssueType.TRANSFER_DISABLE
            and issue.severity == Severity.CRITICAL
            for issue in evaluation.issues
        )


# ---------------------------------------------------------------------------
# Property 3 (subtask 7.5): unverified/unretrievable contracts rate High
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(data=st.data(), address=ADDRESSES)
def test_property_3_unverified_or_unretrievable_rate_high(
    data: st.DataObject, address: str
) -> None:
    # Feature: dex-trading-agent, Property 3: Unverified or unretrievable contracts rate High
    # Validates: Requirements 2.9
    scenario = data.draw(
        st.sampled_from(["provider_error", "timeout", "unverified", "possible_spam"])
    )
    if scenario == "possible_spam":
        # Retrievable but flagged as spam, with no Critical-forcing authority,
        # so the rating is exactly High (Req 2.9 (b)).
        inputs = SecurityInputs(
            token_address=address,
            mint_authority=data.draw(OPTIONAL_AUTHORITY),
            freeze_authority=None,
            has_transfer_fee_extension=data.draw(st.booleans()),
            update_authority=data.draw(OPTIONAL_AUTHORITY),
            possible_spam=True,
            authority_source="solana-rpc",
        )
        inspector = build_inspector(inputs, address=address)
    else:
        error = {
            "provider_error": ProviderError("unreachable", provider="fake"),
            "timeout": TimedOut("exceeded 30s", timeout_s=30.0),
            "unverified": Unverified("mint unparseable", subject=address),
        }[scenario]
        inspector = build_inspector(error=error, address=address)

    evaluation = inspector.evaluate(make_token(address))

    assert evaluation.rating == Severity.HIGH
    assert evaluation.unverified is True
    assert any(
        issue.type == SecurityIssueType.UNVERIFIED for issue in evaluation.issues
    )


# ---------------------------------------------------------------------------
# Subtask 7.6: issue-record completeness and timestamp formatting (Req 2.6, 2.8)
# ---------------------------------------------------------------------------


def test_detect_issues_records_all_four_types_with_fields() -> None:
    """Req 2.4/2.6: every detected issue records its type, description, severity."""
    address = "mintfreezefeeowner"
    inputs = SecurityInputs(
        token_address=address,
        mint_authority="MINT_AUTH",
        freeze_authority="FREEZE_AUTH",
        has_transfer_fee_extension=True,
        is_token_2022=True,
        update_authority="UPDATE_AUTH",
        authority_source="solana-rpc",
    )
    inspector = build_inspector(inputs, address=address)

    issues = inspector.detect_issues(inputs)

    by_type = {issue.type: issue for issue in issues}
    assert set(by_type) == {
        SecurityIssueType.MINTABLE,
        SecurityIssueType.TRANSFER_DISABLE,
        SecurityIssueType.FEE_MODIFIABLE,
        SecurityIssueType.OWNERSHIP_PRIVILEGE,
    }
    for issue in issues:
        assert issue.description  # non-empty description (Req 2.6)
        assert issue.severity == ISSUE_SEVERITY[issue.type] or (
            issue.type == SecurityIssueType.TRANSFER_DISABLE
            and issue.severity == Severity.CRITICAL
        )
    # The freeze authority is recorded as a Critical transfer-disable (Req 2.5).
    assert by_type[SecurityIssueType.TRANSFER_DISABLE].severity == Severity.CRITICAL
    assert "FREEZE_AUTH" in by_type[SecurityIssueType.TRANSFER_DISABLE].description


def test_clean_contract_has_no_issues_and_none_rating() -> None:
    """A renounced, clean mint yields no issues and a None rating (Req 2.7)."""
    address = "cleanmint"
    inputs = SecurityInputs(
        token_address=address,
        mint_authority=None,
        freeze_authority=None,
        has_transfer_fee_extension=False,
        update_authority=None,
        possible_spam=False,
        authority_source="solana-rpc",
    )
    inspector = build_inspector(inputs, address=address)

    evaluation = inspector.evaluate(make_token(address))

    assert evaluation.issues == ()
    assert evaluation.rating == Severity.NONE
    assert evaluation.unverified is False


def test_evaluation_timestamp_is_second_precision_utc() -> None:
    """Req 2.8: evaluations are stamped to second-level UTC precision."""
    address = "tsprecision"
    fixed = datetime(2025, 6, 1, 12, 30, 45, tzinfo=timezone.utc)
    inputs = SecurityInputs(token_address=address, authority_source="solana-rpc")
    provider = FakeContractInspectorProvider()
    provider.set_inputs(inputs)
    inspector = SecurityInspector(provider, clock=lambda: fixed)

    evaluation = inspector.evaluate(make_token(address))

    assert evaluation.evaluated_at == fixed
    assert evaluation.evaluated_at.tzinfo == timezone.utc
    assert evaluation.evaluated_at.microsecond == 0


def test_evaluation_is_persisted_when_repository_configured() -> None:
    """The evaluation is appended to the SecurityEval repository (Task 3 reuse)."""
    address = "persisted"
    repo = InMemorySecurityEvalRepository()
    inputs = SecurityInputs(
        token_address=address,
        freeze_authority="FREEZE",
        authority_source="solana-rpc",
    )
    inspector = build_inspector(inputs, address=address, repository=repo)

    evaluation = inspector.evaluate(make_token(address))

    latest = repo.latest(address)
    assert latest.is_ok()
    assert latest.value == evaluation
    assert latest.value.rating == Severity.CRITICAL


def test_both_authorities_active_marks_unverified() -> None:
    """Req 2.9 (c): both mint and freeze authorities active marks unverified.

    The rating remains the maximum contributing severity (Critical from the
    active freeze authority), with the unverified flag set true.
    """
    address = "bothauth"
    inputs = SecurityInputs(
        token_address=address,
        mint_authority="MINT",
        freeze_authority="FREEZE",
        authority_source="solana-rpc",
    )
    inspector = build_inspector(inputs, address=address)

    evaluation = inspector.evaluate(make_token(address))

    assert evaluation.unverified is True
    assert evaluation.rating == Severity.CRITICAL
    assert any(
        issue.type == SecurityIssueType.UNVERIFIED for issue in evaluation.issues
    )


def test_adverse_score_triggers_unverified_when_configured() -> None:
    """Req 2.9 (b): an adverse score below the configured threshold -> High/unverified."""
    address = "lowscore"
    inputs = SecurityInputs(
        token_address=address,
        score=Decimal(10),
        authority_source="solana-rpc",
    )
    inspector = build_inspector(
        inputs, address=address, adverse_score_below=Decimal(40)
    )

    evaluation = inspector.evaluate(make_token(address))

    assert evaluation.rating == Severity.HIGH
    assert evaluation.unverified is True


def test_on_state_change_re_evaluates_and_updates_rating() -> None:
    """Req 2.10: on_state_change re-evaluates and returns the updated rating."""
    address = "statechange"
    provider = FakeContractInspectorProvider()
    repo = InMemorySecurityEvalRepository()
    # Distinct second-precision timestamps so both evaluations persist.
    times = iter(
        [
            datetime(2025, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
        ]
    )
    # Initially clean -> None.
    provider.set_inputs(SecurityInputs(token_address=address, authority_source="rpc"))
    inspector = SecurityInspector(provider, repo, clock=lambda: next(times))
    token = make_token(address)

    first = inspector.evaluate(token)
    assert first.rating == Severity.NONE

    # Contract state changes: a freeze authority becomes active.
    provider.set_inputs(
        SecurityInputs(
            token_address=address,
            freeze_authority="FREEZE",
            authority_source="rpc",
        )
    )
    second = inspector.on_state_change(token)

    assert second.rating == Severity.CRITICAL
    assert repo.latest(address).value == second
    assert len(repo.history(address)) == 2
