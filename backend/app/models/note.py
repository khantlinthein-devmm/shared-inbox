from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AgentNote(Base):
    """Internal note attached to a conversation (visible to agents only, never sent to Viber)."""

    __tablename__ = "agent_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="notes")
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

    def __repr__(self) -> str:
        return f"<AgentNote id={self.id} conversation_id={self.conversation_id}>"