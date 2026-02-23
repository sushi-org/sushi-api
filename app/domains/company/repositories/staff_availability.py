from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.models import StaffAvailability
from app.domains.company.repositories.base import BaseRepository


class StaffAvailabilityRepository(BaseRepository[StaffAvailability]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StaffAvailability)

    async def list_by_staff(self, staff_id: UUID) -> list[StaffAvailability]:
        return await self.list_by(staff_id=staff_id)

    async def list_by_staff_and_branch(self, staff_id: UUID, branch_id: UUID) -> list[StaffAvailability]:
        stmt = select(StaffAvailability).where(
            and_(StaffAvailability.staff_id == staff_id, StaffAvailability.branch_id == branch_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_staff_branch_day(
        self, staff_id: UUID, branch_id: UUID, day_of_week: int
    ) -> list[StaffAvailability]:
        stmt = select(StaffAvailability).where(
            and_(
                StaffAvailability.staff_id == staff_id,
                StaffAvailability.branch_id == branch_id,
                StaffAvailability.day_of_week == day_of_week,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def replace_for_staff_branch(
        self, staff_id: UUID, branch_id: UUID, slots: list[dict]
    ) -> list[StaffAvailability]:
        """Delete all existing slots for this staff-branch pair and insert new ones."""
        stmt = delete(StaffAvailability).where(
            and_(StaffAvailability.staff_id == staff_id, StaffAvailability.branch_id == branch_id)
        )
        await self.session.execute(stmt)

        rows: list[StaffAvailability] = []
        for slot in slots:
            row = StaffAvailability(staff_id=staff_id, branch_id=branch_id, **slot)
            self.session.add(row)
            rows.append(row)
        await self.session.flush()
        return rows
