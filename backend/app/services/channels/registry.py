from app.services.channel_store import ChannelConfig, get_config
from app.services.channels.base import ChannelAPIError, ChannelClient
from app.services.channels.messenger import MessengerClient
from app.services.channels.telegram import TelegramClient
from app.services.channels.viber import ViberClient
from app.services.channels.whatsapp import WhatsAppClient

LABELS = {"viber": "Viber", "telegram": "Telegram", "messenger": "Messenger", "whatsapp": "WhatsApp"}


class ChannelNotConnected(ChannelAPIError):
    """Raised when sending through a channel nobody has connected yet."""


def build_client(config: ChannelConfig) -> ChannelClient:
    if config.channel == "viber":
        return ViberClient(config.get("auth_token"))
    if config.channel == "telegram":
        return TelegramClient(config.get("bot_token"))
    if config.channel == "messenger":
        return MessengerClient(config.get("page_access_token"))
    if config.channel == "whatsapp":
        return WhatsAppClient(config.get("access_token"), config.get("phone_number_id"))
    raise ValueError(f"Unknown channel: {config.channel!r}")


async def get_channel_client(channel: str) -> ChannelClient:
    config = await get_config(channel)
    if config is None:
        label = LABELS.get(channel, channel)
        raise ChannelNotConnected(f"{label} isn't connected. An admin can connect it on the Channels page.")
    return build_client(config)
