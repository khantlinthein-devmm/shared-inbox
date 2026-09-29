from app.services.channels.base import ChannelSendResult
from app.services.channels.meta import MetaAPIError, download, graph_request
from app.services.media import OutboundMedia

# Formats WhatsApp accepts per message type; anything else is sent as a document.
IMAGE_TYPES = {"image/jpeg", "image/png"}
VIDEO_TYPES = {"video/mp4", "video/3gpp"}
AUDIO_TYPES = {"audio/ogg", "audio/mpeg", "audio/aac", "audio/mp4", "audio/amr"}


class WhatsAppClient:
    """WhatsApp Business through Meta's Cloud API."""

    channel = "whatsapp"

    def __init__(self, access_token: str, phone_number_id: str) -> None:
        self.token = access_token
        self.phone_number_id = phone_number_id

    async def get_account_info(self) -> dict:
        return await graph_request(
            "GET", self.phone_number_id, self.token, params={"fields": "display_phone_number,verified_name"}
        )

    async def _send(self, to: str, message_type: str, body: dict) -> ChannelSendResult:
        data = await graph_request(
            "POST",
            f"{self.phone_number_id}/messages",
            self.token,
            json={"messaging_product": "whatsapp", "recipient_type": "individual", "to": to, "type": message_type, message_type: body},
        )
        message_id = (data.get("messages") or [{}])[0].get("id")
        return ChannelSendResult(message_id=message_id, raw=data)

    async def send_text(self, receiver: str, text: str) -> ChannelSendResult:
        return await self._send(receiver, "text", {"body": text, "preview_url": True})

    async def send_media(self, receiver: str, media: OutboundMedia) -> ChannelSendResult:
        ctype = (media.content_type or "application/octet-stream").split(";")[0].strip().lower()
        if media.kind == "image" and ctype in IMAGE_TYPES:
            message_type = "image"
        elif media.kind == "video" and ctype in VIDEO_TYPES:
            message_type = "video"
        elif media.kind in ("voice", "audio") and ctype in AUDIO_TYPES:
            message_type = "audio"  # OGG/Opus shows as a voice note
        else:
            message_type = "document"
        with media.path.open("rb") as fh:
            uploaded = await graph_request(
                "POST",
                f"{self.phone_number_id}/media",
                self.token,
                data={"messaging_product": "whatsapp", "type": ctype},
                files={"file": (media.file_name, fh, ctype)},
                timeout=120.0,
            )
        body = {"id": uploaded["id"]}
        if message_type == "document":
            body["filename"] = media.file_name
        return await self._send(receiver, message_type, body)

    async def download_media(self, media_id: str) -> tuple[bytes, str | None]:
        meta = await graph_request("GET", media_id, self.token)
        if not meta.get("url"):
            raise MetaAPIError("WhatsApp media has no download URL")
        return await download(meta["url"], self.token), meta.get("mime_type")
