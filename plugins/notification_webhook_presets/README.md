<!--
SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# hegemony-notification-webhook-presets

Friendly presets for team-chat services reached via incoming webhooks. Each
exposes a couple of fields and rewrites them onto a base transport:

| Destination | Base transport | Fields |
|-------------|----------------|--------|
| `webex` | `shoutrrr` | incoming webhook token (secret) |
| `teams` | `outgoing_webhook` | Power Automate workflow URL (secret) |

- **Webex** builds a Shoutrrr `generic://webexapis.com/v1/webhooks/incoming/<token>?template=json&messagekey=text`
  URL, so it needs the host's `shoutrrr` transport (and the `shoutrrr` binary).
- **Teams** builds an `outgoing_webhook` config that POSTs an Adaptive Card to a
  Microsoft Teams **Power Automate** "When a Teams webhook request is received"
  workflow — the supported path now that Office 365 connectors are retired. Other
  approaches exist; this preset targets the Power Automate flow URL.

Secret/sensitive values (the Webex token, the Teams URL signature) are entered as
secret references and resolved by the host at send time; this plugin never handles
secret values.

## Install

```bash
pip install hegemony-notification-webhook-presets
```

The worker discovers it via the `hegemony.notification_providers` entry-point group.
