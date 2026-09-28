from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import QuickReply, User, UserRole
from app.schemas.quick_reply import QuickReplyCreate, QuickReplyOut, QuickReplyUpdate

router = APIRouter(prefix="/quick-replies", tags=["quick-replies"])


@router.get("", response_model=list[QuickReplyOut])
async def list_quick_replies(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[QuickReply]:
    rows = await db.scalars(select(QuickReply).order_by(QuickReply.title, QuickReply.id))
    return list(rows)


@router.post("", response_model=QuickReplyOut, status_code=status.HTTP_201_CREATED)
async def create_quick_reply(
    payload: QuickReplyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin)),
) -> QuickReply:
    title = payload.title.strip()
    content = payload.content.strip()
    if not title or not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title and content are required")
    reply = QuickReply(title=title, content=content, created_by_id=user.id)
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return reply


@router.patch("/{reply_id}", response_model=QuickReplyOut)
async def update_quick_reply(
    reply_id: int,
    payload: QuickReplyUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
) -> QuickReply:
    reply = await db.get(QuickReply, reply_id)
    if reply is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quick reply not found")
    if payload.title is not None and payload.title.strip():
        reply.title = payload.title.strip()
    if payload.content is not None and payload.content.strip():
        reply.content = payload.content.strip()
    await db.commit()
    await db.refresh(reply)
    return reply


@router.delete("/{reply_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quick_reply(
    reply_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
) -> Response:
    reply = await db.get(QuickReply, reply_id)
    if reply is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quick reply not found")
    await db.delete(reply)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
