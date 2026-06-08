"""Telegram Bot API adapter - notification channel.

Design reference: "Per-Integration Details" -> Telegram. Implements
:class:`NotificationChannel` by delivering an :class:`Alert` through the bot
``sendMessage`` method (Req 8.x). The bot token and target chat id are injected
from secrets/config (never hard-coded or logged - design "Security
Considerations"). Per-channel retry, quiet-hours, and final-status recording are
the Notifier's responsibility (Task 17); this adapter performs a single delivery
attempt and reports its typed outcome.

The injected :class:`~dex_agent.providers.clients.HttpClient` keeps it testable
with no real Telegram call.
"""

from __future__ import annotations

from typing import Any, Mapping

from dex_agent.errors import ProviderError
from dex_agent.providers.adapters._common import run_request
from dex_agent.providers.clients import HttpClient
from dex_agent.providers.interfaces import (
    Alert,
    DeliveryResult,
    NotificationChannel,
)
from dex_agent.result import Err, Ok, Result

API_BASE = "https://api.telegram.org"
PROVIDER = "Telegram"
CHANNEL_NAME = "telegram"


class TelegramChannel(NotificationChannel):
    """Delivers alerts via the Telegram bot ``sendMessage`` method."""

    def __init__(
        self,
        http: HttpClient,
        *,
        bot_token: str,
        chat_id: str,
        base_url: str = API_BASE,
        parse_mode: str | None = None,
    ) -> None:
        self._http = http
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._base = base_url.rstrip("/")
        self._parse_mode = parse_mode

    def _render(self, alert: Alert) -> str:
        if alert.title and alert.body:
            return f"{alert.title}\n{alert.body}"
        return alert.title or alert.body

    def deliver(self, alert: Alert) -> Result[DeliveryResult]:
        body: dict[str, Any] = {"chat_id": self._chat_id, "text": self._render(alert)}
        if self._parse_mode:
            body["parse_mode"] = self._parse_mode
        url = f"{self._base}/bot{self._bot_token}/sendMessage"
        result = run_request(
            lambda: self._http.request("POST", url, json=body),
            provider=PROVIDER,
        )
        if result.is_err():
            return result
        payload: Mapping[str, Any] = result.value if isinstance(result.value, Mapping) else {}
        if payload.get("ok") is False:
            return Err(
                ProviderError(
                    f"Telegram API error: {payload.get('description', 'unknown')}",
                    provider=PROVIDER,
                    context={"error_code": payload.get("error_code")},
                )
            )
        return Ok(DeliveryResult(channel=CHANNEL_NAME, delivered=True))


__all__ = ["TelegramChannel", "API_BASE", "CHANNEL_NAME"]
