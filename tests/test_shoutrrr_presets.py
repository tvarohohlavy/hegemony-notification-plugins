# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for the Shoutrrr preset plugin: registration + pure config builders."""

from typing import Any

import hegemony_notification_shoutrrr_presets as plugin


class FakeRegistry:
    """Captures register_preset calls; satisfies the SDK Protocol surface used here."""

    api_version = 1

    def __init__(self) -> None:
        self.presets: dict[str, dict[str, Any]] = {}

    def register_destination_type(self, **kwargs: Any) -> None:  # pragma: no cover
        raise AssertionError("preset plugin should not register native transports")

    def register_preset(self, *, destination_type: str, **kwargs: Any) -> None:
        self.presets[destination_type] = kwargs


def _build(destination_type: str, config: dict[str, Any]) -> dict[str, Any]:
    reg = FakeRegistry()
    plugin.register(reg)
    return reg.presets[destination_type]["build_config"](config)


def test_register_adds_all_presets_over_shoutrrr():
    reg = FakeRegistry()
    plugin.register(reg)
    assert set(reg.presets) == {"telegram", "discord", "slack", "pushover"}
    for entry in reg.presets.values():
        assert entry["base_transport"] == "shoutrrr"
        assert "config_schema" in entry


def test_telegram_url_and_secret_passthrough():
    out = _build("telegram", {"token": "{{ secret('vault://tg') }}", "chats": "1,2"})
    assert out == {"url_secret": "telegram://{{ secret('vault://tg') }}@telegram?chats=1,2"}


def test_discord_url():
    out = _build("discord", {"token": "tok", "webhook_id": "123"})
    assert out == {"url_secret": "discord://tok@123"}


def test_slack_url_with_and_without_botname():
    assert _build("slack", {"token": "a/b/c"}) == {"url_secret": "slack://a/b/c"}
    assert _build("slack", {"token": "a/b/c", "botname": "bot"}) == {
        "url_secret": "slack://bot@a/b/c"
    }


def test_pushover_url_with_optional_devices():
    assert _build("pushover", {"token": "t", "user_key": "u"}) == {
        "url_secret": "pushover://shoutrrr:t@u/"
    }
    assert _build("pushover", {"token": "t", "user_key": "u", "devices": "phone"}) == {
        "url_secret": "pushover://shoutrrr:t@u/?devices=phone"
    }
