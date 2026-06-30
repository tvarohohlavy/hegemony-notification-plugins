# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Shoutrrr transport: send via the ``shoutrrr`` CLI using a raw service URL.

Shoutrrr supports many services (Discord, Slack, Teams, Telegram, …) via URL config. The
URL is supplied as a secret reference and resolved by the host at send time.
"""

import asyncio
import logging
import os
import shutil

from hegemony_notification_sdk import NotificationSendContext

logger = logging.getLogger(__name__)

DEFAULT_SHOUTRRR_TIMEOUT_SECONDS = 30


def _get_shoutrrr_binary() -> str:
    """Find the shoutrrr binary in PATH or common container locations."""
    binary = shutil.which("shoutrrr")
    if binary:
        return binary
    for path in ("/usr/local/bin/shoutrrr", "/usr/bin/shoutrrr", "/app/shoutrrr"):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    raise FileNotFoundError(
        "shoutrrr binary not found. Ensure it is installed and in PATH. "
        "Download from: https://github.com/nicholas-fedor/shoutrrr/releases"
    )


async def send(ctx: NotificationSendContext) -> None:
    """Send a notification via the Shoutrrr CLI."""
    config, title, body, services = ctx.config, ctx.title, ctx.body, ctx.services

    url_ref = config.get("url_secret")
    if isinstance(url_ref, str):
        url_ref = url_ref.strip() or None
    url_ref = services.validate_secret_ref(url_ref, field_name="url_secret", required=True)
    assert url_ref is not None

    url = await services.resolve_secret_ref(url_ref, source="notification.shoutrrr")
    if not url:
        raise ValueError(
            f"Could not resolve '{url_ref}' - ensure the referenced secret exists "
            "(environment variable, file, or dynamic backend)."
        )

    # Title/body (incl. any per-destination override) are finalized by the host before
    # dispatch; the transport just renders them.
    message = f"{title}\n\n{body}"

    binary = _get_shoutrrr_binary()
    cmd = [binary, "send", "--url", url, "--message", message]
    logger.debug("Executing shoutrrr: %s send --url <redacted> <message>", binary)
    timeout = DEFAULT_SHOUTRRR_TIMEOUT_SECONDS

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"Shoutrrr command timed out after {timeout}s") from None

        if process.returncode != 0:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            raise RuntimeError(f"Shoutrrr failed (exit {process.returncode}): {error_msg}")

        logger.info("Shoutrrr notification sent successfully via %s", url_ref)
    except FileNotFoundError as err:
        raise FileNotFoundError(
            f"shoutrrr binary not found at {binary}. Ensure it is installed."
        ) from err


CONFIG_SCHEMA = {
    "type": "object",
    "required": ["url_secret"],
    "properties": {
        "url_secret": {
            "type": "string",
            "x_secret_ref": True,
            "title": "Shoutrrr URL (secret reference)",
        },
    },
}
