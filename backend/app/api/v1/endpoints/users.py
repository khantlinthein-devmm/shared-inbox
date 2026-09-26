from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.auth import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/agents", response_model=list[UserOut])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[User]:
    """List all staff users (agents + admins) for the assignment dropdown."""
    rows = await db.scalars(
        select(User)
        .where(User.is_active.is_(True))
        .where(User.role.in_((UserRole.admin.value, UserRole.agent.value)))
        .order_by(User.full_name)
    )
    return list(rows)


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = None


@router.get("", response_model=list[UserOut])
async def list_all_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
) -> list[User]:
    """Admin only: list every account (including disabled) for /admin/users."""
    rows = await db.scalars(select(User).order_by(User.created_at.asc()))
    return list(rows)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_roles(UserRole.admin)),
) -> User:
    """Admin only: rename, change role, reset password, or disable/enable."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.full_name is not None and payload.full_name.strip():
        user.full_name = payload.full_name.strip()
    if payload.role is not None:
        user.role = payload.role.value
    if payload.is_active is not None:
        if user.id == current.id and payload.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable yourself")
        user.is_active = payload.is_active
    if payload.password is not None:
        if len(payload.password) < 6:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password too short")
        user.hashed_password = hash_password(payload.password)
    await db.commit()
    return user


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
) -> User:
    """Admin only: create a new agent account."""
    existing = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        role=payload.role.value,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    return user