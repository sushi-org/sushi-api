from __future__ import annotations

import datetime as _dt
from uuid import UUID

from fastapi import HTTPException, status

from app.domains.company.models import Booking, BookingStatus
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.branch import BranchRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository
from app.domains.company.repositories.staff_service import StaffServiceRepository
from app.domains.company.repositories.availability_override import AvailabilityOverrideRepository
from app.domains.company.schemas import BookingCreate, BookingUpdate


class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        staff_service_repo: StaffServiceRepository,
        availability_repo: StaffAvailabilityRepository,
        override_repo: AvailabilityOverrideRepository,
        service_repo: ServiceRepository,
        branch_repo: BranchRepository,
    ) -> None:
        self.booking_repo = booking_repo
        self.staff_service_repo = staff_service_repo
        self.availability_repo = availability_repo
        self.override_repo = override_repo
        self.service_repo = service_repo
        self.branch_repo = branch_repo

    async def list_by_company(self, company_id: UUID, *, branch_id: UUID | None = None) -> list[Booking]:
        return await self.booking_repo.list_by_company(company_id, branch_id=branch_id)

    async def get(self, booking_id: UUID) -> Booking:
        booking = await self.booking_repo.get_by_id(booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        return booking

    async def create(self, company_id: UUID, data: BookingCreate) -> Booking:
        # Resolve staff-service link for price/duration
        staff_svc = await self.staff_service_repo.get_by_staff_and_service(data.staff_id, data.service_id)
        if staff_svc is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff is not assigned to this service",
            )

        service = await self.service_repo.get_by_id(data.service_id)
        if service is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

        duration = staff_svc.duration_override if staff_svc.duration_override is not None else service.default_duration_minutes
        price = staff_svc.price_override if staff_svc.price_override is not None else service.default_price
        currency = service.currency

        start_dt = _dt.datetime.combine(_dt.date.today(), data.start_time)
        end_dt = start_dt + _dt.timedelta(minutes=duration)
        end_time = end_dt.time()

        # Overlap check
        overlapping = await self.booking_repo.find_overlapping(
            staff_id=data.staff_id,
            date=data.date,
            start_time=data.start_time,
            end_time=end_time,
        )
        if overlapping:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Time slot overlaps with an existing confirmed booking",
            )

        return await self.booking_repo.create(
            company_id=company_id,
            branch_id=data.branch_id,
            staff_id=data.staff_id,
            service_id=data.service_id,
            customer_phone=data.customer_phone,
            customer_name=data.customer_name,
            date=data.date,
            start_time=data.start_time,
            end_time=end_time,
            duration_minutes=duration,
            price=price,
            currency=currency,
            booked_via=data.booked_via,
            conversation_id=data.conversation_id,
            notes=data.notes,
        )

    async def update(self, booking_id: UUID, data: BookingUpdate) -> Booking:
        booking = await self.get(booking_id)
        payload = data.model_dump(exclude_unset=True)

        if "status" in payload and payload["status"] == BookingStatus.cancelled:
            payload["cancelled_at"] = _dt.datetime.now(_dt.timezone.utc)

        updated = await self.booking_repo.update(booking_id, **payload)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        return updated
