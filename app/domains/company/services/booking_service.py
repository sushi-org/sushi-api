from __future__ import annotations

import dataclasses
import datetime as _dt
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status

from app.domains.company.models import Booking, BookingStatus
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.branch import BranchRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff import StaffRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository
from app.domains.company.repositories.staff_service import StaffServiceRepository
from app.domains.company.repositories.availability_override import AvailabilityOverrideRepository
from app.domains.company.schemas import BookingCreate, BookingUpdate

if TYPE_CHECKING:
    from app.domains.company.services.scheduling_service import SchedulingService


@dataclasses.dataclass
class AgentBookingResult:
    """Successful booking result returned to agent tools."""

    booking_id: UUID
    service_name: str
    staff_name: str
    date: _dt.date
    start_time: _dt.time
    end_time: _dt.time
    duration_minutes: int
    price: float
    currency: str


class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        staff_service_repo: StaffServiceRepository,
        availability_repo: StaffAvailabilityRepository,
        override_repo: AvailabilityOverrideRepository,
        service_repo: ServiceRepository,
        branch_repo: BranchRepository,
        staff_repo: StaffRepository | None = None,
    ) -> None:
        self.booking_repo = booking_repo
        self.staff_service_repo = staff_service_repo
        self.availability_repo = availability_repo
        self.override_repo = override_repo
        self.service_repo = service_repo
        self.branch_repo = branch_repo
        self.staff_repo = staff_repo

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

    # ── Agent-facing methods ─────────────────────────────────────────────

    async def create_from_agent(
        self,
        branch_id: UUID,
        company_id: UUID,
        staff_id: UUID,
        service_id: UUID,
        date: _dt.date,
        start_time: _dt.time,
        customer_phone: str,
        customer_name: str,
        conversation_id: UUID,
        scheduling_service: SchedulingService,
    ) -> AgentBookingResult | dict:
        """Create a booking from an agent tool call.

        Returns AgentBookingResult on success, or an error dict on failure.
        Delegates slot validation to SchedulingService.
        """
        staff_svc = await self.staff_service_repo.get_by_staff_and_service(staff_id, service_id)
        if staff_svc is None:
            return {"error": "invalid_assignment", "message": "Staff is not assigned to this service."}

        service = await self.service_repo.get_by_id(service_id)
        if service is None:
            return {"error": "service_not_found", "message": "Service not found."}

        duration = staff_svc.duration_override if staff_svc.duration_override is not None else service.default_duration_minutes
        price = staff_svc.price_override if staff_svc.price_override is not None else service.default_price
        end_dt = _dt.datetime.combine(_dt.date.today(), start_time) + _dt.timedelta(minutes=duration)
        end_time = end_dt.time()

        validation = await scheduling_service.validate_slot(
            staff_id=staff_id,
            branch_id=branch_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
        )
        if not validation.valid:
            return {"error": validation.error_code, "message": validation.error_message}

        booking = await self.booking_repo.create(
            company_id=company_id,
            branch_id=branch_id,
            staff_id=staff_id,
            service_id=service_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
            date=date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration,
            price=price,
            currency=service.currency,
            booked_via="agent",
            conversation_id=conversation_id,
        )

        staff_name = "Unknown"
        if self.staff_repo:
            staff = await self.staff_repo.get_by_id(staff_id)
            if staff:
                staff_name = staff.name

        return AgentBookingResult(
            booking_id=booking.id,
            service_name=service.name,
            staff_name=staff_name,
            date=date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration,
            price=float(price),
            currency=service.currency,
        )

    async def edit_from_agent(
        self,
        booking_id: UUID,
        branch_id: UUID,
        scheduling_service: SchedulingService,
        *,
        date: _dt.date | None = None,
        start_time: _dt.time | None = None,
        staff_id: UUID | None = None,
        service_id: UUID | None = None,
    ) -> AgentBookingResult | dict:
        """Edit a booking from an agent tool call.

        Returns AgentBookingResult on success, or an error dict on failure.
        """
        booking = await self.booking_repo.get_by_id(booking_id)
        if booking is None or booking.branch_id != branch_id:
            return {"error": "not_found", "message": "Booking not found."}

        if booking.status != BookingStatus.confirmed:
            return {
                "error": "invalid_status",
                "message": f"Booking cannot be edited — current status is '{booking.status.value}'.",
            }

        new_date = date if date is not None else booking.date
        new_start = start_time if start_time is not None else booking.start_time
        new_staff_id = staff_id if staff_id is not None else booking.staff_id
        new_service_id = service_id if service_id is not None else booking.service_id

        staff_svc = await self.staff_service_repo.get_by_staff_and_service(new_staff_id, new_service_id)
        if staff_svc is None:
            return {"error": "invalid_assignment", "message": "Staff is not assigned to this service."}

        service = await self.service_repo.get_by_id(new_service_id)
        if service is None:
            return {"error": "service_not_found", "message": "Service not found."}

        duration = staff_svc.duration_override if staff_svc.duration_override is not None else service.default_duration_minutes
        price = staff_svc.price_override if staff_svc.price_override is not None else service.default_price
        new_end = (_dt.datetime.combine(_dt.date.today(), new_start) + _dt.timedelta(minutes=duration)).time()

        validation = await scheduling_service.validate_slot(
            staff_id=new_staff_id,
            branch_id=branch_id,
            date=new_date,
            start_time=new_start,
            end_time=new_end,
            exclude_booking_id=booking_id,
        )
        if not validation.valid:
            return {"error": validation.error_code, "message": validation.error_message}

        await self.booking_repo.update(
            booking_id,
            date=new_date,
            start_time=new_start,
            end_time=new_end,
            staff_id=new_staff_id,
            service_id=new_service_id,
            duration_minutes=duration,
            price=price,
        )

        staff_name = "Unknown"
        if self.staff_repo:
            staff = await self.staff_repo.get_by_id(new_staff_id)
            if staff:
                staff_name = staff.name

        return AgentBookingResult(
            booking_id=booking_id,
            service_name=service.name,
            staff_name=staff_name,
            date=new_date,
            start_time=new_start,
            end_time=new_end,
            duration_minutes=duration,
            price=float(price),
            currency=service.currency,
        )

    async def cancel_from_agent(self, booking_id: UUID, branch_id: UUID) -> dict:
        """Cancel a booking from an agent tool call. Returns a result dict."""
        booking = await self.booking_repo.get_by_id(booking_id)
        if booking is None or booking.branch_id != branch_id:
            return {"error": "not_found", "message": "Booking not found."}

        if booking.status != BookingStatus.confirmed:
            return {
                "error": "invalid_status",
                "message": f"Booking cannot be cancelled — current status is '{booking.status.value}'.",
            }

        await self.booking_repo.update(booking_id, status=BookingStatus.cancelled)
        return {
            "booking_id": str(booking_id),
            "status": "cancelled",
            "message": "Booking has been cancelled successfully.",
        }

    async def list_for_customer(self, branch_id: UUID, customer_phone: str) -> list[Booking]:
        """List bookings with service and staff eager-loaded (no N+1)."""
        return await self.booking_repo.list_by_customer_phone_with_relations(
            branch_id, customer_phone
        )
