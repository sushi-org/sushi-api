from __future__ import annotations

import datetime as _dt
from typing import Any
from uuid import UUID

from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff import StaffRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository
from app.domains.company.repositories.staff_service import StaffServiceRepository


class BookAppointmentTool(BaseTool):
    def __init__(
        self,
        service_repo: ServiceRepository,
        staff_service_repo: StaffServiceRepository,
        booking_repo: BookingRepository,
        staff_repo: StaffRepository,
        staff_availability_repo: StaffAvailabilityRepository,
    ) -> None:
        self._service_repo = service_repo
        self._staff_service_repo = staff_service_repo
        self._booking_repo = booking_repo
        self._staff_repo = staff_repo
        self._availability_repo = staff_availability_repo

    @property
    def name(self) -> str:
        return "book_appointment"

    @property
    def description(self) -> str:
        return "Book a confirmed appointment for the customer."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "service_id": {"type": "string", "description": "UUID of the service"},
                "staff_id": {"type": "string", "description": "UUID of the staff member"},
                "date": {"type": "string", "format": "date", "description": "YYYY-MM-DD"},
                "start_time": {"type": "string", "format": "time", "description": "HH:MM"},
                "customer_name": {"type": "string", "description": "Customer name if provided during conversation"},
            },
            "required": ["service_id", "staff_id", "date", "start_time"],
        }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict:
        service_id = UUID(arguments["service_id"])
        staff_id = UUID(arguments["staff_id"])
        date = _dt.date.fromisoformat(arguments["date"])
        start_time = _dt.time.fromisoformat(arguments["start_time"])
        customer_name = arguments.get("customer_name") or context.customer_name or ""
        customer_phone = context.customer_phone

        staff_svc = await self._staff_service_repo.get_by_staff_and_service(staff_id, service_id)
        if staff_svc is None:
            return {"error": "invalid_assignment", "message": "Staff is not assigned to this service."}

        service = await self._service_repo.get_by_id(service_id)
        if service is None:
            return {"error": "service_not_found", "message": "Service not found."}

        duration = staff_svc.duration_override if staff_svc.duration_override is not None else service.default_duration_minutes
        price = staff_svc.price_override if staff_svc.price_override is not None else service.default_price
        end_dt = _dt.datetime.combine(_dt.date.today(), start_time) + _dt.timedelta(minutes=duration)
        end_time = end_dt.time()

        # Verify staff has an availability window covering the requested slot
        day_of_week = date.weekday()
        windows = await self._availability_repo.list_by_staff_branch_day(
            staff_id, context.branch_id, day_of_week
        )
        if not windows:
            return {
                "error": "staff_unavailable",
                "message": f"The staff member is not available on {date.strftime('%A')}s.",
            }

        slot_covered = any(
            w.start_time <= start_time and w.end_time >= end_time
            for w in windows
        )
        if not slot_covered:
            window_strs = [f"{w.start_time.strftime('%H:%M')}-{w.end_time.strftime('%H:%M')}" for w in windows]
            return {
                "error": "outside_hours",
                "message": (
                    f"The requested time {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} "
                    f"is outside the staff's available hours ({', '.join(window_strs)})."
                ),
            }

        # Check for overlapping bookings
        overlapping = await self._booking_repo.find_overlapping(
            staff_id=staff_id, date=date, start_time=start_time, end_time=end_time
        )
        if overlapping:
            return {"error": "slot_unavailable", "message": "This slot is no longer available."}

        booking = await self._booking_repo.create(
            company_id=context.company_id,
            branch_id=context.branch_id,
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
            conversation_id=context.conversation_id,
        )

        staff = await self._staff_repo.get_by_id(staff_id)

        return {
            "booking_id": str(booking.id),
            "service": service.name,
            "staff": staff.name if staff else "Unknown",
            "date": date.isoformat(),
            "start_time": start_time.strftime("%H:%M"),
            "end_time": end_time.strftime("%H:%M"),
            "duration_minutes": duration,
            "price": float(price),
            "currency": service.currency,
            "status": "confirmed",
        }
