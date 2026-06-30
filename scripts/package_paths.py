# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PACKAGE_DIRS = (
    ROOT / "packages" / "notification_sdk",
    ROOT / "plugins" / "notification_core_transports",
    ROOT / "plugins" / "notification_shoutrrr_presets",
    ROOT / "plugins" / "notification_webhook_presets",
)

PLUGIN_DIRS = PACKAGE_DIRS[1:]
SDK_VERSION_FILE = (
    ROOT / "packages" / "notification_sdk" / "src" / "hegemony_notification_sdk" / "_version.py"
)
