"""Admin API behind the Channels page: connect messaging channels without touching .env."""

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_roles
from app.models import User, UserRole
from app.services import channel_store
from app.services.channel_store import CHANNELS, ChannelConfig, get_config, get_public_url, is_public
from app.services.channels.base import ChannelAPIError
from app.services.channels.messenger import MessengerClient
from app.services.channels.registry import LABELS
from app.services.channels.telegram import TelegramClient
from app.services.channels.viber import ViberClient
from app.services.channels.whatsapp import WhatsAppClient

router = APIRouter(prefix="/channels", tags=["channels"])
admin_only = Depends(require_roles(UserRole.admin))

REQUIRED = {
    "viber": ["auth_token"],
    "telegram": ["bot_token"],
    "messenger": ["page_access_token", "app_secret"],
    "whatsapp": ["access_token", "phone_number_id", "app_secret"],
}
SECRET_FIELDS = {"auth_token", "bot_token", "page_access_token", "access_token", "app_secret", "webhook_secret"}
EDITABLE = {channel: set(fields) | {"auto_reply"} for channel, fields in REQUIRED.items()}
# Details learned from the provider when connecting, shown on the card.
DETAIL_FIELDS = ("account_name", "bot_username", "page_id", "page_name", "display_phone", "verified_name")
# Telegram and Viber webhooks are registered by API; Meta's must be added in the App Dashboard.
AUTO_WEBHOOK = {"telegram", "viber"}


class PublicUrlIn(BaseModel):
    url: str


def _mask(value: str) -> str:
    return f"••••{value[-4:]}" if len(value) > 4 else "••••"


def _webhook_url(public_url: str, channel: str) -> str:
    return f"{public_url}/api/v1/{channel}/webhook"


def _describe(channel: str, config: ChannelConfig | None, public_url: str) -> dict:
    values = config.values if config else {}
    return {
        "channel": channel,
        "label": LABELS[channel],
        "connected": config is not None,
        "source": config.source if config else None,
        "fields": {
            key: (_mask(values[key]) if key in SECRET_FIELDS else values[key])
            for key in EDITABLE[channel]
            if values.get(key)
        },
        "details": {key: values[key] for key in DETAIL_FIELDS if values.get(key)},
        "webhook_url": _webhook_url(public_url, channel),
        "webhook_auto": channel in AUTO_WEBHOOK,
        # Admins paste this into the Meta App Dashboard, so it's shown in full.
        "verify_token": values.get("verify_token") if channel in ("messenger", "whatsapp") else None,
    }


async def _register_webhook(channel: str, values: dict, public_url: str) -> str | None:
    """Point Telegram/Viber at this server. Returns a warning instead of raising."""
    if channel not in AUTO_WEBHOOK:
        return None
    if not is_public(public_url):
        return "Set a public https URL above so this channel can deliver messages."
    try:
        if channel == "telegram":
            await TelegramClient(values["bot_token"]).set_webhook(_webhook_url(public_url, channel), values["webhook_secret"])
        else:
            await ViberClient(values["auth_token"]).set_webhook(_webhook_url(public_url, channel))
    except ChannelAPIError as exc:
        return f"Saved, but registering the webhook failed: {exc}"
    return None


@router.get("")
async def list_channels(_: User = admin_only) -> dict:
    public_url = await get_public_url()
    return {
        "public_url": public_url,
        "public_url_ok": is_public(public_url),
        "channels": [_describe(channel, await get_config(channel), public_url) for channel in CHANNELS],
    }


@router.put("/public-url")
async def set_public_url(payload: PublicUrlIn, _: User = admin_only) -> dict:
    """Save the server's public address and re-register webhooks that depend on it."""
    url = payload.url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="URL must start with https://")
    await channel_store.set_public_url(url)
    warnings = {}
    for channel in AUTO_WEBHOOK:
        config = await get_config(channel)
        if config is not None:
            warning = await _register_webhook(channel, config.values, url)
            if warning:
                warnings[channel] = warning
    return {**await list_channels(_), "warnings": warnings}


@router.put("/{channel}")
async def connect_channel(channel: str, payload: dict[str, str], _: User = admin_only) -> dict:
    """Validate credentials with the provider, store them encrypted, and wire up the webhook."""
    if channel not in CHANNELS:
        raise HTTPException(status_code=404, detail="Unknown channel")
    current = await get_config(channel)
    # Blank fields keep their current value, so admins can change one token at a time.
    values = dict(current.values) if current else {}
    for key, value in payload.items():
        if key in EDITABLE[channel] and (value.strip() or key == "auto_reply"):
            values[key] = value.strip()
    missing = [key for key in REQUIRED[channel] if not values.get(key)]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing: {', '.join(missing)}")

    try:
        if channel == "telegram":
            me = (await TelegramClient(values["bot_token"]).get_account_info()).get("result", {})
            values["bot_username"] = me.get("username", "")
            values["webhook_secret"] = values.get("webhook_secret") or secrets.token_hex(24)
        elif channel == "viber":
            values["account_name"] = (await ViberClient(values["auth_token"]).get_account_info()).get("name", "")
        elif channel == "messenger":
            page = await MessengerClient(values["page_access_token"]).get_account_info()
            values["page_id"], values["page_name"] = page.get("id", ""), page.get("name", "")
        else:
            number = await WhatsAppClient(values["access_token"], values["phone_number_id"]).get_account_info()
            values["display_phone"] = number.get("display_phone_number", "")
            values["verified_name"] = number.get("verified_name", "")
    except (ChannelAPIError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Could not connect to {LABELS[channel]}: {exc}") from exc

    if channel in ("messenger", "whatsapp"):
        values["verify_token"] = values.get("verify_token") or secrets.token_urlsafe(24)

    # Save before registering: Viber calls the webhook during registration and
    # it must already accept the new token.
    await channel_store.save_config(channel, values)
    public_url = await get_public_url()
    warnings = []
    warning = await _register_webhook(channel, values, public_url)
    if warning:
        warnings.append(warning)
    if channel == "messenger":
        try:
            await MessengerClient(values["page_access_token"]).subscribe_page(values["page_id"])
        except ChannelAPIError as exc:
            warnings.append(f"Couldn't subscribe the app to the Page yet ({exc}); add the webhook in Meta first, then Save again.")
    return {**_describe(channel, await get_config(channel), public_url), "warnings": warnings}


@router.delete("/{channel}")
async def disconnect_channel(channel: str, _: User = admin_only) -> dict:
    if channel not in CHANNELS:
        raise HTTPException(status_code=404, detail="Unknown channel")
    config = await get_config(channel)
    if config is None:
        raise HTTPException(status_code=404, detail="Not connected")
    if config.source == "env":
        raise HTTPException(status_code=400, detail="This channel is configured in .env; remove it there.")
    try:  # best effort: stop the provider sending to us
        if channel == "telegram":
            await TelegramClient(config.get("bot_token")).delete_webhook()
        elif channel == "viber":
            await ViberClient(config.get("auth_token")).remove_webhook()
    except ChannelAPIError:
        pass
    await channel_store.delete_config(channel)
    return _describe(channel, await get_config(channel), await get_public_url())
