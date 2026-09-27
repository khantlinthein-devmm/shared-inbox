from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.deps import require_roles
from app.models.user import User, UserRole
from app.services.channels.base import ChannelAPIError
from app.services.channels.telegram import client as telegram_client
from app.services.channels.viber import client as viber_client

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


class SetWebhookIn(BaseModel):
    url: str | None = None


@router.get("/viber/account")
async def viber_account_info(_: User = Depends(require_roles(UserRole.admin))) -> dict:
    """Admin only: report the connected Viber account info (health check)."""
    try:
        return await viber_client.get_account_info()
    except ChannelAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/viber/set-webhook")
async def viber_set_webhook(
    payload: SetWebhookIn,
    _: User = Depends(require_roles(UserRole.admin)),
) -> dict:
    """Admin only: point Viber at this server's /api/v1/viber/webhook endpoint."""
    settings = get_settings()
    url = payload.url or settings.viber_webhook_url
    if not url:
        raise HTTPException(status_code=400, detail="Provide a 'url' or configure VIBER_WEBHOOK_URL")
    try:
        return await viber_client.set_webhook(url=url)
    except ChannelAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/telegram/account")
async def telegram_account_info(_: User = Depends(require_roles(UserRole.admin))) -> dict:
    """Admin only: report the connected Telegram bot info (health check)."""
    try:
        return await telegram_client.get_account_info()
    except ChannelAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/telegram/set-webhook")
async def telegram_set_webhook(
    payload: SetWebhookIn,
    _: User = Depends(require_roles(UserRole.admin)),
) -> dict:
    """Admin only: point Telegram at this server's /api/v1/telegram/webhook endpoint."""
    settings = get_settings()
    url = payload.url or settings.telegram_webhook_url
    if not url:
        raise HTTPException(status_code=400, detail="Provide a 'url' or configure TELEGRAM_WEBHOOK_URL")
    try:
        return await telegram_client.set_webhook(url=url)
    except ChannelAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
