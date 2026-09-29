"""Shared plumbing for Meta's Graph API (Messenger and WhatsApp Cloud API)."""

import hashlib
import hmac

import httpx

from app.core.config import get_settings
from app.services.channels.base import ChannelAPIError


class MetaAPIError(ChannelAPIError):
    """Raised when the Graph API rejects a request or can't be reached."""


def graph_url(path: str) -> str:
    s = get_settings()
    return f"{s.graph_api_base_url.rstrip('/')}/{s.graph_api_version}/{path.lstrip('/')}"


async def graph_request(
    method: str,
    path: str,
    token: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
    data: dict | None = None,
    files: dict | None = None,
    timeout: float = 30.0,
) -> dict:
    if not token:
        raise MetaAPIError("Access token is not configured")
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                graph_url(path),
                params=params,
                json=json,
                data=data,
                files=files,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        raise MetaAPIError(f"Could not reach the Meta API: {exc}") from exc
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code >= 400 or "error" in body:
        message = (body.get("error") or {}).get("message") or response.text[:200]
        raise MetaAPIError(f"Meta API error (HTTP {response.status_code}): {message}")
    return body


async def download(url: str, token: str | None = None) -> bytes:
    """Fetch a media file from a Meta CDN/media URL (WhatsApp's needs the token)."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise MetaAPIError(f"Media download failed: {exc}") from exc
    if response.status_code != 200:
        raise MetaAPIError(f"Media download failed (HTTP {response.status_code})")
    return response.content


def subscription_challenge(params, verify_token: str) -> str | None:
    """Answer Meta's webhook verification handshake: return hub.challenge if the token matches."""
    offered = params.get("hub.verify_token", "")
    if params.get("hub.mode") == "subscribe" and verify_token and hmac.compare_digest(offered, verify_token):
        return params.get("hub.challenge", "")
    return None


def verify_signature(app_secret: str, body: bytes, header: str) -> bool:
    """Check the `X-Hub-Signature-256: sha256=<hex>` header Meta signs webhooks with."""
    if not app_secret or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))
