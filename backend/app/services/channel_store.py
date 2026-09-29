"""Where channel credentials and runtime settings come from.

Admins connect channels in the UI (stored encrypted in channel_accounts); the
older .env settings for Viber and Telegram still work as a fallback so existing
deployments keep running. Reads are cached for a few seconds so webhooks don't
hit the database on every call; saving invalidates the cache.
"""

import logging
import time
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import AppSetting, ChannelAccount
from app.services.secret_box import seal, unseal

logger = logging.getLogger(__name__)

CHANNELS = ("viber", "telegram", "messenger", "whatsapp")
CACHE_SECONDS = 10.0
PUBLIC_URL_KEY = "public_url"


@dataclass
class ChannelConfig:
    channel: str
    values: dict = field(default_factory=dict)
    source: str = "ui"  # "ui" or "env"

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key) or default


_cache: dict[str, tuple[float, object]] = {}


def invalidate(key: str | None = None) -> None:
    if key is None:
        _cache.clear()
    else:
        _cache.pop(key, None)


def _cached(key: str):
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return True, hit[1]
    return False, None


def _env_config(channel: str) -> ChannelConfig | None:
    s = get_settings()
    if channel == "viber" and s.viber_auth_token:
        return ChannelConfig("viber", {"auth_token": s.viber_auth_token, "auto_reply": s.viber_auto_reply}, "env")
    if channel == "telegram" and s.telegram_bot_token:
        values = {
            "bot_token": s.telegram_bot_token,
            "webhook_secret": s.telegram_webhook_secret,
            "auto_reply": s.telegram_auto_reply,
        }
        return ChannelConfig("telegram", values, "env")
    return None


async def get_config(channel: str) -> ChannelConfig | None:
    """The active configuration for a channel, or None if it isn't connected."""
    hit, value = _cached(channel)
    if hit:
        return value  # type: ignore[return-value]
    async with SessionLocal() as db:
        row = await db.get(ChannelAccount, channel)
    config: ChannelConfig | None = None
    if row is not None:
        values = unseal(row.secrets)
        if values is None:
            logger.error("Stored %s credentials can't be decrypted (SECRET_KEY changed?); reconnect it", channel)
        else:
            config = ChannelConfig(channel, values, "ui")
    if config is None:
        config = _env_config(channel)
    _cache[channel] = (time.monotonic(), config)
    return config


async def save_config(channel: str, values: dict) -> None:
    async with SessionLocal() as db:
        row = await db.get(ChannelAccount, channel)
        if row is None:
            db.add(ChannelAccount(channel=channel, secrets=seal(values)))
        else:
            row.secrets = seal(values)
        await db.commit()
    invalidate(channel)


async def delete_config(channel: str) -> None:
    async with SessionLocal() as db:
        row = await db.get(ChannelAccount, channel)
        if row is not None:
            await db.delete(row)
            await db.commit()
    invalidate(channel)


async def get_public_url() -> str:
    """Base URL the internet reaches this backend at (webhooks, media links)."""
    hit, value = _cached(PUBLIC_URL_KEY)
    if hit:
        return value  # type: ignore[return-value]
    async with SessionLocal() as db:
        row = await db.get(AppSetting, PUBLIC_URL_KEY)
    url = (row.value if row else "") or get_settings().public_base_url
    url = url.strip().rstrip("/")
    _cache[PUBLIC_URL_KEY] = (time.monotonic(), url)
    return url


async def set_public_url(url: str) -> None:
    async with SessionLocal() as db:
        row = await db.get(AppSetting, PUBLIC_URL_KEY)
        if row is None:
            db.add(AppSetting(key=PUBLIC_URL_KEY, value=url))
        else:
            row.value = url
        await db.commit()
    invalidate(PUBLIC_URL_KEY)


def is_public(url: str) -> bool:
    """False for localhost-style URLs that providers can't deliver webhooks to."""
    host = url.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()
    return url.startswith("https://") and host not in ("localhost", "127.0.0.1", "0.0.0.0") and "." in host
