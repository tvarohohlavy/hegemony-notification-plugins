# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Friendly notification presets that build Shoutrrr URLs from simple fields.

Each preset rewrites a small, user-friendly config (a bot token, a chat id, …) into the
``shoutrrr`` base transport's config — a single ``url_secret`` holding the Shoutrrr service
URL. Token fields are entered as secret references (e.g. ``{{ secret('vault://…') }}``) and
are passed through untouched; the host's Shoutrrr transport resolves them at send time.

The ``build_config`` functions are pure and synchronous: string assembly only, no I/O and
no secret resolution.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# A secret-reference string field (the user pastes ``{{ secret('…') }}`` / ``{{ env('…') }}``).
_SECRET_FIELD = {"type": "string", "format": "secret-ref"}


@dataclass(frozen=True, slots=True)
class Preset:
    """A user-friendly destination type expressed as a rewrite onto a base transport."""

    destination_type: str
    display_name: str
    description: str
    config_schema: dict[str, Any]
    build_config: Callable[[dict[str, Any]], dict[str, Any]]
    base_transport: str = "shoutrrr"


def _telegram(config: dict[str, Any]) -> dict[str, Any]:
    return {"url_secret": f"telegram://{config['token']}@telegram?chats={config['chats']}"}


def _discord(config: dict[str, Any]) -> dict[str, Any]:
    return {"url_secret": f"discord://{config['token']}@{config['webhook_id']}"}


def _slack(config: dict[str, Any]) -> dict[str, Any]:
    botname = str(config.get("botname") or "").strip()
    prefix = f"{botname}@" if botname else ""
    return {"url_secret": f"slack://{prefix}{config['token']}"}


def _pushover(config: dict[str, Any]) -> dict[str, Any]:
    devices = str(config.get("devices") or "").strip()
    suffix = f"?devices={devices}" if devices else ""
    return {"url_secret": f"pushover://shoutrrr:{config['token']}@{config['user_key']}/{suffix}"}


PRESETS: tuple[Preset, ...] = (
    Preset(
        destination_type="telegram",
        display_name="Telegram",
        description="Send messages via a Telegram bot.",
        config_schema={
            "type": "object",
            "required": ["token", "chats"],
            "properties": {
                "token": {**_SECRET_FIELD, "title": "Bot token"},
                "chats": {"type": "string", "title": "Chat IDs (comma-separated)"},
            },
        },
        build_config=_telegram,
    ),
    Preset(
        destination_type="discord",
        display_name="Discord",
        description="Send messages to a Discord channel webhook.",
        config_schema={
            "type": "object",
            "required": ["token", "webhook_id"],
            "properties": {
                "token": {**_SECRET_FIELD, "title": "Webhook token"},
                "webhook_id": {"type": "string", "title": "Webhook ID"},
            },
        },
        build_config=_discord,
    ),
    Preset(
        destination_type="slack",
        display_name="Slack",
        description="Send messages to a Slack incoming webhook.",
        config_schema={
            "type": "object",
            "required": ["token"],
            "properties": {
                "token": {**_SECRET_FIELD, "title": "Webhook tokens (token-a/token-b/token-c)"},
                "botname": {"type": "string", "title": "Bot name (optional)"},
            },
        },
        build_config=_slack,
    ),
    Preset(
        destination_type="pushover",
        display_name="Pushover",
        description="Send push notifications via Pushover.",
        config_schema={
            "type": "object",
            "required": ["token", "user_key"],
            "properties": {
                "token": {**_SECRET_FIELD, "title": "API token"},
                "user_key": {"type": "string", "title": "User key"},
                "devices": {"type": "string", "title": "Devices (comma-separated, optional)"},
            },
        },
        build_config=_pushover,
    ),
)
