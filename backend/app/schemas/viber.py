from pydantic import BaseModel, ConfigDict


class ViberMessagePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str | None = None
    text: str | None = None
    media: str | None = None
    file_name: str | None = None
    duration: int | None = None
    size: int | None = None
    sticker_id: int | None = None
    thumbnail: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class ViberSender(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str | None = None
    avatar: str | None = None
    country: str | None = None
    language: str | None = None


class ViberWebhookEvent(BaseModel):
    """Loose model for Viber webhook callbacks.

    Viber sends a single flat JSON object per event; fields vary by event type.
    `extra="allow"` preserves unknown fields so signatures of future events
    never break webhook ingestion.
    """

    model_config = ConfigDict(extra="allow")

    event: str
    timestamp: int | None = None
    message_token: int | None = None
    user_id: str | None = None
    conversation_type: str | None = None
    sender: ViberSender | None = None
    message: ViberMessagePayload | None = None