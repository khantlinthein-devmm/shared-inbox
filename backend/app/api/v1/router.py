from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    channels,
    conversations,
    messages,
    messenger,
    notes,
    quick_replies,
    telegram,
    users,
    viber,
    whatsapp,
)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router)
api_v1.include_router(users.router)
api_v1.include_router(conversations.router)
api_v1.include_router(messages.router)
api_v1.include_router(notes.router)
api_v1.include_router(quick_replies.router)
api_v1.include_router(viber.router)
api_v1.include_router(telegram.router)
api_v1.include_router(messenger.router)
api_v1.include_router(whatsapp.router)
api_v1.include_router(channels.router)
