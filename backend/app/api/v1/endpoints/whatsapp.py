import json
import logging
import mimetypes
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.services.channel_store import ChannelConfig, get_config
from app.services.channels.base import ChannelAPIError
from app.services.channels.meta import subscription_challenge, verify_signature
from app.services.channels.whatsapp import WhatsAppClient
from app.services.inbound import handle_delivery_update, handle_inbound_message
from app.services.media import save_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

CHANNEL = "whatsapp"
EXTENSIONS = {"audio/ogg": ".ogg", "image/jpeg": ".jpg", "image/webp": ".webp", "audio/mp4": ".m4a", "audio/aac": ".aac"}


@router.get("/webhook", response_class=PlainTextResponse)
async def whatsapp_verify(request: Request) -> str:
    """Meta's one-time handshake when the webhook is added in the App Dashboard."""
    config = await get_config(CHANNEL)
    challenge = subscription_challenge(request.query_params, config.get("verify_token") if config else "")
    if challenge is None:
        raise HTTPException(status_code=403, detail="Verification failed")
    return challenge


@router.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Receive WhatsApp Cloud API messages and statuses, verified by the app-secret HMAC."""
    config = await get_config(CHANNEL)
    if config is None:
        raise HTTPException(status_code=503, detail="WhatsApp is not connected")
    body = await request.body()
    if not verify_signature(config.get("app_secret"), body, request.headers.get("X-Hub-Signature-256", "")):
        raise HTTPException(status_code=400, detail="Invalid signature")
    payload = json.loads(body)
    if payload.get("object") == "whatsapp_business_account":
        background_tasks.add_task(_dispatch, payload, config, datetime.now(timezone.utc))
    return {"ok": True}


async def _dispatch(payload: dict, config: ChannelConfig, received_at: datetime) -> None:
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            # One business account can have several numbers; only handle the connected one.
            if (value.get("metadata") or {}).get("phone_number_id") != config.get("phone_number_id"):
                continue
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts", [])}
            for index, message in enumerate(value.get("messages", [])):
                try:
                    await _handle_message(message, names, config, received_at + timedelta(microseconds=index))
                except Exception:  # pragma: no cover - the webhook already returned 200
                    logger.exception("Failed to process WhatsApp message")
            for status in value.get("statuses", []):
                if status.get("status") in ("delivered", "read") and status.get("id"):
                    await handle_delivery_update(channel_message_id=status["id"], seen=status["status"] == "read")


def _extension(mime: str | None) -> str:
    base = (mime or "").split(";", 1)[0].strip().lower()
    return EXTENSIONS.get(base) or mimetypes.guess_extension(base) or ""


async def _handle_message(message: dict, names: dict, config: ChannelConfig, received_at: datetime) -> None:
    wa_id = message.get("from", "")
    message_type = message.get("type")
    kind, text, media_url = "text", None, None

    if message_type == "text":
        text = (message.get("text") or {}).get("body")
    elif message_type in ("image", "video", "audio", "document", "sticker"):
        media = message.get(message_type) or {}
        kind = {"image": "image", "video": "video", "document": "file", "sticker": "sticker"}.get(message_type)
        if message_type == "audio":
            kind = "voice" if media.get("voice") else "audio"
        text = media.get("caption") or (media.get("filename") if message_type == "document" else None)
        try:
            client = WhatsAppClient(config.get("access_token"), config.get("phone_number_id"))
            content, mime = await client.download_media(media.get("id", ""))
            file_name = media.get("filename") or f"{message_type}{_extension(mime or media.get('mime_type'))}"
            _, media_url = save_bytes(content, file_name)
        except ChannelAPIError:
            logger.warning("Failed to download WhatsApp %s from %s", kind, wa_id)
            text = text or f"[{kind} could not be downloaded]"
    elif message_type == "button":
        text = (message.get("button") or {}).get("text")
    elif message_type == "interactive":
        interactive = message.get("interactive") or {}
        text = (interactive.get("button_reply") or interactive.get("list_reply") or {}).get("title")
    elif message_type == "location":
        loc = message.get("location") or {}
        label = loc.get("name") or loc.get("address") or "Location"
        text = f"[{label}] https://maps.google.com/?q={loc.get('latitude')},{loc.get('longitude')}"
    elif message_type == "reaction":
        return  # an emoji reaction to an earlier message, not a new message
    text = text if (text or media_url) else "[unsupported message type]"

    await handle_inbound_message(
        channel=CHANNEL,
        contact_user_id=wa_id,
        contact_name=names.get(wa_id) or f"+{wa_id}",
        message_type=kind,
        text=text,
        media_url=media_url,
        channel_message_id=message.get("id"),
        payload=message,
        auto_reply=config.get("auto_reply") or None,
        received_at=received_at,
    )
