import hmac

import httpx

from app.core.config import get_settings
from app.services.channels.base import ChannelAPIError, ChannelSendResult


class TelegramAPIError(ChannelAPIError):
    """Raised when the Telegram Bot API returns ok: false."""


class TelegramClient:
    """Thin async wrapper around the Telegram Bot API."""

    channel = "telegram"

    def __init__(self, bot_token: str, base_url: str | None = None) -> None:
        self.bot_token = bot_token
        self.base_url = base_url or get_settings().telegram_api_base_url

    async def _post(self, method: str, payload: dict) -> dict:
        if not self.bot_token:
            raise TelegramAPIError("TELEGRAM_BOT_TOKEN is not configured")
        url = f"{self.base_url}/bot{self.bot_token}/{method}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            data = response.json()
        if not data.get("ok"):
            raise TelegramAPIError(f"Telegram API error (HTTP {response.status_code}): {data}")
        return data

    async def set_webhook(self, url: str) -> dict:
        settings = get_settings()
        payload: dict = {"url": url, "allowed_updates": ["message", "edited_message"]}
        if settings.telegram_webhook_secret:
            payload["secret_token"] = settings.telegram_webhook_secret
        return await self._post("setWebhook", payload)

    async def send_text(self, receiver: str, text: str) -> ChannelSendResult:
        data = await self._post("sendMessage", {"chat_id": receiver, "text": text})
        message_id = data.get("result", {}).get("message_id")
        return ChannelSendResult(message_id=str(message_id) if message_id is not None else None, raw=data)

    async def send_file(
        self,
        receiver: str,
        media_url: str,
        file_name: str,
        size: int,
        content_type: str | None = None,
    ) -> ChannelSendResult:
        # Telegram fetches the file itself when `document` is a public URL.
        data = await self._post(
            "sendDocument",
            {"chat_id": receiver, "document": media_url, "caption": file_name},
        )
        message_id = data.get("result", {}).get("message_id")
        return ChannelSendResult(message_id=str(message_id) if message_id is not None else None, raw=data)

    async def get_account_info(self) -> dict:
        return await self._post("getMe", {})

    async def get_file_url(self, file_id: str) -> str:
        """Resolve a Telegram `file_id` to a temporary, publicly-fetchable URL."""
        data = await self._post("getFile", {"file_id": file_id})
        file_path = data["result"]["file_path"]
        return f"{self.base_url}/file/bot{self.bot_token}/{file_path}"

    @staticmethod
    def verify_secret(configured_secret: str, header_value: str) -> bool:
        """Verify the `X-Telegram-Bot-Api-Secret-Token` header Telegram echoes back."""
        if not configured_secret:
            return False
        return hmac.compare_digest(configured_secret, header_value)


client = TelegramClient(get_settings().telegram_bot_token)
