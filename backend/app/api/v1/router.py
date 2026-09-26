from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    conversations,
    diagnostics,
    messages,
    notes,
    users,
    viber,
)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router)
api_v1.include_router(users.router)
api_v1.include_router(conversations.router)
api_v1.include_router(messages.router)
api_v1.include_router(notes.router)
api_v1.include_router(viber.router)
api_v1.include_router(diagnostics.router)