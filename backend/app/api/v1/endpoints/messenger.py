import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.services.channel_store import ChannelConfig, get_config
from app.services.channels.base import ChannelAPIError
from app.services.channels.messenger import MessengerClient
from app.services.channels.meta import download, subscription_challenge, verify_signature
from app.services.inbound import handle_delivery_update, handle_inbound_message, mark_seen_until
from app.services.media import save_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messenger", tags=["messenger"])

CHANNEL = "messenger"
ATTACHMENT_KINDS = {"image": "image", "video": "video", "audio": "audio", "file": "file"}
_profile_names: dict[str, str] = {}


@router.get("/webhook", response_class=PlainTextResponse)
async def messenger_verify(request: Request) -> str:
    """Meta's one-time handshake when the webhook is added in the App Dashboard."""
    config = await get_config(CHANNEL)
    challenge = subscription_challenge(request.query_params, config.get("verify_token") if config else "")
    if challenge is None:
        raise HTTPException(status_code=403, detail="Verification failed")
    return challenge


@router.post("/webhook")
async def messenger_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Receive Page messaging events, verified by the X-Hub-Signature-256 app-secret HMAC."""
    config = await get_config(CHANNEL)
    if config is None:
        raise HTTPException(status_code=503, detail="Messenger is not connected")
    body = await request.body()
    if not verify_signature(config.get("app_secret"), body, request.headers.get("X-Hub-Signature-256", "")):
        raise HTTPException(status_code=400, detail="Invalid signature")
    payload = json.loads(body)
    if payload.get("object") == "page":
        background_tasks.add_task(_dispatch, payload, config, datetime.now(timezone.utc))
    return {"ok": True}


async def _dispatch(payload: dict, config: ChannelConfig, received_at: datetime) -> None:
    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            try:
                await _handle_event(event, config, received_at)
            except Exception:  # pragma: no cover - the webhook already returned 200
                logger.exception("Failed to process Messenger event")


async def _handle_event(event: dict, config: ChannelConfig, received_at: datetime) -> None:
    psid = (event.get("sender") or {}).get("id")
    if not psid:
        return
    if "message" in event:
        if not event["message"].get("is_echo"):
            await _handle_message(psid, event["message"], config, received_at)
    elif "delivery" in event:
        for mid in event["delivery"].get("mids") or []:
            await handle_delivery_update(channel_message_id=mid, seen=False)
    elif "read" in event and event["read"].get("watermark"):
        # Messenger reports reads as "everything up to this time".
        until = datetime.fromtimestamp(event["read"]["watermark"] / 1000, tz=timezone.utc)
        await mark_seen_until(channel=CHANNEL, contact_user_id=psid, until=until)


async def _contact_name(client: MessengerClient, psid: str) -> str:
    if psid not in _profile_names:
        _profile_names[psid] = await client.get_profile_name(psid) or "Messenger User"
    return _profile_names[psid]


async def _handle_message(psid: str, message: dict, config: ChannelConfig, received_at: datetime) -> None:
    client = MessengerClient(config.get("page_access_token"))
    name = await _contact_name(client, psid)

    # One Messenger message can carry text plus several attachments; store each separately.
    items: list[tuple[str, str | None, str | None]] = []
    if message.get("text"):
        items.append(("text", message["text"], None))
    for attachment in message.get("attachments") or []:
        payload = attachment.get("payload") or {}
        kind = "sticker" if payload.get("sticker_id") else ATTACHMENT_KINDS.get(attachment.get("type", ""))
        url = payload.get("url")
        if kind is None or not url:
            items.append(("text", attachment.get("title") or f"[{attachment.get('type', 'unsupported')} attachment]", None))
            continue
        try:
            content = await download(url)
            _, media_url = save_bytes(content, url.split("?", 1)[0].rsplit("/", 1)[-1] or kind)
            items.append((kind, None, media_url))
        except ChannelAPIError:
            logger.warning("Failed to download Messenger %s from %s", kind, psid)
            items.append((kind, f"[{kind} could not be downloaded]", None))
    if not items:
        items.append(("text", "[unsupported message type]", None))

    mid = message.get("mid")
    for index, (kind, text, media_url) in enumerate(items):
        await handle_inbound_message(
            channel=CHANNEL,
            contact_user_id=psid,
            contact_name=name,
            message_type=kind,
            text=text,
            media_url=media_url,
            channel_message_id=(mid if index == 0 else f"{mid}:{index}") if mid else None,
            payload=message if index == 0 else None,
            auto_reply=(config.get("auto_reply") or None) if index == 0 else None,
            received_at=received_at + timedelta(microseconds=index),
        )
