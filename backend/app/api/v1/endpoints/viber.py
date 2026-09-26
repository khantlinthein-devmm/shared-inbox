import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Conversation, ConversationStatus, Message, MessageSender, MessageStatus
from app.schemas.message import MessageOut
from app.schemas.viber import ViberWebhookEvent
from app.services.serializers import serialize_conversation
from app.services.viber_client import ViberAPIError, ViberClient, client as viber_client
from app.services.ws_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/viber", tags=["viber"])


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
    if event.sender is None:
        return

    settings = get_settings()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        conversation = await db.scalar(
            select(Conversation).where(Conversation.contact_user_id == event.sender.id)
        )
        if conversation is None:
            conversation = Conversation(
                contact_user_id=event.sender.id,
                contact_name=event.sender.name or "Viber User",
                contact_avatar=event.sender.avatar,
                status=ConversationStatus.unassigned.value,
                created_at=now,
                updated_at=now,
            )
            db.add(conversation)
            await db.flush()

        inbound = Message(
            conversation_id=conversation.id,
            sender=MessageSender.contact.value,
            message_type=event.message.type or "text",
            text=event.message.text,
            media_url=event.message.media,
            status=MessageStatus.received.value,
            payload=event.message.model_dump(exclude_none=True),
            viber_message_token=str(event.message_token) if event.message_token else None,
            created_at=now,
        )
        db.add(inbound)

        if settings.viber_auto_reply:
            try:
                await viber_client.send_text(event.sender.id, settings.viber_auto_reply)
                db.add(
                    Message(
                        conversation_id=conversation.id,
                        sender=MessageSender.agent.value,
                        message_type="text",
                        text=settings.viber_auto_reply,
                        status=MessageStatus.sent.value,
                        created_at=now,
                    )
                )
            except ViberAPIError:
                logger.warning("Auto-reply failed for %s", event.sender.id)

        await db.commit()
        conversation_id = conversation.id
        inbound_id = inbound.id
        created_at = inbound.created_at

    async with SessionLocal() as db:
        conversation_data = await serialize_conversation(db, conversation_id)

    inbound_dict = {
        "message": MessageOut.model_validate(
            {
                "id": inbound_id,
                "conversation_id": conversation_id,
                "sender": MessageSender.contact.value,
                "sender_name": event.sender.name or "Viber User",
                "message_type": event.message.type or "text",
                "text": event.message.text,
                "media_url": event.message.media,
                "status": MessageStatus.received.value,
                "created_at": created_at.isoformat(),
            }
        ).model_dump(mode="json"),
        "conversation": conversation_data,
    }
    await manager.broadcast_to_agents({"type": "message:new", "payload": inbound_dict})


async def _handle_delivery_update(event: ViberWebhookEvent, *, seen: bool) -> None:
    token = str(event.message_token) if event.message_token else None
    if token is None:
        return

    status_value = MessageStatus.seen.value if seen else MessageStatus.delivered.value
    async with SessionLocal() as db:
        message = await db.scalar(select(Message).where(Message.viber_message_token == token))
        if message is None or message.status == status_value:
            return
        message.status = status_value
        await db.commit()

        await manager.broadcast_to_agents(
            {
                "type": "message:status",
                "payload": {
                    "message_id": message.id,
                    "conversation_id": message.conversation_id,
                    "status": status_value,
                },
            }
        )