from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.models import Branch
from app.domains.company.repositories.base import BaseRepository


class BranchRepository(BaseRepository[Branch]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Branch)

    async def list_by_company(self, company_id: UUID) -> list[Branch]:
        return await self.list_by(company_id=company_id)
