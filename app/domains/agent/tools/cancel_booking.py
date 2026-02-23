from __future__ import annotations

from typing import Any
from uuid import UUID

from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.company.models import BookingStatus
from app.domains.company.repositories.booking import BookingRepository


class CancelBookingTool(BaseTool):
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    @property
    def name(self) -> str:
        return "cancel_booking"

    @property
    def description(self) -> str:
        return "Cancel an existing confirmed booking by its ID."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "booking_id": {
                    "type": "string",
                    "description": "UUID of the booking to cancel",
                },
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
                "message": f"Booking cannot be cancelled — current status is '{booking.status.value}'.",
            }

        await self._booking_repo.update(booking_id, status=BookingStatus.cancelled)

        return {
            "booking_id": str(booking_id),
            "status": "cancelled",
            "message": "Booking has been cancelled successfully.",
        }
