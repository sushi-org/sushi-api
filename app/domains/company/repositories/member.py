from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.models import Member
from app.domains.company.repositories.base import BaseRepository


class MemberRepository(BaseRepository[Member]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Member)

    async def list_by_company(self, company_id: UUID) -> list[Member]:
        return await self.list_by(company_id=company_id)

    async def get_by_email(self, email: str) -> Member | None:
        stmt = select(Member).where(Member.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
