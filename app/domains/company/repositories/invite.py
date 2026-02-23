from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.domains.company.models import Invite, InviteStatus
from app.domains.company.repositories.base import BaseRepository


class InviteRepository(BaseRepository[Invite]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Invite)

    async def list_active_by_company(self, company_id: UUID) -> list[Invite]:
        stmt = select(Invite).where(
            and_(Invite.company_id == company_id, Invite.status == InviteStatus.active)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_by_code(self, code: str) -> Invite | None:
        stmt = select(Invite).where(
            and_(
                Invite.code == code,
                Invite.status == InviteStatus.active,
                Invite.expires_at > func.now(),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
