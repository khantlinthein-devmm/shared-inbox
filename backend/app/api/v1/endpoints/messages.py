import json
import secrets
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import DEFAULT_CALL_INVITE, get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Conversation, Message, MessageSender, MessageStatus, User
from app.schemas.message import CallCreate, CallOut, MessageCreate, MessageOut
from app.services.channels.base import ChannelAPIError
from app.services.channels.registry import get_channel_client
from app.services.media import (
    OutboundMedia,
    convert_to_ogg_opus,
    detect_kind,
    public_url,
    safe_file_name,
    save_bytes,
)
from app.services.serializers import message_to_dict, serialize_conversation
from app.services.ws_manager import manager

router = APIRouter(prefix="/conversations", tags=["messages"])

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB (Viber file limit for bots)


async def _store_and_broadcast(db: AsyncSession, conversation: Conversation, message: Message) -> MessageOut:
    conversation.updated_at = datetime.now(timezone.utc)
    conversation.unread_count = 0  # replying means the agent has read the conversation
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
    """Send a reply from an agent to the contact (via their channel) and store it."""
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

    channel_client = get_channel_client(conversation.channel)
    try:
        result = await channel_client.send_text(conversation.contact_user_id, text)
    except ChannelAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.agent.value,
        sender_id=user.id,
        message_type="text",
        text=text,
        status=MessageStatus.sent.value,
        channel_message_id=result.message_id,
        created_at=datetime.now(timezone.utc),
    )
    return await _store_and_broadcast(db, conversation, message)


@router.post(
    "/{conversation_id}/attachments",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    conversation_id: int,
    file: UploadFile,
    voice: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageOut:
    """Send an image, video, audio, voice recording or file from an agent to the contact.

    The file is persisted to the local upload dir and served back under
    `/uploads/...` (mounted in `main.py`), then sent through the contact's
    channel using the richest message type that channel accepts for it.
    `voice=true` marks a composer recording, which is re-encoded to OGG/Opus
    so Telegram shows it as a playable voice note.
    """
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
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File is empty")

    original_name = (file.filename or "attachment").strip()
    safe_name = safe_file_name(original_name)
    path, media_url = save_bytes(content, safe_name)
    message_type = "voice" if voice else detect_kind(file.content_type)
    media = OutboundMedia(
        kind=message_type,
        path=path,
        url=media_url,
        file_name=safe_name,
        content_type=file.content_type,
        size=len(content),
    )

    if voice:
        converted = await convert_to_ogg_opus(path)
        if converted is not None:
            path.unlink(missing_ok=True)
            media = OutboundMedia(
                kind="voice",
                path=converted,
                url=public_url(converted),
                file_name="voice.ogg",
                content_type="audio/ogg",
                size=converted.stat().st_size,
            )
        else:
            media.kind = "file"

    channel_client = get_channel_client(conversation.channel)
    try:
        result = await channel_client.send_media(conversation.contact_user_id, media)
    except ChannelAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.agent.value,
        sender_id=user.id,
        message_type=message_type,
        # Images, videos and voice notes speak for themselves; files keep their name as a label.
        text=original_name if message_type in ("file", "audio") else None,
        media_url=media.url,
        status=MessageStatus.sent.value,
        channel_message_id=result.message_id,
        payload={"file_name": media.file_name, "content_type": media.content_type, "size": media.size},
        created_at=datetime.now(timezone.utc),
    )
    return await _store_and_broadcast(db, conversation, message)


def _jitsi_url(room: str, *, video: bool, display_name: str | None = None) -> str:
    # Jitsi reads per-link config from the URL fragment as JSON-encoded values.
    params: dict = {}
    if not video:
        params["config.startWithVideoMuted"] = True
        params["config.startAudioOnly"] = True
    if display_name:
        params["userInfo.displayName"] = display_name
    domain = get_settings().jitsi_domain.strip().removeprefix("https://").strip("/")
    url = f"https://{domain}/{room}"
    if params:
        url += "#" + "&".join(f"{k}={quote(json.dumps(v, ensure_ascii=False))}" for k, v in params.items())
    return url


@router.post("/{conversation_id}/calls", response_model=CallOut, status_code=status.HTTP_201_CREATED)
async def start_call(
    conversation_id: int,
    payload: CallCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CallOut:
    """Start a Jitsi voice/video call: send the contact a join link and return the agent's own link.

    Bot APIs can't place native Viber/Telegram calls, so the call runs in the
    browser (or Jitsi app) on both sides. The room name is random (128 bits),
    so only people holding the link can find it.
    """
    conversation = await db.get(
        Conversation,
        conversation_id,
        options=[selectinload(Conversation.messages)],
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    room = f"SharedInbox-{secrets.token_hex(16)}"
    kind = "video" if payload.video else "voice"
    invite_url = _jitsi_url(room, video=payload.video)
    template = get_settings().call_invite_template.strip() or DEFAULT_CALL_INVITE
    text = template.replace("{kind}", kind).replace("{url}", invite_url)
    if invite_url not in text:
        text = f"{text} {invite_url}"

    channel_client = get_channel_client(conversation.channel)
    try:
        result = await channel_client.send_text(conversation.contact_user_id, text)
    except ChannelAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.agent.value,
        sender_id=user.id,
        message_type=f"{kind}_call",
        text=text,
        media_url=invite_url,
        status=MessageStatus.sent.value,
        channel_message_id=result.message_id,
        payload={"room": room},
        created_at=datetime.now(timezone.utc),
    )
    out = await _store_and_broadcast(db, conversation, message)
    return CallOut(join_url=_jitsi_url(room, video=payload.video, display_name=user.full_name), message=out)