"""Authorization_Manager: wallet authorization, the trading gate, revocation.

Design reference: "Authorization_Manager" (Requirements 11.1-11.6). The manager:

* verifies a connected wallet's authorization **within a 5-second bound** before
  enabling trade execution (Req 11.1); on success it enables trading and records
  an :class:`~dex_agent.models.AuthStatus` ``ENABLED`` status change;
* on verification failure **or** a timeout it does **not** enable trading, stays
  in monitoring-only mode, surfaces an error indication to the caller, and
  records a ``FAILED`` status change (Req 11.2);
* gates trading via :meth:`trading_enabled`, which defaults to ``False`` until an
  authorized wallet is connected (Req 11.3);
* processes revocation by disabling trade execution within the bound while
  retaining monitoring functions, recording a ``REVOKED`` status change
  (Req 11.4, 11.5); and
* records **every** trading-authorization status change with a timestamp
  (Req 11.6) through the injected
  :class:`~dex_agent.repositories.interfaces.AuthorizationRepository`.

Design conventions (Task 1 / "Conventions"):

* The wallet-verification capability is an **injected seam** - a ``verifier``
  callable returning a :class:`~dex_agent.result.Result`. Property/unit tests
  replace it with an in-memory fake so no real network/chain calls occur.
* The 5-second bound is enforced against an **injected monotonic clock**; no real
  sleeps are performed. A verifier that signals it took too long (by returning
  ``Err(TimedOut)``) or whose measured elapsed time exceeds the bound is treated
  as a timeout (Req 11.2).
* Timestamps come from an **injected wall clock** (defaulting to UTC now) so
  recorded status changes are deterministic in tests.
* Outcomes are reported with the shared :class:`~dex_agent.result.Result` type;
  no failure path performs partial state mutation beyond recording the status
  change that actually occurred.
"""

from __future__ import annotations

import time as _time
from datetime import datetime
from typing import Any, Callable

from dex_agent.errors import AgentError, ProviderError, TimedOut, Unverified
from dex_agent.models import AuthorizationRecord, AuthStatus, utc_now
from dex_agent.repositories.interfaces import AuthorizationRepository
from dex_agent.result import Err, Ok, Result

# A verifier is the injected wallet-authorization capability. It receives the
# wallet identifier and returns a Result: Ok on a verified authorization, or an
# Err carrying a typed error (e.g. TimedOut / ProviderError / Unverified).
Verifier = Callable[[str], "Result[Any]"]

# Wall clock producing the timestamp recorded on each status change (Req 11.6).
WallClock = Callable[[], datetime]

# Monotonic clock (seconds) used to measure the verification elapsed time
# against the 5s bound. Injectable so tests advance time without sleeping.
MonotonicClock = Callable[[], float]


