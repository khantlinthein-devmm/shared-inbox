from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Shared Inbox"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 12

    # Database
    database_url: str = "postgresql+asyncpg://inbox:inbox@localhost:5432/shared_inbox"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Uploads / public URLs
    upload_dir: str = "uploads"
    public_base_url: str = "http://localhost:8000"

    # Viber
    viber_auth_token: str = ""
    viber_webhook_url: str = ""
    viber_webhook_events: list[str] = [
        "conversation_started",
        "subscribed",
        "unsubscribed",
        "message",
        "delivered",
        "seen",
    ]
    viber_sender_name: str = "Support Bot"
    viber_auto_reply: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()