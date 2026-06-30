# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Friendly presets for team-chat services reached via incoming webhooks.

Both presets rewrite a small, user-friendly config onto the ``outgoing_webhook`` base
transport (a plain HTTP POST) — no Shoutrrr binary required:

- ``webex`` POSTs ``{"markdown": ...}`` to a Webex incoming webhook URL.
- ``teams`` POSTs an Adaptive Card to a Microsoft Teams *Power Automate* "When a Teams
  webhook request is received" workflow (the successor to the retired Office 365
  connectors).

``build_config`` functions are pure and synchronous: string assembly only. Secret
references pass through untouched for the base transport to resolve at send time.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# A secret-reference string field (the user pastes ``{{ secret('…') }}`` / ``{{ env('…') }}``).
_SECRET_FIELD = {"type": "string", "format": "secret-ref"}

# Webex incoming-webhook payload. ``{{ title }}`` / ``{{ body }}`` are rendered (and
# JSON-escaped) by the outgoing_webhook transport; Webex renders the ``markdown`` field.
_WEBEX_PAYLOAD_TEMPLATE = '{"markdown": "**{{ title }}**\\n\\n{{ body }}"}'

# Adaptive Card posted to a Microsoft Teams Power Automate workflow. ``{{ title }}`` /
# ``{{ body }}`` are rendered (and JSON-escaped) by the outgoing_webhook transport.
_TEAMS_PAYLOAD_TEMPLATE = """{
  "type": "message",
  "attachments": [
    {
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
          {
            "type": "TextBlock",
            "text": "{{ title }}",
            "weight": "Bolder",
            "size": "Medium"
          },
          {
            "type": "TextBlock",
            "text": "{{ body }}",
            "wrap": true
          }
        ]
      }
    }
  ]
}"""


@dataclass(frozen=True, slots=True)
class Preset:
    """A user-friendly destination type expressed as a rewrite onto a base transport."""

    destination_type: str
    display_name: str
    description: str
    base_transport: str
    config_schema: dict[str, Any]
    build_config: Callable[[dict[str, Any]], dict[str, Any]]


def _webex(config: dict[str, Any]) -> dict[str, Any]:
    # Plain HTTP POST of a markdown message to the Webex incoming webhook URL. The token
    # may be a secret reference; the outgoing_webhook transport resolves it in the URL.
    return {
        "url": f"https://webexapis.com/v1/webhooks/incoming/{config['webhook_token']}",
        "method": "POST",
        "payload_template": _WEBEX_PAYLOAD_TEMPLATE,
    }


def _teams(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": config["url"],
        "method": "POST",
        "auth_type": "none",
        "verify_tls": True,
        "retry_count": 3,
        "retry_backoff_seconds": 2,
        "timeout_seconds": 30,
        "payload_template": _TEAMS_PAYLOAD_TEMPLATE,
    }


PRESETS: tuple[Preset, ...] = (
    Preset(
        destination_type="webex",
        display_name="Webex",
        description="Post a markdown message to a Webex space via its incoming webhook.",
        base_transport="outgoing_webhook",
        config_schema={
            "type": "object",
            "required": ["webhook_token"],
            "properties": {
                "webhook_token": {
                    **_SECRET_FIELD,
                    "title": "Incoming webhook token",
                    "description": "The path token from the Webex incoming webhook URL.",
                },
            },
        },
        build_config=_webex,
    ),
    Preset(
        destination_type="teams",
        display_name="Microsoft Teams",
        description="Post an Adaptive Card to a Teams Power Automate workflow webhook.",
        base_transport="outgoing_webhook",
        config_schema={
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {
                    "type": "string",
                    "format": "secret-ref",
                    "title": "Power Automate workflow URL",
                    "description": (
                        "The 'When a Teams webhook request is received' trigger URL. May be a "
                        "secret reference; it contains a signature query parameter."
                    ),
                },
            },
        },
        build_config=_teams,
    ),
)
