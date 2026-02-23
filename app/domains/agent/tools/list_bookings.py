from __future__ import annotations

from typing import Any

from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff import StaffRepository


class ListBookingsTool(BaseTool):
    def __init__(
        self,
        booking_repo: BookingRepository,
        service_repo: ServiceRepository,
        staff_repo: StaffRepository,
    ) -> None:
        self._booking_repo = booking_repo
        self._service_repo = service_repo
        self._staff_repo = staff_repo

    @property
    def name(self) -> str:
        return "list_bookings"

    @property
    def description(self) -> str:
        return (
            "Look up existing bookings for the current customer. "
            "Use this before cancelling or editing a booking. "
            "The customer is automatically identified — no phone number needed."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict:
        phone = context.customer_phone
        if not phone:
            return {"error": "missing_phone", "message": "Unable to identify the customer."}

        bookings = await self._booking_repo.list_by_customer_phone(
            branch_id=context.branch_id,
            customer_phone=phone,
        )

        if not bookings:
            return {"bookings": [], "message": "No upcoming bookings found for this customer."}

        results = []
        for b in bookings:
            service = await self._service_repo.get_by_id(b.service_id)
            staff = await self._staff_repo.get_by_id(b.staff_id)
            results.append({
                "booking_id": str(b.id),
                "service": service.name if service else "Unknown",
                "staff": staff.name if staff else "Unknown",
                "date": b.date.isoformat(),
                "start_time": b.start_time.strftime("%H:%M"),
                "end_time": b.end_time.strftime("%H:%M"),
                "duration_minutes": b.duration_minutes,
                "price": float(b.price),
                "currency": b.currency,
                "status": b.status.value,
            })

        return {"bookings": results}
