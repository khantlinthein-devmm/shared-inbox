from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConversationStatus(str, Enum):
    unassigned = "unassigned"
    open = "open"
    pending = "pending"
    closed = "closed"


class ChannelType(str, Enum):
    """Messaging channels a conversation can come from."""

    viber = "viber"
    telegram = "telegram"
    messenger = "messenger"
    whatsapp = "whatsapp"


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("channel", "contact_user_id", name="uq_conversation_channel_contact"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(20), default=ChannelType.viber.value, index=True)
    # Contact's channel-native identifier (Viber user id, Telegram chat id, ...).
    contact_user_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_name: Mapped[str] = mapped_column(String(255), default="Contact")
    contact_avatar: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ConversationStatus.unassigned.value, index=True)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Contact messages no agent has looked at yet (shared by the whole team).
    unread_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assigned_to: Mapped["User | None"] = relationship(foreign_keys=[assigned_to_id])
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    notes: Mapped[list["AgentNote"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} channel={self.channel!r} contact={self.contact_user_id!r}>"