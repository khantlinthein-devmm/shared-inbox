from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChannelAccount(Base):
    """Credentials for one connected messaging channel, entered by an admin in the UI."""

    __tablename__ = "channel_accounts"

    channel: Mapped[str] = mapped_column(String(20), primary_key=True)
    # JSON of tokens/secrets, encrypted with a key derived from SECRET_KEY.
    secrets: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AppSetting(Base):
    """Small key/value store for settings admins change at runtime (e.g. the public URL)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
