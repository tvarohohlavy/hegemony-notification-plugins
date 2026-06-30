<!--
SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# hegemony-notification-plugins

Out-of-tree **notification plugins** for the Hegemony workflow-automation
platform, plus the dependency-light SDK they build against. This mirrors
[`hegemony-inventory-plugins`](../hegemony-inventory-plugins): the platform loads
these wheels at runtime via an entry-point group, and they are **opt-in** — not
bundled into the core images.

## Layout

```
packages/
  notification_sdk/                 # hegemony-notification-sdk (pydantic-only contract)
plugins/
  notification_shoutrrr_presets/    # Telegram/Discord/Slack/Pushover presets over shoutrrr
tests/                              # SDK contract + preset config-builder tests
```

## How it plugs in

A plugin exposes a `register(registry)` callable under the
`hegemony.notification_providers` entry-point group. The host (worker) discovers
installed plugins, passes its registry facade, and the plugin registers one or
more destination types — most simply as **presets** that rewrite a friendly
config onto a base transport (see the SDK README). The host owns secret
resolution and the actual send.

## Develop

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ty check
```

## Install a plugin into a Hegemony deployment

```bash
pip install hegemony-notification-shoutrrr-presets
```
