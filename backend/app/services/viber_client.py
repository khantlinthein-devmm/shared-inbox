import hashlib
import hmac
import os

import httpx

from app.core.config import get_settings

# Overridable so tests / smoke runs can point at a mock Viber API.
VIBER_API_BASE_URL = os.getenv("VIBER_API_BASE_URL", "https://chatapi.viber.com/pa")


class ViberAPIError(RuntimeError):
    """Raised when the Viber Public Account API returns a non-zero status."""


class ViberClient:
    """Thin async wrapper around the Viber Public Account REST API."""

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
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{self.base_url}{path}", json=payload, headers=self._headers())
            data = response.json()
        if response.status_code != 200 or data.get("status") != 0:
            raise ViberAPIError(f"Viber API error (HTTP {response.status_code}): {data}")
        return data

    async def set_webhook(self, url: str, events: list[str]) -> dict:
        return await self._post("/set_webhook", {"url": url, "event_types": events, "send_name": True})

    async def remove_webhook(self) -> dict:
        return await self._post("/set_webhook", {"url": ""})

    async def send_text(self, receiver: str, text: str) -> dict:
        return await self._post("/send_message", {"receiver": receiver, "type": "text", "text": text})

    async def send_message(self, payload: dict) -> dict:
        return await self._post("/send_message", payload)

    async def get_account_info(self) -> dict:
        return await self._post("/get_account_info", {})

    @staticmethod
    def verify_signature(secret: str, body: bytes, signature: str) -> bool:
        """Verify the `X-Viber-Content-Signature` HMAC-SHA256 header sent by Viber."""
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


client = ViberClient(get_settings().viber_auth_token)