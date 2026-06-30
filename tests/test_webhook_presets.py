# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for the webhook preset plugin: registration + pure config builders."""

import json
from typing import Any

import hegemony_notification_webhook_presets as plugin


class FakeRegistry:
    api_version = 2

    def __init__(self) -> None:
        self.presets: dict[str, dict[str, Any]] = {}

    def register_destination_type(self, **kwargs: Any) -> None:  # pragma: no cover
        raise AssertionError("webhook presets register presets, not native transports")

    def register_preset(self, *, destination_type: str, **kwargs: Any) -> None:
        self.presets[destination_type] = kwargs


def _build(destination_type: str, config: dict[str, Any]) -> dict[str, Any]:
    reg = FakeRegistry()
    plugin.register(reg)
    return reg.presets[destination_type]["build_config"](config)


def test_register_adds_webex_and_teams_over_correct_base_transports():
    reg = FakeRegistry()
    plugin.register(reg)
    assert set(reg.presets) == {"webex", "teams"}
    assert reg.presets["webex"]["base_transport"] == "shoutrrr"
    assert reg.presets["teams"]["base_transport"] == "outgoing_webhook"


def test_webex_builds_shoutrrr_generic_url():
    out = _build("webex", {"webhook_token": "{{ secret('vault://webex') }}"})
    assert out == {
        "url_secret": (
            "generic://webexapis.com/v1/webhooks/incoming/{{ secret('vault://webex') }}"
            "?template=json&messagekey=text"
        )
    }


def test_teams_builds_outgoing_webhook_config_with_adaptive_card():
    out = _build("teams", {"url": "https://example.powerautomate.com/workflows/x"})
    assert out["url"] == "https://example.powerautomate.com/workflows/x"
    assert out["method"] == "POST"
    assert out["auth_type"] == "none"
    # The payload template is a valid Adaptive Card message envelope with title/body slots.
    payload = out["payload_template"]
    assert "{{ title }}" in payload
    assert "{{ body }}" in payload
    parsed = json.loads(payload.replace("{{ title }}", "T").replace("{{ body }}", "B"))
    assert parsed["type"] == "message"
    assert parsed["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"
