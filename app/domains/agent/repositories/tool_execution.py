from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agent.models import ToolExecution
from app.domains.company.repositories.base import BaseRepository


class ToolExecutionRepository(BaseRepository[ToolExecution]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ToolExecution)

    async def list_by_conversation(self, conversation_id: UUID) -> list[ToolExecution]:
        stmt = (
            select(ToolExecution)
            .where(ToolExecution.conversation_id == conversation_id)
            .order_by(ToolExecution.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
