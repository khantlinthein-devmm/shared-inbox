from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import AgentNote, Conversation, ConversationStatus, User, UserRole
from app.schemas.conversation import ConversationOut, ConversationUpdate
from app.schemas.message import ConversationDetailOut, MessageOut
from app.services.serializers import (
    conversation_to_dict,
    message_to_dict,
    note_to_dict,
    serialize_conversation,
)
from app.services.ws_manager import manager

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    status: ConversationStatus | None = None,
    channel: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    """List conversations, optionally filtered by status, channel, and/or contact name."""
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.assigned_to),
        )
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
    )
    if status is not None:
        stmt = stmt.where(Conversation.status == status.value)
    if channel:
        stmt = stmt.where(Conversation.channel == channel)
    if search and search.strip():
        stmt = stmt.where(Conversation.contact_name.ilike(f"%{search.strip()}%"))

    rows = (await db.scalars(stmt)).unique().all()
    return [conversation_to_dict(c) for c in rows]


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Full thread: conversation metadata + messages + internal notes."""
    conversation = await db.get(
        Conversation,
        conversation_id,
        options=[
            selectinload(Conversation.messages),
            selectinload(Conversation.assigned_to),
            selectinload(Conversation.notes).joinedload(AgentNote.author),
        ],
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = sorted(conversation.messages, key=lambda m: m.created_at)
    notes = sorted(conversation.notes, key=lambda n: n.created_at)
    return {
        "conversation": conversation_to_dict(conversation),
        "messages": [MessageOut.model_validate(message_to_dict(m, conversation)) for m in messages],
        "notes": [note_to_dict(n) for n in notes],
    }


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Assign an agent and/or change the status. Broadcasts the change over WS."""
    conversation = await db.get(
        Conversation,
        conversation_id,
        options=[
            selectinload(Conversation.messages),
            selectinload(Conversation.assigned_to),
        ],
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if payload.status is not None:
        conversation.status = payload.status.value

    if payload.assigned_to_id is not None:
        if payload.assigned_to_id == 0:
            conversation.assigned_to_id = None
        else:
            agent = await db.get(User, payload.assigned_to_id)
            if agent is None or agent.role not in (UserRole.admin.value, UserRole.agent.value):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assignee must be an active agent or admin",
                )
            conversation.assigned_to_id = agent.id

    await db.commit()
    data = await serialize_conversation(db, conversation_id)
    await manager.broadcast_to_agents({"type": "conversation:updated", "payload": data})
    return data