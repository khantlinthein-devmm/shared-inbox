from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import AgentNote, Conversation, User
from app.schemas.message import AgentNoteCreate, AgentNoteOut
from app.services.serializers import note_to_dict
from app.services.ws_manager import manager

router = APIRouter(prefix="/conversations", tags=["notes"])


@router.get("/{conversation_id}/notes", response_model=list[AgentNoteOut])
async def list_notes(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AgentNoteOut]:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    rows = (
        await db.scalars(
            select(AgentNote)
            .where(AgentNote.conversation_id == conversation_id)
            .options(joinedload(AgentNote.author))
            .order_by(AgentNote.created_at.asc())
        )
    ).all()
    return [AgentNoteOut.model_validate(note_to_dict(n)) for n in rows]


@router.post("/{conversation_id}/notes", response_model=AgentNoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    conversation_id: int,
    payload: AgentNoteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentNoteOut:
    """Add an internal (agent-only) note to a conversation."""
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Note content is required")

    note = AgentNote(
        conversation_id=conversation_id,
        author_id=user.id,
        content=content,
        created_at=datetime.now(timezone.utc),
    )
    db.add(note)
    await db.commit()

    out = AgentNoteOut(
        id=note.id,
        conversation_id=note.conversation_id,
        author_id=note.author_id,
        author_name=user.full_name,
        content=note.content,
        created_at=note.created_at,
    )
    await manager.broadcast_to_agents({"type": "note:new", "payload": out.model_dump(mode="json")})
    return out