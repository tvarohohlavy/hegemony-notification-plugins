# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Webhook-based notification presets (Webex, Microsoft Teams)."""

from hegemony_notification_sdk import NotificationPluginRegistry

from .presets import PRESETS


def register(registry: NotificationPluginRegistry) -> None:
    """Entry point for the ``hegemony.notification_providers`` group."""
    for preset in PRESETS:
        registry.register_preset(
            destination_type=preset.destination_type,
            display_name=preset.display_name,
            description=preset.description,
            base_transport=preset.base_transport,
            build_config=preset.build_config,
            config_schema=preset.config_schema,
        )


__all__ = ["register"]
