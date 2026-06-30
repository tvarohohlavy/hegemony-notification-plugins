# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Platform services injected into notification transports at send time.

An out-of-tree transport (e.g. the auto-installed core ``email``/``shoutrrr``/
``outgoing_webhook`` plugin) never imports the platform's secret backends, template
resolver, or formatting helpers. Instead the host builds a :class:`NotificationSendContext`
— the message ``config``/``title``/``body`` plus a :class:`NotificationServices` bound to
the current run — and passes it to the transport's ``send``. The transport calls these
methods; secret resolution and template rendering stay inside the platform.

This mirrors ``hegemony_inventory_sdk.PlatformServices``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class NotificationServices(Protocol):
    """Injected platform capabilities a transport uses to resolve and render content."""

    async def resolve_secret_ref(self, ref: str | None, *, source: str) -> str | None:
        """Resolve an opaque secret/template reference to its value (platform-side)."""
        ...

    def validate_secret_ref(
        self, ref: Any, *, field_name: str, required: bool = False
    ) -> str | None:
        """Validate that ``ref`` is a protected template reference; return it normalized.

        Raises if ``required`` and missing, or if a raw (unprotected) literal is supplied
        where a secret reference is expected. Pure: performs no resolution or I/O.
        """
        ...

    def render_message(
        self, template: str, *, title: str, body: str, escape_json_strings: bool = False
    ) -> str:
        """Render a per-destination message template with the notification title/body.

        ``escape_json_strings`` JSON-escapes interpolated values for templates that emit
        a JSON document (used by webhook payload templates).
        """
        ...

    async def render_template(self, template: str) -> str:
        """Resolve a full-scope template string (vars, env, secrets) to its value."""
        ...

    def contains_template(self, value: str) -> bool:
        """Whether ``value`` contains template (Jinja) expressions."""
        ...


@dataclass(frozen=True, slots=True)
class NotificationSendContext:
    """Everything a transport needs to send one already-formatted notification."""

    config: dict[str, Any]
    title: str
    body: str
    services: NotificationServices
