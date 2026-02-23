from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agent.models import Agent
from app.domains.company.repositories.base import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Agent)

    async def get_by_branch_id(self, branch_id: UUID) -> Agent | None:
        stmt = select(Agent).where(Agent.branch_id == branch_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
