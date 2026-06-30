# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The registry facade contract a plugin's ``register(registry)`` callable receives.

The core platform supplies a concrete object satisfying this Protocol. Plugins program
against the Protocol only, never against the platform's registry internals.

Two registration shapes are offered:

- :meth:`register_preset` — the recommended shape for adding a user-friendly destination
  on top of an existing transport (e.g. Telegram/Slack over ``shoutrrr``). The plugin
  contributes a friendly ``config_schema`` and a *pure* ``build_config`` that rewrites the
  friendly config into the base transport's config. Secret resolution and the actual send
  stay in the host's base transport, so the plugin never touches platform internals.
- :meth:`register_destination_type` — a native transport with its own ``send`` coroutine,
  for channels that are not expressible as a preset over an existing transport.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

# Sends one already-formatted notification: ``await send(config, title, body)``. Any secret
# references in ``config`` are resolved by the transport, never by the SDK or the caller.
SendFn = Callable[[dict[str, Any], str, str], Awaitable[None]]

# Rewrites a friendly preset config into a base transport's config. Must be pure and
# synchronous: no I/O and no secret resolution — secret references pass through untouched.
BuildConfigFn = Callable[[dict[str, Any]], dict[str, Any]]


@runtime_checkable
class NotificationPluginRegistry(Protocol):
    """Registration surface passed to ``register(registry)`` plugin callables."""

    #: The platform's plugin registration ABI version (see ``SDK_ABI_VERSION``).
    api_version: int

    def register_destination_type(
        self,
        *,
        destination_type: str,
        display_name: str,
        description: str,
        send: SendFn,
        config_schema: dict[str, Any] | None = None,
    ) -> None:
        """Register a native destination type with its own ``send`` implementation."""
        ...

    def register_preset(
        self,
        *,
        destination_type: str,
        display_name: str,
        description: str,
        base_transport: str,
        build_config: BuildConfigFn,
        config_schema: dict[str, Any] | None = None,
    ) -> None:
        """Register a friendly preset that rewrites its config onto a base transport."""
        ...
