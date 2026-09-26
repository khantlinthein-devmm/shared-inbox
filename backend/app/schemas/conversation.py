from datetime import datetime

from pydantic import BaseModel

from app.models import ConversationStatus


class ConversationOut(BaseModel):
    id: int
    contact_user_id: str
    contact_name: str
    contact_avatar: str | None = None
    status: str
    assigned_to_id: int | None = None
    assigned_to_email: str | None = None
    assigned_to_full_name: str | None = None
    last_message: str | None = None
    last_message_at: datetime | None = None
    message_count: int = 0


class ConversationUpdate(BaseModel):
    status: ConversationStatus | None = None
    # 0 clears the assignment (unassign), None leaves it unchanged.
    assigned_to_id: int | None = None