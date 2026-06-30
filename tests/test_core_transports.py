# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for the core transports plugin: registration + send paths via injected services."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import hegemony_notification_core_transports as plugin
from hegemony_notification_sdk import NotificationSendContext


class FakeServices:
    """In-memory ``NotificationServices`` for transport tests.

    ``secrets`` maps a reference string to its resolved value; unknown refs resolve to
    themselves (so plain literals pass through). Records resolved refs for assertions.
    """

    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self.secrets = secrets or {}
        self.resolved: list[tuple[str, str]] = []

    async def resolve_secret_ref(self, ref: str | None, *, source: str) -> str | None:
        if ref is None:
            return None
        self.resolved.append((ref, source))
        return self.secrets.get(ref, ref)

    def validate_secret_ref(self, ref: Any, *, field_name: str, required: bool = False):
        if ref is None or (isinstance(ref, str) and not ref.strip()):
            if required:
                raise ValueError(f"{field_name} is required")
            return None
        return ref

    def render_message(
        self, template: str, *, title: str, body: str, escape_json_strings: bool = False
    ) -> str:
        return template.replace("{{ title }}", title).replace("{{ body }}", body)

    async def render_template(self, template: str) -> str:
        return template

    def contains_template(self, value: str) -> bool:
        return "{{" in value


class FakeRegistry:
    api_version = 2

    def __init__(self) -> None:
        self.types: dict[str, dict[str, Any]] = {}

    def register_destination_type(self, *, destination_type: str, **kwargs: Any) -> None:
        self.types[destination_type] = kwargs

    def register_preset(self, **kwargs: Any) -> None:  # pragma: no cover
        raise AssertionError("core transports register native types, not presets")


def _ctx(config: dict[str, Any], services: FakeServices, title="T", body="B"):
    return NotificationSendContext(config=config, title=title, body=body, services=services)


def test_register_adds_three_native_transports():
    reg = FakeRegistry()
    plugin.register(reg)
    assert set(reg.types) == {"email", "shoutrrr", "outgoing_webhook"}
    for entry in reg.types.values():
        assert callable(entry["send"])
        assert entry["config_schema"]["type"] == "object"


@pytest.mark.asyncio
async def test_shoutrrr_resolves_url_and_invokes_binary():
    from hegemony_notification_core_transports import shoutrrr

    services = FakeServices(secrets={"{{ secret('vault://sh') }}": "telegram://tok@telegram"})
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"", b""))
    proc.returncode = 0
    with (
        patch.object(shoutrrr.shutil, "which", return_value="/usr/bin/shoutrrr"),
        patch.object(shoutrrr.asyncio, "create_subprocess_exec", return_value=proc) as exec_mock,
    ):
        await shoutrrr.send(_ctx({"url_secret": "{{ secret('vault://sh') }}"}, services))
    args = exec_mock.call_args.args
    assert "telegram://tok@telegram" in args  # resolved URL passed to the binary
    assert "send" in args


@pytest.mark.asyncio
async def test_email_resolves_config_and_sends():
    from hegemony_notification_core_transports import email

    services = FakeServices(
        secrets={
            email.DEFAULT_SMTP_PORT_EXPR: "587",
            email.DEFAULT_SMTP_USE_TLS_EXPR: "false",
            email.DEFAULT_SMTP_USE_STARTTLS_EXPR: "true",
        }
    )
    config = {"to": ["ops@example.com"], "from": "noreply@example.com", "smtp_host_ref": "smtp.x"}
    with patch("aiosmtplib.send", new_callable=AsyncMock) as send_mock:
        await email.send(_ctx(config, services))
    assert send_mock.await_count == 1
    kwargs = send_mock.call_args.kwargs
    assert kwargs["hostname"] == "smtp.x"
    assert kwargs["port"] == 587


@pytest.mark.asyncio
async def test_webhook_posts_payload_with_bearer_auth():
    from hegemony_notification_core_transports import outgoing_webhook

    services = FakeServices(secrets={"{{ secret('vault://tok') }}": "s3cret"})
    config = {
        "url": "https://example.com/hook",
        "auth_type": "bearer",
        "auth_token_ref": "{{ secret('vault://tok') }}",
    }
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.status_code = 200
    client = MagicMock()
    client.request = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    with patch.object(outgoing_webhook.httpx, "AsyncClient", return_value=client):
        await outgoing_webhook.send(_ctx(config, services))
    kwargs = client.request.call_args.kwargs
    assert kwargs["url"] == "https://example.com/hook"
    assert kwargs["headers"]["Authorization"] == "Bearer s3cret"


@pytest.mark.asyncio
async def test_webhook_rejects_credentialed_url():
    from hegemony_notification_core_transports import outgoing_webhook

    services = FakeServices()
    with pytest.raises(ValueError, match="credentials"):
        await outgoing_webhook.send(_ctx({"url": "https://user:pass@example.com/hook"}, services))
