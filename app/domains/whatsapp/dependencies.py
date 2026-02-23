from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.domains.company.repositories.branch import BranchRepository
from app.domains.whatsapp.repositories.account import WhatsAppAccountRepository
from app.domains.whatsapp.repositories.config import WhatsAppConfigRepository
from app.domains.whatsapp.services.whatsapp_service import WhatsAppService


# ── Repositories ─────────────────────────────────────────────────────────


async def get_whatsapp_config_repo(session: AsyncSession = Depends(get_session)) -> WhatsAppConfigRepository:
    return WhatsAppConfigRepository(session)


async def get_whatsapp_account_repo(session: AsyncSession = Depends(get_session)) -> WhatsAppAccountRepository:
    return WhatsAppAccountRepository(session)


# ── Services ─────────────────────────────────────────────────────────────


async def get_whatsapp_service(
    config_repo: WhatsAppConfigRepository = Depends(get_whatsapp_config_repo),
    account_repo: WhatsAppAccountRepository = Depends(get_whatsapp_account_repo),
    session: AsyncSession = Depends(get_session),
) -> WhatsAppService:
    branch_repo = BranchRepository(session)
    return WhatsAppService(config_repo, account_repo, branch_repo)
