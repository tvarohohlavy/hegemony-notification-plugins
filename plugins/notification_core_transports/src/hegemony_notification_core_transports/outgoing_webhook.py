# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Outgoing Webhook transport: HTTP request to an arbitrary endpoint.

Supports configurable auth (bearer/basic/custom header), TLS verification with an optional
custom CA, HMAC request signing, a custom payload template, and retries. Secret resolution
and template rendering are provided by the injected services.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import re
import ssl
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from hegemony_notification_sdk import NotificationSendContext, NotificationServices

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 2
HTTP_HEADER_TOKEN_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


def _looks_like_json_payload_template(template: str) -> bool:
    stripped = template.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _redact_url(url: str) -> str:
    """Return a safe URL summary (scheme + host) without secrets."""
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme or "http"
        hostname = parsed.hostname or parsed.netloc or "unknown"
        port = f":{parsed.port}" if parsed.port else ""
        safe_path = "/…" if parsed.path else "/"
        return f"{scheme}://{hostname}{port}{safe_path}"
    except Exception:
        return "<redacted>"


def _validate_resolved_webhook_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Webhook 'url' resolved to an empty value")
    normalized = url.strip()
    parsed = urlparse(normalized)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise ValueError("Resolved webhook 'url' must start with http:// or https://")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(
            "Resolved webhook 'url' must not contain credentials; use auth fields instead"
        )
    return normalized


def _describe_configured_webhook_url(services: NotificationServices, url_value: Any) -> str:
    if not isinstance(url_value, str) or not url_value.strip():
        return "<configured-webhook-url>"
    normalized = url_value.strip()
    if services.contains_template(normalized):
        return "<templated-webhook-url>"
    return _redact_url(normalized)


async def _resolve_webhook_url(services: NotificationServices, url_value: Any) -> str:
    if not isinstance(url_value, str) or not url_value.strip():
        raise ValueError("Missing required webhook 'url'")
    normalized = url_value.strip()
    if not services.contains_template(normalized):
        return _validate_resolved_webhook_url(normalized)
    try:
        resolved = await services.render_template(normalized)
    except ValueError as exc:
        raise ValueError("Could not parse or resolve webhook 'url' template.") from exc
    if resolved is None or not str(resolved).strip():
        raise ValueError("Webhook 'url' template resolved to an empty value")
    return _validate_resolved_webhook_url(str(resolved))


async def _resolve_auth_headers(
    services: NotificationServices, config: dict[str, Any]
) -> dict[str, str]:
    auth_type = config.get("auth_type", "none")
    headers: dict[str, str] = {}

    if auth_type == "bearer":
        ref = services.validate_secret_ref(
            config.get("auth_token_ref"), field_name="auth_token_ref", required=True
        )
        assert ref is not None
        token = await services.resolve_secret_ref(ref, source="notification.outgoing_webhook")
        if not token:
            raise ValueError(f"Could not resolve '{ref}' - ensure the referenced secret exists.")
        headers["Authorization"] = f"Bearer {token}"

    elif auth_type == "basic":
        username = config.get("auth_username", "")
        ref = services.validate_secret_ref(
            config.get("auth_password_ref"), field_name="auth_password_ref", required=True
        )
        assert ref is not None
        password = await services.resolve_secret_ref(ref, source="notification.outgoing_webhook")
        if not password:
            raise ValueError(f"Could not resolve '{ref}' - ensure the referenced secret exists.")
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

    elif auth_type == "custom_header":
        header_name = config.get("auth_header_name", "")
        if (
            not isinstance(header_name, str)
            or not header_name.strip()
            or not HTTP_HEADER_TOKEN_PATTERN.fullmatch(header_name)
        ):
            raise ValueError(
                "'auth_header_name' must be a non-empty string when auth_type is 'custom_header'"
            )
        ref = services.validate_secret_ref(
            config.get("auth_header_value_ref"), field_name="auth_header_value_ref", required=True
        )
        assert ref is not None
        header_value = await services.resolve_secret_ref(
            ref, source="notification.outgoing_webhook"
        )
        if not header_value:
            raise ValueError(f"Could not resolve '{ref}' - ensure the referenced secret exists.")
        headers[header_name] = header_value

    elif auth_type != "none":
        raise ValueError(f"Unsupported webhook auth_type '{auth_type}' in _resolve_auth_headers")

    return headers


def _build_ssl_context(config: dict[str, Any]) -> ssl.SSLContext | bool:
    verify_tls = config.get("verify_tls", True)
    ca_bundle = config.get("custom_ca_bundle")
    if not verify_tls:
        return False
    if ca_bundle:
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cadata=ca_bundle)
        return ctx
    return True


