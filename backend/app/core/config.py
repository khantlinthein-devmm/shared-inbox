from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_CALL_INVITE = "Our support team is inviting you to a {kind} call. Tap the link to join: {url}"


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

    # Telegram
    telegram_bot_token: str = ""
    telegram_api_base_url: str = "https://api.telegram.org"
    telegram_webhook_url: str = ""
    # Sent back by Telegram as `X-Telegram-Bot-Api-Secret-Token` on every webhook
    # call so we can verify requests actually come from Telegram.
    telegram_webhook_secret: str = ""
    telegram_auto_reply: str = ""

    # Meta Graph API (Messenger + WhatsApp Cloud API). Base is overridable for tests.
    graph_api_base_url: str = "https://graph.facebook.com"
    graph_api_version: str = "v23.0"

    # Calls (Jitsi Meet). meet.jit.si works for trying it out; use a
    # self-hosted Jitsi or 8x8 JaaS domain in production.
    jitsi_domain: str = "meet.jit.si"
    # Sent to the contact; {kind} becomes "voice"/"video" and {url} the join link.
    # Empty means DEFAULT_CALL_INVITE.
    call_invite_template: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()