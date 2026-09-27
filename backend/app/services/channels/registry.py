from app.services.channels.base import ChannelClient
from app.services.channels.telegram import client as telegram_client
from app.services.channels.viber import client as viber_client

_CLIENTS: dict[str, ChannelClient] = {
    viber_client.channel: viber_client,
    telegram_client.channel: telegram_client,
}


def get_channel_client(channel: str) -> ChannelClient:
    try:
        return _CLIENTS[channel]
    except KeyError:
        raise ValueError(f"Unknown channel: {channel!r}") from None
