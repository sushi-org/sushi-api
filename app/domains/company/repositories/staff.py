from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.models import Staff
from app.domains.company.repositories.base import BaseRepository


class StaffRepository(BaseRepository[Staff]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Staff)

    async def list_by_company(self, company_id: UUID) -> list[Staff]:
        return await self.list_by(company_id=company_id)
