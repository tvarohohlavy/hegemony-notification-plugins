<!--
SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# hegemony-notification-webhook-presets

Friendly presets for team-chat services reached via incoming webhooks. Both
rewrite onto the `outgoing_webhook` base transport (a plain HTTP POST) — no
Shoutrrr binary required:

| Destination | Base transport | Fields |
|-------------|----------------|--------|
| `webex_incoming_webhook` | `outgoing_webhook` | incoming webhook token (secret) |
| `teams_power_automate` | `outgoing_webhook` | Power Automate workflow URL (secret) |

Type names pin the *method* so other methods for the same service can coexist as
separate presets later (e.g. a Webex Messages bot-API variant, or a Teams Graph bot).

- **`webex_incoming_webhook`** POSTs `{"markdown": "**<title>**\n\n<body>"}` to
  `https://webexapis.com/v1/webhooks/incoming/<token>`. The token may be a secret
  reference, resolved in the URL at send time. (The Webex Messages bot API — bot
  token + room id — is a different method, not covered here.)
- **`teams_power_automate`** POSTs an Adaptive Card to a Microsoft Teams **Power
  Automate** "When a Teams webhook request is received" workflow — the supported path
  now that Office 365 connectors are retired.

Secret/sensitive values (the Webex token, the Teams URL signature) are entered as
secret references and resolved by the host at send time; this plugin never handles
secret values.

## Install

```bash
pip install hegemony-notification-webhook-presets
```

The worker discovers it via the `hegemony.notification_providers` entry-point group.
