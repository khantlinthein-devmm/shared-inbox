import json

from app.services.channels.base import ChannelAPIError, ChannelSendResult
from app.services.channels.meta import graph_request
from app.services.media import OutboundMedia

# Messenger attachment types; everything else (documents, etc.) goes as "file".
ATTACHMENT_TYPES = {"image": "image", "video": "video", "audio": "audio", "voice": "audio"}


class MessengerClient:
    """Facebook Page messaging through the Graph API (Send API)."""

    channel = "messenger"

    def __init__(self, page_token: str) -> None:
        self.page_token = page_token

    async def get_account_info(self) -> dict:
        return await graph_request("GET", "me", self.page_token, params={"fields": "id,name"})

    async def subscribe_page(self, page_id: str) -> dict:
        """Subscribe the app to this Page's message, delivery and read events."""
        return await graph_request(
            "POST",
            f"{page_id}/subscribed_apps",
            self.page_token,
            params={"subscribed_fields": "messages,message_deliveries,message_reads"},
        )

    async def send_text(self, receiver: str, text: str) -> ChannelSendResult:
        data = await graph_request(
            "POST",
            "me/messages",
            self.page_token,
            json={"recipient": {"id": receiver}, "messaging_type": "RESPONSE", "message": {"text": text}},
        )
        return ChannelSendResult(message_id=data.get("message_id"), raw=data)

    async def send_media(self, receiver: str, media: OutboundMedia) -> ChannelSendResult:
        kind = ATTACHMENT_TYPES.get(media.kind, "file")
        message = {"attachment": {"type": kind, "payload": {"is_reusable": False}}}
        with media.path.open("rb") as fh:
            data = await graph_request(
                "POST",
                "me/messages",
                self.page_token,
                data={
                    "recipient": json.dumps({"id": receiver}),
                    "messaging_type": "RESPONSE",
                    "message": json.dumps(message),
                },
                files={"filedata": (media.file_name, fh, media.content_type or "application/octet-stream")},
                timeout=120.0,
            )
        return ChannelSendResult(message_id=data.get("message_id"), raw=data)

    async def get_profile_name(self, psid: str) -> str | None:
        # Needs the "Business Asset User Profile Access" feature; many apps don't have it.
        try:
            data = await graph_request("GET", psid, self.page_token, params={"fields": "first_name,last_name"})
        except ChannelAPIError:
            return None
        return " ".join(filter(None, [data.get("first_name"), data.get("last_name")])) or None
