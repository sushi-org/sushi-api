from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.repositories.base import BaseRepository
from app.domains.whatsapp.models import WhatsAppAccount


class WhatsAppAccountRepository(BaseRepository[WhatsAppAccount]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WhatsAppAccount)

    async def get_by_phone_number_id(self, phone_number_id: str) -> WhatsAppAccount | None:
        stmt = select(WhatsAppAccount).where(WhatsAppAccount.phone_number_id == phone_number_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_branch_id(self, branch_id: UUID) -> WhatsAppAccount | None:
        stmt = select(WhatsAppAccount).where(WhatsAppAccount.branch_id == branch_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
