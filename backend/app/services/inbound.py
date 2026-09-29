"""Channel-agnostic handling of inbound contact messages and delivery updates.

Every channel's webhook endpoint normalizes its provider-specific payload and
calls into these two functions, so the find-or-create-conversation / persist /
broadcast logic is written once and shared across Viber, Telegram, etc.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.core.database import SessionLocal
from app.models import Conversation, ConversationStatus, Message, MessageSender, MessageStatus
from app.schemas.message import MessageOut
from app.services.channels.base import ChannelAPIError
from app.services.channels.registry import get_channel_client
from app.services.serializers import serialize_conversation
from app.services.ws_manager import manager

logger = logging.getLogger(__name__)


async def handle_inbound_message(
    *,
    channel: str,
    contact_user_id: str,
    contact_name: str,
    contact_avatar: str | None = None,
    message_type: str = "text",
    text: str | None = None,
    media_url: str | None = None,
    channel_message_id: str | None = None,
    payload: dict | None = None,
    auto_reply: str | None = None,
    received_at: datetime | None = None,
) -> None:
    """Persist an inbound contact message, creating its conversation if needed,
    optionally send a configured auto-reply, then broadcast to agent dashboards.

    `received_at` should be taken when the webhook arrived, so a message whose
    media took a while to download still sorts before messages sent after it.
    """
    now = received_at or datetime.now(timezone.utc)

    async with SessionLocal() as db:
        conversation = await db.scalar(
            select(Conversation).where(
                Conversation.channel == channel,
                Conversation.contact_user_id == contact_user_id,
            )
        )
        if conversation is None:
            conversation = Conversation(
                channel=channel,
                contact_user_id=contact_user_id,
                contact_name=contact_name or "Contact",
                contact_avatar=contact_avatar,
                status=ConversationStatus.unassigned.value,
                created_at=now,
                updated_at=now,
            )
            db.add(conversation)
            await db.flush()
            seen_ids: list[int] = []
        else:
            conversation.updated_at = now
            # A reply means the contact has seen what the agents sent before it.
            # This is the only read signal on Telegram (bots get no read receipts)
            # and fills gaps on Viber, whose seen callbacks can be missed.
            seen_ids = list(
                (
                    await db.scalars(
                        update(Message)
                        .where(
                            Message.conversation_id == conversation.id,
                            Message.sender == MessageSender.agent.value,
                            Message.status.in_((MessageStatus.sent.value, MessageStatus.delivered.value)),
                            Message.created_at <= now,
                        )
                        .values(status=MessageStatus.seen.value)
                        .returning(Message.id)
                    )
                ).all()
            )

        inbound = Message(
            conversation_id=conversation.id,
            sender=MessageSender.contact.value,
            message_type=message_type,
            text=text,
            media_url=media_url,
            status=MessageStatus.received.value,
            payload=payload,
            channel_message_id=channel_message_id,
            created_at=now,
        )
        db.add(inbound)

        if auto_reply:
            try:
                client = get_channel_client(channel)
                await client.send_text(contact_user_id, auto_reply)
                db.add(
                    Message(
                        conversation_id=conversation.id,
                        sender=MessageSender.agent.value,
                        message_type="text",
                        text=auto_reply,
                        status=MessageStatus.sent.value,
                        created_at=now,
                    )
                )
            except ChannelAPIError:
                logger.warning("Auto-reply failed for %s contact %s", channel, contact_user_id)

        await db.commit()
        conversation_id = conversation.id
        inbound_id = inbound.id
        created_at = inbound.created_at
        resolved_contact_name = conversation.contact_name

    async with SessionLocal() as db:
        conversation_data = await serialize_conversation(db, conversation_id)

    inbound_dict = {
        "message": MessageOut.model_validate(
            {
                "id": inbound_id,
                "conversation_id": conversation_id,
                "sender": MessageSender.contact.value,
                "sender_name": resolved_contact_name,
                "message_type": message_type,
                "text": text,
                "media_url": media_url,
                "status": MessageStatus.received.value,
                "created_at": created_at.isoformat(),
            }
        ).model_dump(mode="json"),
        "conversation": conversation_data,
    }
    await manager.broadcast_to_agents({"type": "message:new", "payload": inbound_dict})
    for message_id in seen_ids:
        await _broadcast_status(message_id, conversation_id, MessageStatus.seen.value)


_STATUS_RANK = {MessageStatus.sent.value: 0, MessageStatus.delivered.value: 1, MessageStatus.seen.value: 2}


async def handle_delivery_update(*, channel_message_id: str, seen: bool) -> None:
    """Advance a previously-sent message's status (delivered/seen) and broadcast it."""
    status_value = MessageStatus.seen.value if seen else MessageStatus.delivered.value
    async with SessionLocal() as db:
        message = await db.scalar(select(Message).where(Message.channel_message_id == channel_message_id))
        # Callbacks can arrive out of order; a late "delivered" must not undo "seen".
        if message is None or _STATUS_RANK.get(message.status, -1) >= _STATUS_RANK[status_value]:
            return
        message.status = status_value
        await db.commit()
        await _broadcast_status(message.id, message.conversation_id, status_value)


async def _broadcast_status(message_id: int, conversation_id: int, status: str) -> None:
    await manager.broadcast_to_agents(
        {
            "type": "message:status",
            "payload": {"message_id": message_id, "conversation_id": conversation_id, "status": status},
        }
    )
