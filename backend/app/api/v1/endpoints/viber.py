import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.core.config import get_settings
from app.schemas.viber import ViberWebhookEvent
from app.services.channels.viber import ViberClient
from app.services.inbound import handle_delivery_update, handle_inbound_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/viber", tags=["viber"])

CHANNEL = "viber"


@router.post("/webhook")
async def viber_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Receive webhook callbacks from Viber.

    Signature: `X-Viber-Content-Signature` (HMAC-SHA256 of the raw body using the
    bot auth token as the key). See https://developers.viber.com/docs/api/rest-bot-api/#callbacks
    """
    settings = get_settings()
    body = await request.body()
    signature = request.headers.get("X-Viber-Content-Signature", "")

    if not settings.viber_auth_token:
        raise HTTPException(status_code=500, detail="VIBER_AUTH_TOKEN is not configured")
    if not ViberClient.verify_signature(settings.viber_auth_token, body, signature):
        raise HTTPException(status_code=400, detail="Invalid Viber signature")

    event = ViberWebhookEvent.model_validate_json(body)
    background_tasks.add_task(_dispatch_event, event)
    # Viber expects a fast ack; real work runs in a background task.
    return {"status": 0}


async def _dispatch_event(event: ViberWebhookEvent) -> None:
    try:
        if event.event == "message" and event.message is not None:
            await _handle_message(event)
        elif event.event in ("delivered", "seen"):
            await _handle_delivery_update(event, seen=event.event == "seen")
        # conversation_started / subscribed / unsubscribed are intentionally ignored
    except Exception:  # pragma: no cover - the webhook already returned 200
        logger.exception("Failed to process Viber event: %s", event.event)


async def _handle_message(event: ViberWebhookEvent) -> None:
    if event.sender is None or event.message is None:
        return

    settings = get_settings()
    await handle_inbound_message(
        channel=CHANNEL,
        contact_user_id=event.sender.id,
        contact_name=event.sender.name or "Viber User",
        contact_avatar=event.sender.avatar,
        message_type=event.message.type or "text",
        text=event.message.text,
        media_url=event.message.media,
        channel_message_id=str(event.message_token) if event.message_token else None,
        payload=event.message.model_dump(exclude_none=True),
        auto_reply=settings.viber_auto_reply or None,
    )


async def _handle_delivery_update(event: ViberWebhookEvent, *, seen: bool) -> None:
    if event.message_token is None:
        return
    await handle_delivery_update(channel_message_id=str(event.message_token), seen=seen)
