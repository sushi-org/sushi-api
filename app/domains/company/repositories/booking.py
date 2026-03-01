from __future__ import annotations

import datetime
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.models import Booking, BookingStatus
from app.domains.company.repositories.base import BaseRepository


class BookingRepository(BaseRepository[Booking]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Booking)

    async def auto_complete_past_bookings(self, company_id: UUID, *, branch_id: UUID | None = None) -> int:
        """Mark confirmed bookings with a date before today as completed."""
        conditions = [
            Booking.company_id == company_id,
            Booking.status == BookingStatus.confirmed,
            Booking.date < datetime.date.today(),
        ]
        if branch_id is not None:
            conditions.append(Booking.branch_id == branch_id)

        stmt = (
            update(Booking)
            .where(and_(*conditions))
            .values(status=BookingStatus.completed)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def list_by_company(self, company_id: UUID, *, branch_id: UUID | None = None) -> list[Booking]:
        await self.auto_complete_past_bookings(company_id, branch_id=branch_id)
        filters: dict = {"company_id": company_id}
        if branch_id is not None:
            filters["branch_id"] = branch_id
        return await self.list_by(**filters)

    async def find_overlapping(
        self,
        staff_id: UUID,
        date: datetime.date,
        start_time: datetime.time,
        end_time: datetime.time,
        exclude_booking_id: UUID | None = None,
    ) -> list[Booking]:
        """Find confirmed bookings that overlap the given time window."""
        conditions = [
            Booking.staff_id == staff_id,
            Booking.date == date,
            Booking.status == BookingStatus.confirmed,
            Booking.start_time < end_time,
            Booking.end_time > start_time,
        ]
        if exclude_booking_id is not None:
            conditions.append(Booking.id != exclude_booking_id)

        stmt = select(Booking).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_customer_phone(
        self,
        branch_id: UUID,
        customer_phone: str,
        *,
        status: BookingStatus | None = BookingStatus.confirmed,
    ) -> list[Booking]:
        """All bookings for a customer at a branch, optionally filtered by status."""
        conditions = [
            Booking.branch_id == branch_id,
            Booking.customer_phone == customer_phone,
        ]
        if status is not None:
            conditions.append(Booking.status == status)

        stmt = (
            select(Booking)
            .where(and_(*conditions))
            .order_by(Booking.date.desc(), Booking.start_time.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_staff_date_range(
        self,
        staff_id: UUID,
        branch_id: UUID,
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[Booking]:
        """All confirmed bookings for a staff member at a branch within a date range."""
        stmt = (
            select(Booking)
            .where(
                and_(
                    Booking.staff_id == staff_id,
                    Booking.branch_id == branch_id,
                    Booking.status == BookingStatus.confirmed,
                    Booking.date >= date_from,
                    Booking.date <= date_to,
                )
            )
            .order_by(Booking.date, Booking.start_time)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_staff_ids_date_range(
        self,
        staff_ids: list[UUID],
        branch_id: UUID,
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[Booking]:
        """All confirmed bookings for multiple staff members at a branch within a date range."""
        if not staff_ids:
            return []
        stmt = select(Booking).where(
            and_(
                Booking.staff_id.in_(staff_ids),
                Booking.branch_id == branch_id,
                Booking.status == BookingStatus.confirmed,
                Booking.date >= date_from,
                Booking.date <= date_to,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
