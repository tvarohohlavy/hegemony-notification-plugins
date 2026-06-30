# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Hegemony core notification transports: email, shoutrrr, outgoing_webhook.

These are the destination types Hegemony ships with. They are packaged as a plugin (rather
than living in-tree) and auto-installed alongside the platform, so the host carries no
transport code — every destination type, built-in or third-party, loads through the same
``hegemony.notification_providers`` entry-point group.
"""

from hegemony_notification_sdk import NotificationPluginRegistry

from . import email, outgoing_webhook, shoutrrr


def register(registry: NotificationPluginRegistry) -> None:
    """Entry point for the ``hegemony.notification_providers`` group."""
    registry.register_destination_type(
        destination_type="email",
        display_name="Email",
        description="Send notifications via SMTP.",
        send=email.send,
        config_schema=email.CONFIG_SCHEMA,
    )
    registry.register_destination_type(
        destination_type="shoutrrr",
        display_name="Shoutrrr (custom URL)",
        description="Send via a raw Shoutrrr service URL (Discord, Slack, Telegram, …).",
        send=shoutrrr.send,
        config_schema=shoutrrr.CONFIG_SCHEMA,
    )
    registry.register_destination_type(
        destination_type="outgoing_webhook",
        display_name="Outgoing Webhook",
        description="Send an HTTP request to an arbitrary endpoint.",
        send=outgoing_webhook.send,
        config_schema=outgoing_webhook.CONFIG_SCHEMA,
    )


__all__ = ["register"]