def _compute_hmac_signature(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def _apply_signing_policy(
    services: NotificationServices,
    signing: dict[str, Any],
    payload_bytes: bytes,
    headers: dict[str, str],
) -> None:
    algorithm = signing.get("algorithm", "hmac-sha256")
    if algorithm != "hmac-sha256":
        raise ValueError(f"Unsupported signing algorithm '{algorithm}'")

    ref = services.validate_secret_ref(
        signing.get("secret_ref"), field_name="signing.secret_ref", required=True
    )
    assert ref is not None
    secret = await services.resolve_secret_ref(ref, source="notification.outgoing_webhook")
    if not secret:
        raise ValueError(
            "signing.secret_ref is configured but could not be resolved to a non-empty secret"
        )

    sig_header = signing.get("signature_header", "X-Webhook-Signature")
    ts_header = signing.get("timestamp_header")
    signed_content = signing.get("signed_content", "body")
    prefix = signing.get("prefix", "")

    if signed_content == "timestamp_dot_body" and not ts_header:
        raise ValueError(
            "signing.timestamp_header is required when signing.signed_content='timestamp_dot_body'"
        )

    timestamp: str | None = None
    if ts_header:
        timestamp = str(int(time.time()))
        headers[ts_header] = timestamp

    if signed_content == "timestamp_dot_body" and timestamp:
        message = f"{timestamp}.".encode() + payload_bytes
    else:
        message = payload_bytes

    sig = _compute_hmac_signature(secret, message)
    headers[sig_header] = f"{prefix}{sig}"


def _summarize_http_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code if exc.response is not None else "unknown"
        detail: str | None = None
        if exc.response is not None:
            try:
                payload = exc.response.json()
            except Exception:
                payload = None
            if isinstance(payload, dict):
                raw_detail = payload.get("detail")
                if isinstance(raw_detail, str):
                    detail = raw_detail.strip() or None
            if detail is None:
                text = (exc.response.text or "").strip()
                if text:
                    detail = text[:160]
        if detail:
            return f"HTTP {status}: {detail}"
        return f"HTTP {status}"
    if isinstance(exc, httpx.TimeoutException):
        return "request timeout"
    if isinstance(exc, httpx.ConnectError):
        return "connection failed"
    if isinstance(exc, httpx.NetworkError):
        return "network error"
    return exc.__class__.__name__


async def send(ctx: NotificationSendContext) -> None:
    """Send a notification via outgoing HTTP webhook."""
    config, title, body, services = ctx.config, ctx.title, ctx.body, ctx.services

    configured_url = config.get("url")
    method = config.get("method", "POST").upper()
    timeout = config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    retry_count = config.get("retry_count", DEFAULT_RETRY_COUNT)
    retry_backoff = config.get("retry_backoff_seconds", DEFAULT_RETRY_BACKOFF_SECONDS)

    request_headers: dict[str, str] = {"Content-Type": "application/json"}
    extra_headers = config.get("headers")
    if extra_headers and isinstance(extra_headers, dict):
        request_headers.update(extra_headers)

    request_headers.update(await _resolve_auth_headers(services, config))

    payload_template = config.get("payload_template")
    if payload_template:
        if not isinstance(payload_template, str):
            logger.error(
                "payload_template is not a string (type=%s), falling back to default payload",
                type(payload_template).__name__,
            )
            payload_bytes = json.dumps({"title": title, "body": body}).encode()
        else:
            payload_str = services.render_message(
                payload_template,
                title=title,
                body=body,
                escape_json_strings=_looks_like_json_payload_template(payload_template),
            )
            payload_bytes = payload_str.encode()
    else:
        payload_bytes = json.dumps({"title": title, "body": body}).encode()

    signing_policy = config.get("signing")
    if signing_policy is not None:
        if not isinstance(signing_policy, dict):
            raise ValueError("Invalid 'signing' field: expected object")
        await _apply_signing_policy(services, signing_policy, payload_bytes, request_headers)

    ssl_ctx = _build_ssl_context(config)
    destination_label = _describe_configured_webhook_url(services, configured_url)

    logger.debug(
        "Sending outgoing webhook: method=%s url=%s verify_tls=%s",
        method,
        destination_label,
        config.get("verify_tls", True),
    )

    last_error: Exception | None = None
    max_attempts = retry_count + 1
    attempts_made = 0

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout), verify=ssl_ctx) as client:
        for attempt in range(max_attempts):
            attempts_made = attempt + 1
            try:
                url = await _resolve_webhook_url(services, configured_url)
                destination_label = _redact_url(url)
                response = await client.request(
                    method=method, url=url, content=payload_bytes, headers=request_headers
                )
                response.raise_for_status()
                logger.info(
                    "Outgoing webhook delivered: url=%s status=%s",
                    destination_label,
                    response.status_code,
                )
                return
            except ValueError:
                raise
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else 0
                if 400 <= status_code < 500:
                    logger.error(
                        "Outgoing webhook got HTTP %d from %s; not retrying client error",
                        status_code,
                        destination_label,
                    )
                    break
                if attempt < retry_count:
                    wait_time = retry_backoff * (2**attempt)
                    logger.warning(
                        "Outgoing webhook attempt %d/%d failed (url=%s, status=%d). Retrying in %.1fs...",
                        attempt + 1,
                        max_attempts,
                        destination_label,
                        status_code,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
            except Exception as exc:
                last_error = exc
                if attempt < retry_count:
                    wait_time = retry_backoff * (2**attempt)
                    logger.warning(
                        "Outgoing webhook attempt %d/%d failed (url=%s). Retrying in %.1fs...",
                        attempt + 1,
                        max_attempts,
                        destination_label,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)

    if last_error is not None:
        reason = _summarize_http_error(last_error)
        raise RuntimeError(
            f"Outgoing webhook delivery failed after {attempts_made} attempt(s) "
            f"to {destination_label} ({reason})"
        ) from last_error
    raise RuntimeError(
        f"Outgoing webhook delivery failed after {attempts_made} attempt(s) to {destination_label}"
    )


CONFIG_SCHEMA = {
    "type": "object",
    "required": ["url"],
    "properties": {
        "url": {"type": "string", "title": "URL"},
        "method": {"type": "string", "enum": ["POST", "PUT"], "title": "Method"},
        "headers": {"type": "object", "title": "Headers (optional)"},
        "payload_template": {"type": "string", "title": "Payload template (optional)"},
        "timeout_seconds": {"type": "number", "title": "Timeout (seconds)"},
        "auth_type": {
            "type": "string",
            "enum": ["none", "bearer", "basic", "custom_header"],
            "title": "Auth type",
        },
    },
}
