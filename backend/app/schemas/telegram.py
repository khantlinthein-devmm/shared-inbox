from pydantic import BaseModel, ConfigDict, Field


class TelegramChat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    type: str | None = None


class TelegramUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class TelegramPhotoSize(BaseModel):
    model_config = ConfigDict(extra="ignore")

    file_id: str
    file_unique_id: str | None = None


class TelegramFile(BaseModel):
    """Shared shape of document / voice / audio / video / video_note / animation."""

    model_config = ConfigDict(extra="ignore")

    file_id: str
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    duration: int | None = None


class TelegramSticker(BaseModel):
    model_config = ConfigDict(extra="ignore")

    file_id: str
    emoji: str | None = None
    is_animated: bool = False
    is_video: bool = False


class TelegramMessage(BaseModel):
    """Loose model for a Telegram message. `extra='allow'` keeps unknown fields
    (e.g. voice, sticker, location) around in case a caller needs them later.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    message_id: int
    date: int | None = None
    chat: TelegramChat
    from_user: TelegramUser | None = Field(default=None, alias="from")
    text: str | None = None
    caption: str | None = None
    document: TelegramFile | None = None
    photo: list[TelegramPhotoSize] | None = None
    voice: TelegramFile | None = None
    audio: TelegramFile | None = None
    video: TelegramFile | None = None
    video_note: TelegramFile | None = None
    animation: TelegramFile | None = None
    sticker: TelegramSticker | None = None


class TelegramUpdate(BaseModel):
    """A single Telegram Bot API update. https://core.telegram.org/bots/api#update"""

    model_config = ConfigDict(extra="allow")

    update_id: int
    message: TelegramMessage | None = None
    edited_message: TelegramMessage | None = None
