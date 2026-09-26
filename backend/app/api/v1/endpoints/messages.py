import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Conversation, Message, MessageSender, MessageStatus, User
from app.schemas.message import MessageCreate, MessageOut
from app.services.serializers import message_to_dict, serialize_conversation
from app.services.viber_client import ViberAPIError, client as viber_client
from app.services.ws_manager import manager

router = APIRouter(prefix="/conversations", tags=["messages"])

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB (Viber file limit for bots)
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MessageOut]:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    rows = (
        await db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
    ).all()
    return [MessageOut.model_validate(message_to_dict(m, conversation)) for m in rows]


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def create_agent_message(
    conversation_id: int,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageOut:
    """Send a reply from an agent to the Viber contact and store it."""
    conversation = await db.get(
        Conversation,
        conversation_id,
        options=[selectinload(Conversation.messages)],
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message text is required")

    try:
        viber_response = await viber_client.send_text(conversation.contact_user_id, text)
    except ViberAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    token = viber_response.get("message_token")
    message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.agent.value,
        sender_id=user.id,
        message_type="text",
        text=text,
        status=MessageStatus.sent.value,
        viber_message_token=str(token) if token else None,
        created_at=datetime.now(timezone.utc),
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(message)
    await db.commit()

    out = MessageOut.model_validate(message_to_dict(message, conversation))
    conversation_data = await serialize_conversation(db, conversation.id)
    await manager.broadcast_to_agents(
        {
            "type": "message:new",
            "payload": {"message": out.model_dump(mode="json"), "conversation": conversation_data},
        }
    )
    return out


@router.post(
    "/{conversation_id}/attachments",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    conversation_id: int,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageOut:
    """Send a file attachment from an agent to the Viber contact and store it.

    The file is persisted to the local upload dir and served back under
    `/uploads/...` (mounted in `main.py`). It is mirrored to the Viber contact
    as a `file` message with a publicly reachable `media` URL.
    """
    settings = get_settings()
    conversation = await db.get(
        Conversation,
        conversation_id,
        options=[selectinload(Conversation.messages)],
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    content = await file.read(MAX_ATTACHMENT_BYTES + 1)
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 25 MB)")

    original_name = (file.filename or "attachment").strip()
    safe_name = _SAFE_NAME.sub("-", Path(original_name).name).strip("-")[:120] or "attachment"

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{user.id}-{int(datetime.now().timestamp() * 1000)}-{safe_name}"
    (upload_dir / stored_name).write_bytes(content)

    base = settings.public_base_url.rstrip("/")
    media_url = f"{base}/uploads/{stored_name}"

    try:
        viber_response = await viber_client.send_message(
            {
                "receiver": conversation.contact_user_id,
                "type": "file",
                "media": media_url,
                "size": len(content),
                "file_name": safe_name,
            }
        )
    except ViberAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    token = viber_response.get("message_token")
    message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.agent.value,
        sender_id=user.id,
        message_type="file",
        text=file.filename or safe_name,
        media_url=media_url,
        status=MessageStatus.sent.value,
        viber_message_token=str(token) if token else None,
        payload={"file_name": safe_name, "content_type": file.content_type, "size": len(content)},
        created_at=datetime.now(timezone.utc),
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(message)
    await db.commit()

    out = MessageOut.model_validate(message_to_dict(message, conversation))
    conversation_data = await serialize_conversation(db, conversation.id)
    await manager.broadcast_to_agents(
        {
            "type": "message:new",
            "payload": {"message": out.model_dump(mode="json"), "conversation": conversation_data},
        }
    )
    return out