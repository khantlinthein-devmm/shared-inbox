from dataclasses import dataclass, field
from typing import Protocol

from app.services.media import OutboundMedia


class ChannelAPIError(RuntimeError):
    """Raised when a channel provider's API rejects a request."""


@dataclass
class ChannelSendResult:
    """Normalized result of sending a message through any channel."""

    message_id: str | None
    raw: dict = field(default_factory=dict)


class ChannelClient(Protocol):
    """Common interface every messaging channel client implements.

    Endpoints and services talk to this interface instead of a specific
    provider, so adding a channel means adding one implementation here
    plus one webhook endpoint - nothing else changes.
    """

    channel: str

    async def send_text(self, receiver: str, text: str) -> ChannelSendResult: ...

    async def send_media(self, receiver: str, media: OutboundMedia) -> ChannelSendResult: ...

    async def get_account_info(self) -> dict: ...
