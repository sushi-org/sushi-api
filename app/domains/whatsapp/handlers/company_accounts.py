from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.domains.whatsapp.dependencies import get_whatsapp_service
from app.domains.whatsapp.schemas import (
    WhatsAppAccountCreate,
    WhatsAppAccountResponse,
)
from app.domains.whatsapp.services.whatsapp_service import WhatsAppService

router = APIRouter(tags=["whatsapp-accounts"])


@router.get("", response_model=list[WhatsAppAccountResponse])
async def list_company_accounts(
    company_id: UUID,
    svc: WhatsAppService = Depends(get_whatsapp_service),
):
    accounts = await svc.list_accounts_by_company(company_id)
    return [WhatsAppAccountResponse.model_validate(a) for a in accounts]


@router.post("", response_model=WhatsAppAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_company_account(
    company_id: UUID,
    body: WhatsAppAccountCreate,
    svc: WhatsAppService = Depends(get_whatsapp_service),
):
    account = await svc.create_account(body)
    return WhatsAppAccountResponse.model_validate(account)


@router.delete("/{account_id}", response_model=WhatsAppAccountResponse)
async def disconnect_company_account(
    company_id: UUID,
    account_id: UUID,
    svc: WhatsAppService = Depends(get_whatsapp_service),
):
    account = await svc.disconnect_account(account_id)
    return WhatsAppAccountResponse.model_validate(account)
