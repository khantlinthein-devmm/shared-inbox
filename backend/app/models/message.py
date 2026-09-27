from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MessageSender(str, Enum):
    contact = "contact"
    agent = "agent"


class MessageStatus(str, Enum):
    received = "received"
    sent = "sent"
    delivered = "delivered"
    seen = "seen"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    sender: Mapped[str] = mapped_column(String(20), default=MessageSender.contact.value)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Provider-native message id (Viber message_token, Telegram message_id, ...),
    # used to correlate delivery/seen status updates back to this row.
    channel_message_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    message_type: Mapped[str] = mapped_column(String(32), default="text")
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=MessageStatus.received.value)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} sender={self.sender!r}>"