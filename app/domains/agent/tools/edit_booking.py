from __future__ import annotations

import datetime as _dt
from typing import Any
from uuid import UUID

from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.company.models import BookingStatus
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff import StaffRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository
from app.domains.company.repositories.staff_service import StaffServiceRepository


class EditBookingTool(BaseTool):
    def __init__(
        self,
        booking_repo: BookingRepository,
        service_repo: ServiceRepository,
        staff_repo: StaffRepository,
        staff_service_repo: StaffServiceRepository,
        staff_availability_repo: StaffAvailabilityRepository,
    ) -> None:
        self._booking_repo = booking_repo
        self._service_repo = service_repo
        self._staff_repo = staff_repo
        self._staff_service_repo = staff_service_repo
        self._availability_repo = staff_availability_repo

    @property
    def name(self) -> str:
        return "edit_booking"

    @property
    def description(self) -> str:
        return (
            "Reschedule or modify an existing confirmed booking. "
            "You can change the date, time, staff member, or service."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "booking_id": {"type": "string", "description": "UUID of the booking to edit"},
                "date": {"type": "string", "format": "date", "description": "New date (YYYY-MM-DD), omit to keep current"},
                "start_time": {"type": "string", "format": "time", "description": "New start time (HH:MM), omit to keep current"},
                "staff_id": {"type": "string", "description": "New staff UUID, omit to keep current"},
                "service_id": {"type": "string", "description": "New service UUID, omit to keep current"},
            },
            "required": ["booking_id"],
        }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict:
        booking_id = UUID(arguments["booking_id"])

        booking = await self._booking_repo.get_by_id(booking_id)
        if booking is None:
            return {"error": "not_found", "message": "Booking not found."}

        if booking.branch_id != context.branch_id:
            return {"error": "not_found", "message": "Booking not found."}

        if booking.status != BookingStatus.confirmed:
            return {
                "error": "invalid_status",
                "message": f"Booking cannot be edited — current status is '{booking.status.value}'.",
            }

        new_date = _dt.date.fromisoformat(arguments["date"]) if "date" in arguments else booking.date
        new_start = _dt.time.fromisoformat(arguments["start_time"]) if "start_time" in arguments else booking.start_time
        new_staff_id = UUID(arguments["staff_id"]) if "staff_id" in arguments else booking.staff_id
        new_service_id = UUID(arguments["service_id"]) if "service_id" in arguments else booking.service_id

        staff_svc = await self._staff_service_repo.get_by_staff_and_service(new_staff_id, new_service_id)
        if staff_svc is None:
            return {"error": "invalid_assignment", "message": "Staff is not assigned to this service."}

        service = await self._service_repo.get_by_id(new_service_id)
        if service is None:
            return {"error": "service_not_found", "message": "Service not found."}

        duration = staff_svc.duration_override if staff_svc.duration_override is not None else service.default_duration_minutes
        price = staff_svc.price_override if staff_svc.price_override is not None else service.default_price
        new_end = (_dt.datetime.combine(_dt.date.today(), new_start) + _dt.timedelta(minutes=duration)).time()

        # Verify staff has an availability window covering the requested slot
        day_of_week = new_date.weekday()
        windows = await self._availability_repo.list_by_staff_branch_day(
            new_staff_id, context.branch_id, day_of_week
        )
        if not windows:
            return {
                "error": "staff_unavailable",
                "message": f"The staff member is not available on {new_date.strftime('%A')}s.",
            }

        slot_covered = any(
            w.start_time <= new_start and w.end_time >= new_end
            for w in windows
        )
        if not slot_covered:
            window_strs = [f"{w.start_time.strftime('%H:%M')}-{w.end_time.strftime('%H:%M')}" for w in windows]
            return {
                "error": "outside_hours",
                "message": (
                    f"The requested time {new_start.strftime('%H:%M')}-{new_end.strftime('%H:%M')} "
                    f"is outside the staff's available hours ({', '.join(window_strs)})."
                ),
            }

        # Check for overlapping bookings (excluding this one)
        overlapping = await self._booking_repo.find_overlapping(
            staff_id=new_staff_id,
            date=new_date,
            start_time=new_start,
            end_time=new_end,
            exclude_booking_id=booking_id,
        )
        if overlapping:
            return {"error": "slot_unavailable", "message": "The new slot is not available — another booking exists at that time."}

        await self._booking_repo.update(
            booking_id,
            date=new_date,
            start_time=new_start,
            end_time=new_end,
            staff_id=new_staff_id,
            service_id=new_service_id,
            duration_minutes=duration,
            price=price,
        )

        staff = await self._staff_repo.get_by_id(new_staff_id)

        return {
            "booking_id": str(booking_id),
            "service": service.name,
            "staff": staff.name if staff else "Unknown",
            "date": new_date.isoformat(),
            "start_time": new_start.strftime("%H:%M"),
            "end_time": new_end.strftime("%H:%M"),
            "duration_minutes": duration,
            "price": float(price),
            "currency": service.currency,
            "status": "confirmed",
            "message": "Booking has been updated successfully.",
        }
