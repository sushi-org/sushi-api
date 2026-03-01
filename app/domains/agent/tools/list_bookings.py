from __future__ import annotations

from typing import Any

from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.company.services.booking_service import BookingService


class ListBookingsTool(BaseTool):
    def __init__(self, booking_service: BookingService) -> None:
        self._booking_svc = booking_service

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

        bookings = await self._booking_svc.list_for_customer(
            branch_id=context.branch_id,
            customer_phone=phone,
        )

        if not bookings:
            return {"bookings": [], "message": "No upcoming bookings found for this customer."}

        # service and staff are eager-loaded — no N+1
        return {"bookings": [
            {
                "booking_id": str(b.id),
                "service": b.service.name if b.service else "Unknown",
                "staff": b.staff.name if b.staff else "Unknown",
                "date": b.date.isoformat(),
                "start_time": b.start_time.strftime("%H:%M"),
                "end_time": b.end_time.strftime("%H:%M"),
                "duration_minutes": b.duration_minutes,
                "price": float(b.price),
                "currency": b.currency,
                "status": b.status.value,
            }
            for b in bookings
        ]}
