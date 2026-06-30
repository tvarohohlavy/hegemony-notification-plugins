# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Public SDK for Hegemony notification plugins.

Dependency-light (pydantic only). Out-of-tree plugin wheels depend on this package and
never import Hegemony app internals. A plugin exposes a ``register(registry)`` callable
under the ``hegemony.notification_providers`` entry-point group.
"""

from __future__ import annotations

from ._version import SDK_ABI_VERSION, __version__
from .registry import BuildConfigFn, NotificationPluginRegistry, SendFn
from .services import NotificationSendContext, NotificationServices

#: The entry-point group out-of-tree notification plugins register under.
NOTIFICATION_PLUGIN_ENTRY_POINT_GROUP = "hegemony.notification_providers"

__all__ = [
    "NOTIFICATION_PLUGIN_ENTRY_POINT_GROUP",
    "SDK_ABI_VERSION",
    "BuildConfigFn",
    "NotificationPluginRegistry",
    "NotificationSendContext",
    "NotificationServices",
    "SendFn",
    "__version__",
]
