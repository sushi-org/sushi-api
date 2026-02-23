from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.repositories.base import BaseRepository
from app.domains.messaging.models import Message


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Message)

    async def exists_by_channel_message_id(self, channel_message_id: str) -> bool:
        stmt = select(func.count()).select_from(Message).where(
            Message.channel_message_id == channel_message_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def get_recent(self, conversation_id: UUID, limit: int = 20) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def count_by_role(self, conversation_id: UUID, role: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id, Message.role == role)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
