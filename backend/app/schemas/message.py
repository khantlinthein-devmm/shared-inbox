from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.conversation import ConversationOut


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender: str
    sender_id: int | None = None
    sender_name: str | None = None
    message_type: str = "text"
    text: str | None = None
    media_url: str | None = None
    status: str = "received"
    created_at: datetime


class MessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class CallCreate(BaseModel):
    video: bool = True


class CallOut(BaseModel):
    join_url: str
    message: MessageOut


class AgentNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class AgentNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    author_id: int
    author_name: str | None = None
    content: str
    created_at: datetime


class ConversationDetailOut(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]
    notes: list[AgentNoteOut]