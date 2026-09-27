import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.core.config import get_settings
from app.schemas.telegram import TelegramMessage, TelegramUpdate
from app.services.channels.base import ChannelAPIError
from app.services.channels.telegram import client as telegram_client
from app.services.inbound import handle_inbound_message

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
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN is not configured")

    secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not telegram_client.verify_secret(settings.telegram_webhook_secret, secret_header):
        raise HTTPException(status_code=400, detail="Invalid Telegram webhook secret")

    body = await request.body()
    update = TelegramUpdate.model_validate_json(body)
    background_tasks.add_task(_dispatch_update, update)
    # Telegram just needs a fast 200 ack; real work runs in the background.
    return {"ok": True}


async def _dispatch_update(update: TelegramUpdate) -> None:
    try:
        if update.message is not None:
            await _handle_message(update.message)
        # edited_message is intentionally ignored - no edit support yet
    except Exception:  # pragma: no cover - the webhook already returned 200
        logger.exception("Failed to process Telegram update: %s", update.update_id)


async def _handle_message(message: TelegramMessage) -> None:
    settings = get_settings()
    sender = message.from_user
    contact_name = "Telegram User"
    if sender is not None:
        contact_name = " ".join(filter(None, [sender.first_name, sender.last_name])) or sender.username or contact_name

    message_type = "text"
    text = message.text or message.caption
    media_url: str | None = None

    try:
        if message.document is not None:
            message_type = "file"
            media_url = await telegram_client.get_file_url(message.document.file_id)
            text = text or message.document.file_name
        elif message.photo:
            message_type = "image"
            # Telegram sends multiple sizes; the last one is the largest.
            media_url = await telegram_client.get_file_url(message.photo[-1].file_id)
    except ChannelAPIError:
        logger.warning("Failed to resolve Telegram media for chat %s", message.chat.id)

    await handle_inbound_message(
        channel=CHANNEL,
        contact_user_id=str(message.chat.id),
        contact_name=contact_name,
        message_type=message_type,
        text=text,
        media_url=media_url,
        channel_message_id=str(message.message_id),
        payload=message.model_dump(mode="json", exclude_none=True, by_alias=True),
        auto_reply=settings.telegram_auto_reply or None,
    )
