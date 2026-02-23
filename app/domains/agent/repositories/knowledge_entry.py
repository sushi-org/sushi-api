from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agent.models import KnowledgeEntry, KnowledgeEntryStatus
from app.domains.company.repositories.base import BaseRepository


class KnowledgeEntryRepository(BaseRepository[KnowledgeEntry]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, KnowledgeEntry)

    async def list_active_by_agent(self, agent_id: UUID) -> list[KnowledgeEntry]:
        stmt = (
            select(KnowledgeEntry)
            .where(KnowledgeEntry.agent_id == agent_id, KnowledgeEntry.status == KnowledgeEntryStatus.active)
            .order_by(KnowledgeEntry.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_agent(self, agent_id: UUID) -> list[KnowledgeEntry]:
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.agent_id == agent_id).order_by(KnowledgeEntry.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
