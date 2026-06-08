"""Security_Inspector: contract security inspection and severity assignment.

Design references: "Security_Inspector" and "Solana Security Semantics
(Security_Inspector)". Maps to Requirements 2.1, 2.4-2.10.

The inspector evaluates a Token's contract for security issues and assigns a
:class:`~dex_agent.models.Severity` rating equal to the **maximum** contributing
issue severity (Req 2.7), records each detected issue (Req 2.6), and stamps the
evaluation with second-level UTC precision (Req 2.8). It depends only on the
:class:`~dex_agent.providers.interfaces.ContractInspectorProvider` interface (so
the authority source and supporting risk signals are injectable / fakeable) and,
optionally, on a :class:`~dex_agent.repositories.interfaces.SecurityEvalRepository`
to persist results.

Solana Security Semantics (design "Solana Security Semantics"). Requirements
2.4-2.9 are written in EVM-neutral terms; on Solana they concretize to fields on
the SPL mint (authoritative, from Solana RPC ``getAccountInfo`` surfaced through
:class:`~dex_agent.providers.interfaces.SecurityInputs`) plus supporting risk
signals from Moralis token metadata / Token Score (GoPlus optional fallback):

==========================  ====================================  =======================
Requirement concept         Authoritative Solana field            ``SecurityIssueType``
==========================  ====================================  =======================
mintable supply             active (non-null) ``mint_authority``   ``MINTABLE``
transfer-disabling function active (non-null) ``freeze_authority``  ``TRANSFER_DISABLE``
modifiable fees             Token-2022 transfer-fee extension       ``FEE_MODIFIABLE``
ownership privilege         unrenounced ``update_authority``        ``OWNERSHIP_PRIVILEGE``
==========================  ====================================  =======================

An active ``freeze_authority`` is the Solana realization of an *arbitrary
transfer-disable* privilege and forces a ``CRITICAL`` rating (Req 2.5).

Req 2.9 (High / unverified) is remapped: the inspector raises ``rating = High``
with ``unverified = True`` (an ``UNVERIFIED`` issue) when **any** of:

* (a) the SPL mint is **unanalyzable / unavailable** - ``inspect_token`` returns
  a typed error (provider error, timeout, or ``Unverified``); OR
* (b) Moralis flags the token as ``possible_spam`` or returns an adverse
  ``score``; OR
* (c) **both** ``mint_authority`` and ``freeze_authority`` are active and
  unrenounced.

Because the rating is always the maximum contributing severity, an ``UNVERIFIED``
issue contributes a ``High`` floor while any co-occurring ``CRITICAL`` issue
(e.g. an active freeze authority) still wins - Correctness Properties 1-4 are
unchanged.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Callable

from dex_agent.models import (
    Network,
    SecurityEvaluation,
    SecurityIssue,
    SecurityIssueType,
    Severity,
    Token,
    max_by_ordinal,
    utc_now_seconds,
)
from dex_agent.providers.interfaces import (
    ContractInspectorProvider,
    SecurityInputs,
)
from dex_agent.repositories.interfaces import SecurityEvalRepository

# ---------------------------------------------------------------------------
# Issue-type -> contributing severity mapping
# ---------------------------------------------------------------------------
#
# The design pins only the Critical trigger (an arbitrary transfer-disable
# privilege, Req 2.5). The remaining severities below are this component's
# documented contributing-severity choices; the Correctness Properties depend
# only on (1) the rating being the maximum contributing severity, (2) an active
# freeze authority producing Critical, and (3) the unverified path producing a
# High floor - not on the specific non-Critical values.
ISSUE_SEVERITY: dict[SecurityIssueType, Severity] = {
    SecurityIssueType.MINTABLE: Severity.HIGH,
    SecurityIssueType.TRANSFER_DISABLE: Severity.CRITICAL,  # Req 2.5 (forced)
    SecurityIssueType.FEE_MODIFIABLE: Severity.MEDIUM,
    SecurityIssueType.OWNERSHIP_PRIVILEGE: Severity.MEDIUM,
    SecurityIssueType.UNVERIFIED: Severity.HIGH,  # Req 2.9
}


class SecurityInspector:
    """Evaluates a Token contract and assigns its Severity_Rating.

    Args:
        inspector: The :class:`ContractInspectorProvider` supplying the
            (authoritative + supporting) security risk inputs for a token.
        repository: Optional :class:`SecurityEvalRepository` to persist each
            evaluation result (Task 3). When ``None`` results are not persisted.
        adverse_score_below: When set, a non-null ``SecurityInputs.score``
            strictly below this threshold is treated as an *adverse score* and
            triggers the unverified path (Req 2.9 (b)). ``None`` disables the
            score-based trigger (``possible_spam`` always triggers it).
        clock: Callable returning the current second-precision UTC timestamp
            used to stamp evaluations (Req 2.8); injectable for tests.
    """

    def __init__(
        self,
        inspector: ContractInspectorProvider,
        repository: SecurityEvalRepository | None = None,
        *,
        adverse_score_below: Decimal | None = None,
        clock: Callable[[], datetime] = utc_now_seconds,
    ) -> None:
        self._inspector = inspector
        self._repository = repository
        self._adverse_score_below = adverse_score_below
        self._clock = clock

    # ------------------------------------------------------------------
    # Issue detection (Req 2.4, 2.5)
    # ------------------------------------------------------------------
    def detect_issues(self, inputs: SecurityInputs) -> tuple[SecurityIssue, ...]:
        """Detect contract security issues from the security inputs (Req 2.4).

        Returns the detected issues, each carrying its type, a description, and
        its contributing severity (Req 2.6). An active freeze authority yields a
        ``TRANSFER_DISABLE`` issue with ``CRITICAL`` severity (Req 2.5).
        """
        issues: list[SecurityIssue] = []

        if inputs.mint_authority is not None:
            issues.append(
                SecurityIssue(
                    type=SecurityIssueType.MINTABLE,
                    description=(
                        "Active SPL mint authority "
                        f"({inputs.mint_authority}) can mint additional supply."
                    ),
                    severity=ISSUE_SEVERITY[SecurityIssueType.MINTABLE],
                )
            )

        if inputs.freeze_authority is not None:
            # The Solana realization of an "arbitrary transfer-disable" privilege
            # (Req 2.5): an active freeze authority can freeze any token account
            # at will, so the issue is forced to CRITICAL.
            issues.append(
                SecurityIssue(
                    type=SecurityIssueType.TRANSFER_DISABLE,
                    description=(
                        "Active SPL freeze authority "
                        f"({inputs.freeze_authority}) can disable token transfers "
                        "at will (arbitrary transfer-disable privilege)."
                    ),
                    severity=Severity.CRITICAL,
                )
            )

        if inputs.has_transfer_fee_extension:
            issues.append(
                SecurityIssue(
                    type=SecurityIssueType.FEE_MODIFIABLE,
                    description=(
                        "Token-2022 transfer-fee extension present; transaction "
                        "fees can be modified."
                    ),
                    severity=ISSUE_SEVERITY[SecurityIssueType.FEE_MODIFIABLE],
                )
            )

        if inputs.update_authority is not None:
            issues.append(
                SecurityIssue(
                    type=SecurityIssueType.OWNERSHIP_PRIVILEGE,
                    description=(
                        "Unrenounced metadata update authority "
                        f"({inputs.update_authority}) retains ownership privilege."
                    ),
                    severity=ISSUE_SEVERITY[SecurityIssueType.OWNERSHIP_PRIVILEGE],
                )
            )

        return tuple(issues)

    # ------------------------------------------------------------------
    # Evaluation (Req 2.6, 2.7, 2.8, 2.9)
    # ------------------------------------------------------------------
    def evaluate(self, token: Token) -> SecurityEvaluation:
        """Evaluate ``token`` and return its :class:`SecurityEvaluation`.

        The overall rating is the maximum contributing issue severity (Req 2.7,
        default :attr:`Severity.NONE` when no issue is detected). On an
        unretrievable / unanalyzable contract or an adverse risk signal the
        evaluation is High and ``unverified`` (Req 2.9). The result is stamped
        with second-level UTC precision (Req 2.8) and persisted when a
        repository is configured.
        """
        timestamp = self._clock()
        result = self._inspector.inspect_token(token.address, token.network)

        if result.is_err():
            # Req 2.9 (a): the SPL mint is unanalyzable / unavailable.
            evaluation = SecurityEvaluation(
                token_address=token.address,
                rating=Severity.HIGH,
                unverified=True,
                evaluated_at=timestamp,
                issues=(
                    SecurityIssue(
                        type=SecurityIssueType.UNVERIFIED,
                        description=(
                            "Contract/SPL mint could not be retrieved or analyzed "
                            f"within the time limit: {result.error}"
                        ),
                        severity=ISSUE_SEVERITY[SecurityIssueType.UNVERIFIED],
                    ),
                ),
            )
            return self._record(evaluation)

        inputs = result.value
        issues = list(self.detect_issues(inputs))

        unverified_reason = self._unverified_reason(inputs)
        unverified = unverified_reason is not None
        if unverified:
            issues.append(
                SecurityIssue(
                    type=SecurityIssueType.UNVERIFIED,
                    description=unverified_reason,
                    severity=ISSUE_SEVERITY[SecurityIssueType.UNVERIFIED],
                )
            )

        rating = max_by_ordinal(issue.severity for issue in issues)  # Req 2.7

        evaluation = SecurityEvaluation(
            token_address=token.address,
            rating=rating,
            unverified=unverified,
            evaluated_at=timestamp,
            issues=tuple(issues),
        )
        return self._record(evaluation)

    def on_state_change(self, token: Token) -> SecurityEvaluation:
        """Re-evaluate ``token`` after a detected contract state change (Req 2.10).

        Returns the fresh evaluation (with the updated rating), which is also
        persisted when a repository is configured.
        """
        return self.evaluate(token)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _unverified_reason(self, inputs: SecurityInputs) -> str | None:
        """Return the Req 2.9 unverified reason for retrievable inputs, else None.

        Triggers (design Req 2.9 remap): (b) ``possible_spam`` or an adverse
        ``score``; (c) both ``mint_authority`` and ``freeze_authority`` active
        and unrenounced. Trigger (a) (unretrievable) is handled in
        :meth:`evaluate` on the error path.
        """
        if inputs.possible_spam:
            return "Provider flagged the token as possible spam."
        if (
            self._adverse_score_below is not None
            and inputs.score is not None
            and inputs.score < self._adverse_score_below
        ):
            return (
                f"Adverse risk score {inputs.score} is below the "
                f"{self._adverse_score_below} threshold."
            )
        if inputs.mint_authority is not None and inputs.freeze_authority is not None:
            return (
                "Both mint and freeze authorities are active and unrenounced; "
                "security posture could not be established."
            )
        return None

    def _record(self, evaluation: SecurityEvaluation) -> SecurityEvaluation:
        """Persist ``evaluation`` when a repository is configured, then return it."""
        if self._repository is not None:
            self._repository.append(evaluation)
        return evaluation


__all__ = [
    "SecurityInspector",
    "ISSUE_SEVERITY",
]
