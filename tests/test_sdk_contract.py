# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Contract tests for the notification SDK."""

import subprocess
import sys

import hegemony_notification_sdk as sdk


def test_public_surface_is_exported():
    assert sdk.NOTIFICATION_PLUGIN_ENTRY_POINT_GROUP == "hegemony.notification_providers"
    assert isinstance(sdk.SDK_ABI_VERSION, int)
    assert hasattr(sdk, "NotificationPluginRegistry")
    assert hasattr(sdk, "SendFn")
    assert hasattr(sdk, "BuildConfigFn")


def test_registry_is_runtime_checkable_protocol():
    class _Impl:
        api_version = sdk.SDK_ABI_VERSION

        def register_destination_type(self, **_kwargs):
            return None

        def register_preset(self, **_kwargs):
            return None

    assert isinstance(_Impl(), sdk.NotificationPluginRegistry)


def test_sdk_imports_nothing_heavy():
    """Importing the SDK must not pull FastAPI, SQLAlchemy, Temporal, or the platform."""
    code = (
        "import sys, hegemony_notification_sdk\n"
        "heavy = {'fastapi', 'sqlalchemy', 'temporalio', 'apps', 'packages'}\n"
        "leaked = heavy & set(sys.modules)\n"
        "assert not leaked, leaked\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
