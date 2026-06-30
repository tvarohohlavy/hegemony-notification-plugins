<!--
SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# hegemony-notification-sdk

Public, dependency-light SDK for building **Hegemony notification plugins** —
out-of-tree wheels that add notification destination types to the core platform
at runtime.

A plugin depends only on this package (which depends only on `pydantic`) and
exposes a `register(registry)` callable under the
`hegemony.notification_providers` entry-point group:

```toml
# In your plugin's pyproject.toml
[project.entry-points."hegemony.notification_providers"]
my_plugin = "my_plugin:register"

[project.dependencies]
hegemony-notification-sdk = ">=0.1,<0.2"
```

## Presets (recommended)

The simplest way to add a user-friendly channel is a **preset** over an existing
transport. The plugin contributes a friendly `config_schema` and a *pure*
`build_config` that rewrites the friendly fields into the base transport's
config. Secret references pass through untouched — the host's base transport
resolves them at send time, so the plugin never handles secrets or performs I/O.

```python
# my_plugin/__init__.py
from hegemony_notification_sdk import NotificationPluginRegistry


def register(registry: NotificationPluginRegistry) -> None:
    registry.register_preset(
        destination_type="telegram",
        display_name="Telegram",
        description="Send via a Telegram bot.",
        base_transport="shoutrrr",
        build_config=lambda cfg: {
            "url_secret": f"telegram://{cfg['token']}@telegram?chats={cfg['chats']}"
        },
        config_schema={
            "type": "object",
            "required": ["token", "chats"],
            "properties": {
                "token": {"type": "string", "title": "Bot token (secret reference)"},
                "chats": {"type": "string", "title": "Chat IDs (comma-separated)"},
            },
        },
    )
```

## Native transports

For channels that cannot be expressed as a preset, register a native
destination type with its own `send` coroutine via
`register_destination_type(...)`.

## ABI

`SDK_ABI_VERSION` is bumped only on incompatible changes to the registration
contract. The platform exposes its value as `registry.api_version` so a plugin
can self-gate if needed.
