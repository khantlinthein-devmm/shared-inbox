import hmac
from pathlib import PurePosixPath

import httpx

from app.core.config import get_settings
from app.services.channels.base import ChannelAPIError, ChannelSendResult
from app.services.media import OutboundMedia

PHOTO_MAX = 10 * 1024 * 1024
AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/mp4", "audio/m4a", "audio/x-m4a"}


class TelegramAPIError(ChannelAPIError):
    """Raised when the Telegram Bot API returns ok: false."""


def scoped_message_id(chat_id: str | int, message_id: int | None) -> str | None:
    # Telegram numbers messages per chat (every chat starts at 1), but
    # messages.channel_message_id is globally unique, so prefix the chat.
    return f"{chat_id}:{message_id}" if message_id is not None else None


def _method_for(media: OutboundMedia) -> tuple[str, str]:
    """Pick the Bot API method + form field; anything Telegram would reject goes as a document."""
    ctype = (media.content_type or "").lower()
    if media.kind == "voice":
        return "sendVoice", "voice"
    if media.kind == "image" and ctype != "image/gif" and media.size <= PHOTO_MAX:
        return "sendPhoto", "photo"
    if media.kind == "video" and ctype == "video/mp4":
        return "sendVideo", "video"
    if media.kind == "audio" and ctype in AUDIO_TYPES:
        return "sendAudio", "audio"
    return "sendDocument", "document"


class TelegramClient:
    """Thin async wrapper around the Telegram Bot API."""

    channel = "telegram"

    def __init__(self, bot_token: str, base_url: str | None = None) -> None:
        self.bot_token = bot_token
        self.base_url = base_url or get_settings().telegram_api_base_url

    def _url(self, method: str) -> str:
        if not self.bot_token:
            raise TelegramAPIError("TELEGRAM_BOT_TOKEN is not configured")
        return f"{self.base_url}/bot{self.bot_token}/{method}"

    @staticmethod
    def _check(response: httpx.Response) -> dict:
        data = response.json()
        if not data.get("ok"):
            raise TelegramAPIError(f"Telegram API error (HTTP {response.status_code}): {data}")
        return data

    async def _post(self, method: str, payload: dict) -> dict:
        url = self._url(method)
        async with httpx.AsyncClient(timeout=15.0) as client:
            return self._check(await client.post(url, json=payload))

    async def set_webhook(self, url: str) -> dict:
        settings = get_settings()
        payload: dict = {"url": url, "allowed_updates": ["message", "edited_message"]}
        if settings.telegram_webhook_secret:
            payload["secret_token"] = settings.telegram_webhook_secret
        return await self._post("setWebhook", payload)

    async def send_text(self, receiver: str, text: str) -> ChannelSendResult:
        data = await self._post("sendMessage", {"chat_id": receiver, "text": text})
        return self._result(data, receiver)

    async def send_media(self, receiver: str, media: OutboundMedia) -> ChannelSendResult:
        # Upload the bytes directly so sending works even when PUBLIC_BASE_URL
        # isn't reachable from the internet.
        method, field = _method_for(media)
        url = self._url(method)
        with media.path.open("rb") as fh:
            files = {field: (media.file_name, fh, media.content_type or "application/octet-stream")}
            async with httpx.AsyncClient(timeout=120.0) as client:
                data = self._check(await client.post(url, data={"chat_id": receiver}, files=files))
        return self._result(data, receiver)

    async def get_account_info(self) -> dict:
        return await self._post("getMe", {})

    async def download_file(self, file_id: str) -> tuple[bytes, str]:
        """Fetch an inbound file's bytes. Returns (content, telegram file name).

        The download URL embeds the bot token, so it must never be stored or
        handed to browsers - callers re-host the bytes under /uploads instead.
        """
        data = await self._post("getFile", {"file_id": file_id})
        file_path = data["result"]["file_path"]
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{self.base_url}/file/bot{self.bot_token}/{file_path}")
        if response.status_code != 200:
            raise TelegramAPIError(f"Telegram file download failed (HTTP {response.status_code})")
        return response.content, PurePosixPath(file_path).name

    @staticmethod
    def _result(data: dict, chat_id: str) -> ChannelSendResult:
        message_id = data.get("result", {}).get("message_id")
        return ChannelSendResult(message_id=scoped_message_id(chat_id, message_id), raw=data)

    @staticmethod
    def verify_secret(configured_secret: str, header_value: str) -> bool:
        """Verify the `X-Telegram-Bot-Api-Secret-Token` header Telegram echoes back."""
        if not configured_secret:
            return False
        return hmac.compare_digest(configured_secret, header_value)


client = TelegramClient(get_settings().telegram_bot_token)
