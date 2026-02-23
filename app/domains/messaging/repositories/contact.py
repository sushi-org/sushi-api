from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.repositories.base import BaseRepository
from app.domains.messaging.models import Contact


class ContactRepository(BaseRepository[Contact]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Contact)

    async def get_by_company_phone(self, company_id: UUID, phone: str) -> Contact | None:
        stmt = select(Contact).where(Contact.company_id == company_id, Contact.phone == phone)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
