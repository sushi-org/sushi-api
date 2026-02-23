from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.models import Company
from app.domains.company.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Company)

    async def get_by_slug(self, slug: str) -> Company | None:
        stmt = select(Company).where(Company.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> Company | None:
        stmt = select(Company).where(Company.domain == domain)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
