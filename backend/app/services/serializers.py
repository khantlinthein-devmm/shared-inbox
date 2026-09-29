"""Helpers that turn ORM rows into JSON-ready dicts.

Keeping serialization here (rather than relying on lazy ORM access) avoids
`MissingGreenlet` async lazy-load errors after a session is committed/closed.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AgentNote, Conversation, Message


MEDIA_LABELS = {
    "image": "[Photo]",
    "picture": "[Photo]",
    "video": "[Video]",
    "voice": "[Voice message]",
    "audio": "[Audio]",
    "sticker": "[Sticker]",
    "file": "[File]",
    "voice_call": "[Voice call]",
    "video_call": "[Video call]",
}


def preview_text(message: Message) -> str | None:
    # Call invites carry a long link as text; the label reads better in the list.
    if message.message_type.endswith("_call"):
        return MEDIA_LABELS.get(message.message_type)
    if message.text:
        return message.text
    return MEDIA_LABELS.get(message.message_type)


def conversation_to_dict(conversation: Conversation) -> dict:
    messages = sorted(conversation.messages or [], key=lambda m: m.created_at)
    last = messages[-1] if messages else None
    assigned = conversation.assigned_to
    return {
        "id": conversation.id,
        "channel": conversation.channel,
        "contact_user_id": conversation.contact_user_id,
        "contact_name": conversation.contact_name,
        "contact_avatar": conversation.contact_avatar,
        "status": conversation.status,
        "unread_count": conversation.unread_count,
        "assigned_to_id": conversation.assigned_to_id,
        "assigned_to_email": assigned.email if assigned else None,
        "assigned_to_full_name": assigned.full_name if assigned else None,
        "last_message": preview_text(last) if last else None,
        "last_message_at": last.created_at.isoformat() if last else None,
        "message_count": len(messages),
    }


def message_to_dict(message: Message, conversation: Conversation | None = None) -> dict:
    owner_name = conversation.contact_name if conversation else None
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender": message.sender,
        "sender_id": message.sender_id,
        "sender_name": owner_name if message.sender == "contact" else None,
        "message_type": message.message_type,
        "text": message.text,
        "media_url": message.media_url,
        "status": message.status,
        "created_at": message.created_at.isoformat(),
    }


def note_to_dict(note: AgentNote) -> dict:
    return {
        "id": note.id,
        "conversation_id": note.conversation_id,
        "author_id": note.author_id,
        "author_name": note.author.full_name if note.author else None,
        "content": note.content,
        "created_at": note.created_at.isoformat(),
    }


async def serialize_conversation(db: AsyncSession, conversation_id: int) -> dict:
    """Fetch a conversation (messages + assignee eager-loaded) and serialize it."""
    # populate_existing: the request's session may already hold this conversation
    # with a message list loaded before the message just added.
    conversation = await db.get(
        Conversation,
        conversation_id,
        options=[
            selectinload(Conversation.messages),
            selectinload(Conversation.assigned_to),
        ],
        populate_existing=True,
    )
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    return conversation_to_dict(conversation)