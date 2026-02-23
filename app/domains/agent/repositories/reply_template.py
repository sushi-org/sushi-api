from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agent.models import KnowledgeEntryStatus, ReplyTemplate
from app.domains.company.repositories.base import BaseRepository


class ReplyTemplateRepository(BaseRepository[ReplyTemplate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReplyTemplate)

    async def get_active_by_trigger(self, agent_id: UUID, trigger: str) -> ReplyTemplate | None:
        stmt = select(ReplyTemplate).where(
            ReplyTemplate.agent_id == agent_id,
            ReplyTemplate.trigger == trigger,
            ReplyTemplate.status == KnowledgeEntryStatus.active,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_agent(self, agent_id: UUID) -> list[ReplyTemplate]:
        stmt = select(ReplyTemplate).where(ReplyTemplate.agent_id == agent_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
