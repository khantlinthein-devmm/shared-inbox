import hashlib
import hmac
import os

import httpx

from app.core.config import get_settings
from app.services.channels.base import ChannelAPIError, ChannelSendResult
from app.services.media import OutboundMedia

# Overridable so tests / smoke runs can point at a mock Viber API.
VIBER_API_BASE_URL = os.getenv("VIBER_API_BASE_URL", "https://chatapi.viber.com/pa")

VIBER_PICTURE_EXT = {".jpg", ".jpeg", ".png", ".gif"}
VIBER_PICTURE_MAX = 1 * 1024 * 1024
VIBER_VIDEO_MAX = 26 * 1024 * 1024


class ViberAPIError(ChannelAPIError):
    """Raised when the Viber Public Account API returns a non-zero status."""


class ViberClient:
    """Thin async wrapper around the Viber Public Account REST API."""

    channel = "viber"

    def __init__(self, auth_token: str, base_url: str = VIBER_API_BASE_URL) -> None:
        self.auth_token = auth_token
        self.base_url = base_url

    def _headers(self) -> dict[str, str]:
        return {
            "X-Viber-Auth-Token": self.auth_token,
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, payload: dict) -> dict:
        if not self.auth_token:
            raise ViberAPIError("VIBER_AUTH_TOKEN is not configured")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(f"{self.base_url}{path}", json=payload, headers=self._headers())
            data = response.json()
        except httpx.HTTPError as exc:
            raise ViberAPIError(f"Could not reach the Viber API: {exc}") from exc
        except ValueError:
            raise ViberAPIError(f"Unexpected Viber response (HTTP {response.status_code})") from None
        if response.status_code != 200 or data.get("status") != 0:
            raise ViberAPIError(f"Viber API error (HTTP {response.status_code}): {data}")
        return data

    async def set_webhook(self, url: str, events: list[str] | None = None) -> dict:
        settings = get_settings()
        return await self._post(
            "/set_webhook",
            {"url": url, "event_types": events or settings.viber_webhook_events, "send_name": True},
        )

    async def remove_webhook(self) -> dict:
        return await self._post("/set_webhook", {"url": ""})

    async def send_text(self, receiver: str, text: str) -> ChannelSendResult:
        data = await self._post("/send_message", {"receiver": receiver, "type": "text", "text": text})
        token = data.get("message_token")
        return ChannelSendResult(message_id=str(token) if token else None, raw=data)

    async def send_message(self, payload: dict) -> dict:
        return await self._post("/send_message", payload)

    async def send_media(self, receiver: str, media: OutboundMedia) -> ChannelSendResult:
        # Viber fetches media from a public URL. Pictures and videos have strict
        # format/size rules; anything outside them (including voice) goes as a file.
        suffix = media.path.suffix.lower()
        if media.kind == "image" and suffix in VIBER_PICTURE_EXT and media.size <= VIBER_PICTURE_MAX:
            payload = {"type": "picture", "media": media.url, "text": ""}
        elif media.kind == "video" and suffix == ".mp4" and media.size <= VIBER_VIDEO_MAX:
            payload = {"type": "video", "media": media.url, "size": media.size}
        else:
            payload = {"type": "file", "media": media.url, "size": media.size, "file_name": media.file_name}
        data = await self.send_message({"receiver": receiver, **payload})
        token = data.get("message_token")
        return ChannelSendResult(message_id=str(token) if token else None, raw=data)

    async def get_account_info(self) -> dict:
        return await self._post("/get_account_info", {})

    @staticmethod
    def verify_signature(secret: str, body: bytes, signature: str) -> bool:
        """Verify the `X-Viber-Content-Signature` HMAC-SHA256 header sent by Viber."""
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

