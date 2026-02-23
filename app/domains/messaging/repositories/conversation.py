from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domains.company.repositories.base import BaseRepository
from app.domains.messaging.models import Conversation, ConversationStatus, Message


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Conversation)

    async def find_open(self, branch_id: UUID, channel: str, contact_id: UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(
                Conversation.branch_id == branch_id,
                Conversation.channel == channel,
                Conversation.contact_id == contact_id,
                Conversation.status.in_([ConversationStatus.active, ConversationStatus.escalated]),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_company(
        self,
        company_id: UUID,
        branch_id: UUID | None = None,
        status: str | None = None,
        needed_human: bool | None = None,
    ) -> list[Conversation]:
        stmt = select(Conversation).where(Conversation.company_id == company_id)
        if branch_id is not None:
            stmt = stmt.where(Conversation.branch_id == branch_id)
        if needed_human:
            stmt = stmt.where(
                or_(
                    Conversation.status == ConversationStatus.escalated,
                    and_(
                        Conversation.status == ConversationStatus.resolved,
                        Conversation.escalated_at.isnot(None),
                    ),
                )
            )
        elif status is not None:
            stmt = stmt.where(Conversation.status == status)
        stmt = stmt.order_by(Conversation.updated_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_messages(self, conversation_id: UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .options(joinedload(Conversation.contact), joinedload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_message_count(self, conversation_id: UUID) -> int:
        stmt = select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
