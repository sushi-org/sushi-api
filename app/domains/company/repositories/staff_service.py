from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.models import StaffService
from app.domains.company.repositories.base import BaseRepository


class StaffServiceRepository(BaseRepository[StaffService]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StaffService)

    async def list_by_staff(self, staff_id: UUID) -> list[StaffService]:
        return await self.list_by(staff_id=staff_id)

    async def get_by_staff_and_service(self, staff_id: UUID, service_id: UUID) -> StaffService | None:
        stmt = select(StaffService).where(
            and_(StaffService.staff_id == staff_id, StaffService.service_id == service_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_staff_and_service(self, staff_id: UUID, service_id: UUID) -> bool:
        row = await self.get_by_staff_and_service(staff_id, service_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True
