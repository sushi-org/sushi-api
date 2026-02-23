from __future__ import annotations

import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.models import AvailabilityOverride
from app.domains.company.repositories.base import BaseRepository


class AvailabilityOverrideRepository(BaseRepository[AvailabilityOverride]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AvailabilityOverride)

    async def list_by_staff(self, staff_id: UUID) -> list[AvailabilityOverride]:
        return await self.list_by(staff_id=staff_id)

    async def get_for_staff_branch_date(
        self, staff_id: UUID, branch_id: UUID, date: datetime.date
    ) -> AvailabilityOverride | None:
        stmt = select(AvailabilityOverride).where(
            and_(
                AvailabilityOverride.staff_id == staff_id,
                AvailabilityOverride.branch_id == branch_id,
                AvailabilityOverride.date == date,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
