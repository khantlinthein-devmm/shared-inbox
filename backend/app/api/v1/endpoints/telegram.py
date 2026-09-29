import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.schemas.telegram import TelegramMessage, TelegramUpdate
from app.services.channel_store import ChannelConfig, get_config
from app.services.channels.base import ChannelAPIError
from app.services.channels.telegram import TelegramClient, scoped_message_id
from app.services.inbound import handle_inbound_message
from app.services.media import save_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

CHANNEL = "telegram"


@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Receive webhook callbacks from Telegram.

    Verified via the `X-Telegram-Bot-Api-Secret-Token` header, which Telegram
    echoes back on every call once set via `setWebhook`.
    See https://core.telegram.org/bots/api#setwebhook
    """
    config = await get_config(CHANNEL)
    if config is None:
        raise HTTPException(status_code=503, detail="Telegram is not connected")

    secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not TelegramClient.verify_secret(config.get("webhook_secret"), secret_header):
        raise HTTPException(status_code=400, detail="Invalid Telegram webhook secret")

    body = await request.body()
    update = TelegramUpdate.model_validate_json(body)
    background_tasks.add_task(_dispatch_update, update, config, datetime.now(timezone.utc))
    # Telegram just needs a fast 200 ack; real work runs in the background.
    return {"ok": True}


async def _dispatch_update(update: TelegramUpdate, config: ChannelConfig, received_at: datetime) -> None:
    try:
        if update.message is not None:
            await _handle_message(update.message, config, received_at)
        # edited_message is intentionally ignored - no edit support yet
    except Exception:  # pragma: no cover - the webhook already returned 200
        logger.exception("Failed to process Telegram update: %s", update.update_id)


def _pick_media(message: TelegramMessage) -> tuple[str, str, str | None] | None:
    """Return (message_type, file_id, file-name hint) for the message's media, if any."""
    if message.photo:
        # Telegram sends several sizes; the last one is the largest.
        return "image", message.photo[-1].file_id, None
    # An animation (GIF) also carries a `document` copy, so check it first.
    for field, kind in (("animation", "video"), ("video", "video"), ("video_note", "video"), ("voice", "voice"), ("audio", "audio")):
        media = getattr(message, field)
        if media is not None:
            return kind, media.file_id, media.file_name
    if message.sticker is not None and not message.sticker.is_animated:
        return "sticker", message.sticker.file_id, None
    if message.document is not None:
        return "file", message.document.file_id, message.document.file_name
    return None


def _playable_name(name: str) -> str:
    # Telegram names voice notes *.oga; browsers and our static server know *.ogg.
    return name[:-4] + ".ogg" if name.lower().endswith(".oga") else name


async def _handle_message(message: TelegramMessage, config: ChannelConfig, received_at: datetime) -> None:
    sender = message.from_user
    contact_name = "Telegram User"
    if sender is not None:
        contact_name = " ".join(filter(None, [sender.first_name, sender.last_name])) or sender.username or contact_name

    text = message.text or message.caption
    message_type = "text"
    media_url: str | None = None

    picked = _pick_media(message)
    if picked is not None:
        message_type, file_id, name_hint = picked
        if message_type in ("file", "audio"):
            text = text or name_hint
        try:
            content, tg_name = await TelegramClient(config.get("bot_token")).download_file(file_id)
            _, media_url = save_bytes(content, _playable_name(name_hint or tg_name))
        except ChannelAPIError:
            logger.warning("Failed to download Telegram %s for chat %s", message_type, message.chat.id)
            text = text or f"[{message_type} could not be downloaded]"
    elif message.sticker is not None:
        # Animated (.tgs / Lottie) stickers can't be shown in a browser; keep the emoji.
        message_type = "sticker"
        text = message.sticker.emoji or "[sticker]"
    elif not text:
        text = "[unsupported message type]"

    await handle_inbound_message(
        channel=CHANNEL,
        contact_user_id=str(message.chat.id),
        contact_name=contact_name,
        message_type=message_type,
        text=text,
        media_url=media_url,
        channel_message_id=scoped_message_id(message.chat.id, message.message_id),
        payload=message.model_dump(mode="json", exclude_none=True, by_alias=True),
        auto_reply=config.get("auto_reply") or None,
        received_at=received_at,
    )