class AuthorizationManager:
    """Verifies wallet authorization, gates trading, and processes revocation.

    The :class:`AuthorizationRepository` and the ``verifier`` seam are injected
    (design "Conventions"). The manager holds the trading gate and the currently
    authorized wallet in memory; only :meth:`connect_wallet` and :meth:`revoke`
    change that in-memory state, and each transition is recorded.

    Monitoring functions are never disabled by this manager: it controls *only*
    the trading gate. :attr:`monitoring_active` is therefore always ``True``,
    which is how Req 11.5 (monitoring retained after revoke) is upheld.
    """

    #: The wallet-authorization verification time bound, in seconds (Req 11.1).
    VERIFY_BOUND_S: float = 5.0

    def __init__(
        self,
        repo: AuthorizationRepository,
        verifier: Verifier,
        *,
        clock: WallClock = utc_now,
        monotonic: MonotonicClock = _time.monotonic,
        bound_s: float = VERIFY_BOUND_S,
    ) -> None:
        self._repo = repo
        self._verify = verifier
        self._clock = clock
        self._monotonic = monotonic
        self._bound_s = float(bound_s)
        self._trading_enabled = False
        self._wallet_id: str | None = None

    # -- introspection / gate ---------------------------------------------

    def trading_enabled(self) -> bool:
        """The trading gate (Req 11.3).

        Defaults to ``False`` and becomes ``True`` only after an authorized
        wallet has been connected and verified within the bound. Revocation
        returns it to ``False``.
        """
        return self._trading_enabled

    @property
    def authorized_wallet(self) -> str | None:
        """The currently authorized wallet id, or ``None`` in monitoring-only mode."""
        return self._wallet_id

    @property
    def monitoring_active(self) -> bool:
        """Always ``True``: this manager gates trading only and never disables
        monitoring, so monitoring is retained across connect/revoke (Req 11.5)."""
        return True

    # -- connect / verify (Req 11.1, 11.2, 11.3, 11.6) --------------------

    def connect_wallet(self, wallet_id: str) -> Result[AuthorizationRecord]:
        """Connect a trading wallet, verifying its authorization within 5s.

        On a verification that both succeeds and completes within the bound:
        enable trading, record an ``ENABLED`` status change, and return
        ``Ok(record)`` (Req 11.1). On a verification failure **or** a timeout:
        stay monitoring-only (trading disabled), record a ``FAILED`` status
        change, and return ``Err(error)`` so the caller can surface the error
        indication to the user (Req 11.2). The ``FAILED`` status change is still
        recorded with a timestamp (Req 11.6).
        """
        started = self._monotonic()
        try:
            outcome = self._verify(wallet_id)
        except Exception as exc:  # a misbehaving verifier is a failed verification
            outcome = Err(ProviderError(detail=str(exc), provider="wallet_verifier"))
        elapsed = self._monotonic() - started

        timed_out = elapsed > self._bound_s
        verified = (not timed_out) and self._is_ok(outcome)

        if verified:
            self._trading_enabled = True
            self._wallet_id = wallet_id
            record = self._record(wallet_id, AuthStatus.ENABLED)
            return Ok(record)

        # Failure or timeout -> remain monitoring-only; trading stays disabled.
        self._trading_enabled = False
        self._record(wallet_id, AuthStatus.FAILED)
        return Err(self._failure_error(wallet_id, outcome, timed_out, elapsed))

    # -- revoke (Req 11.4, 11.5, 11.6) ------------------------------------

    def revoke(self) -> Result[AuthorizationRecord]:
        """Revoke trading authorization for the connected wallet.

        Disables trade execution (within the bound; this path performs no
        network I/O), retains monitoring functions (Req 11.5), records a
        ``REVOKED`` status change with a timestamp (Req 11.4, 11.6), and clears
        the in-memory authorization. Returns ``Err(Unverified)`` when no wallet
        is currently authorized, since no status change occurs in that case.
        """
        wallet_id = self._wallet_id
        if wallet_id is None:
            self._trading_enabled = False
            return Err(
                Unverified("no authorized wallet to revoke", subject=None)
            )

        self._trading_enabled = False
        self._wallet_id = None
        record = self._record(wallet_id, AuthStatus.REVOKED)
        return Ok(record)

    # -- helpers -----------------------------------------------------------

    def _record(self, wallet_id: str, status: AuthStatus) -> AuthorizationRecord:
        """Persist a status change with its timestamp (Req 11.6)."""
        record = AuthorizationRecord(
            wallet_id=wallet_id,
            status=status,
            changed_at=self._clock(),
        )
        return self._repo.append(record)

    @staticmethod
    def _is_ok(outcome: Any) -> bool:
        """True iff ``outcome`` is a successful :class:`Result`.

        A verifier should return a ``Result``; tolerate a bare truthy/``None``
        return by treating a non-``Result`` truthy value as success and a
        falsy/``None`` value as failure, so the seam stays easy to fake.
        """
        if isinstance(outcome, (Ok, Err)):
            return outcome.is_ok()
        return bool(outcome)

    def _failure_error(
        self,
        wallet_id: str,
        outcome: Any,
        timed_out: bool,
        elapsed: float,
    ) -> AgentError:
        """Build the error indication surfaced on a failed/timed-out connect."""
        if timed_out:
            return TimedOut(
                "wallet authorization verification exceeded the time bound",
                timeout_s=self._bound_s,
            )
        if isinstance(outcome, Err) and isinstance(outcome.error, AgentError):
            return outcome.error
        return Unverified(
            "wallet authorization verification failed", subject=wallet_id
        )


__all__ = [
    "AuthorizationManager",
    "Verifier",
    "WallClock",
    "MonotonicClock",
]
