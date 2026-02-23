from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import verify_admin_key
from app.domains.whatsapp.dependencies import get_whatsapp_service
from app.domains.whatsapp.schemas import (
    WhatsAppAccountCreate,
    WhatsAppAccountResponse,
    WhatsAppAccountUpdate,
    WhatsAppConfigResponse,
    WhatsAppConfigUpdate,
)
from app.domains.whatsapp.services.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/api/v1/admin/whatsapp", tags=["whatsapp-admin"], dependencies=[Depends(verify_admin_key)])


def _mask_token(token: str) -> str:
    if len(token) <= 8:
        return "****"
    return token[:4] + "****" + token[-4:]


# ── Config ────────────────────────────────────────────────────────────────


@router.get("/config", response_model=WhatsAppConfigResponse | None)
async def get_config(svc: WhatsAppService = Depends(get_whatsapp_service)):
    config = await svc.get_config()
    if config is None:
        return None
    return WhatsAppConfigResponse(
        id=config.id,
        access_token_masked=_mask_token(config.access_token),
        verify_token_masked=_mask_token(config.verify_token),
        updated_at=config.updated_at,
    )


@router.put("/config", response_model=WhatsAppConfigResponse)
async def update_config(
    body: WhatsAppConfigUpdate,
    svc: WhatsAppService = Depends(get_whatsapp_service),
):
    config = await svc.update_config(body)
    return WhatsAppConfigResponse(
        id=config.id,
        access_token_masked=_mask_token(config.access_token),
        verify_token_masked=_mask_token(config.verify_token),
        updated_at=config.updated_at,
    )


# ── Accounts ──────────────────────────────────────────────────────────────


@router.get("/accounts", response_model=list[WhatsAppAccountResponse])
async def list_accounts(svc: WhatsAppService = Depends(get_whatsapp_service)):
    accounts = await svc.list_accounts()
    return [WhatsAppAccountResponse.model_validate(a) for a in accounts]


@router.post("/accounts", response_model=WhatsAppAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: WhatsAppAccountCreate,
    svc: WhatsAppService = Depends(get_whatsapp_service),
):
    account = await svc.create_account(body)
    return WhatsAppAccountResponse.model_validate(account)


@router.get("/accounts/{account_id}", response_model=WhatsAppAccountResponse)
async def get_account(
    account_id: UUID,
    svc: WhatsAppService = Depends(get_whatsapp_service),
):
    account = await svc.get_account(account_id)
    return WhatsAppAccountResponse.model_validate(account)


@router.put("/accounts/{account_id}", response_model=WhatsAppAccountResponse)
async def update_account(
    account_id: UUID,
    body: WhatsAppAccountUpdate,
    svc: WhatsAppService = Depends(get_whatsapp_service),
):
    account = await svc.update_account(account_id, body)
    return WhatsAppAccountResponse.model_validate(account)


@router.post("/accounts/{account_id}/approve", response_model=WhatsAppAccountResponse)
async def approve_account(
    account_id: UUID,
    svc: WhatsAppService = Depends(get_whatsapp_service),
):
    account = await svc.approve_account(account_id)
    return WhatsAppAccountResponse.model_validate(account)


@router.get("/accounts/{account_id}/subscription")
async def check_subscription(
    account_id: UUID,
    svc: WhatsAppService = Depends(get_whatsapp_service),
):
    account = await svc.get_account(account_id)
    result = await svc.check_waba_subscription(account.waba_id)
    return result


@router.delete("/accounts/{account_id}", response_model=WhatsAppAccountResponse)
async def disconnect_account(
    account_id: UUID,
    svc: WhatsAppService = Depends(get_whatsapp_service),
):
    account = await svc.disconnect_account(account_id)
    return WhatsAppAccountResponse.model_validate(account)
