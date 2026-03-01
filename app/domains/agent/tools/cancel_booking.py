from __future__ import annotations

from typing import Any
from uuid import UUID

from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.company.services.booking_service import BookingService


class CancelBookingTool(BaseTool):
    def __init__(self, booking_service: BookingService) -> None:
        self._booking_svc = booking_service

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
        return await self._booking_svc.cancel_from_agent(booking_id, context.branch_id)
