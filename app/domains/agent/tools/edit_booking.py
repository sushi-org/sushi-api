from __future__ import annotations

import datetime as _dt
from typing import Any
from uuid import UUID

from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.company.services.booking_service import AgentBookingResult, BookingService
from app.domains.company.services.scheduling_service import SchedulingService


class EditBookingTool(BaseTool):
    def __init__(self, booking_service: BookingService, scheduling_service: SchedulingService) -> None:
        self._booking_svc = booking_service
        self._scheduling_svc = scheduling_service

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

        result = await self._booking_svc.edit_from_agent(
            booking_id=booking_id,
            branch_id=context.branch_id,
            scheduling_service=self._scheduling_svc,
            date=_dt.date.fromisoformat(arguments["date"]) if "date" in arguments else None,
            start_time=_dt.time.fromisoformat(arguments["start_time"]) if "start_time" in arguments else None,
            staff_id=UUID(arguments["staff_id"]) if "staff_id" in arguments else None,
            service_id=UUID(arguments["service_id"]) if "service_id" in arguments else None,
        )

        if isinstance(result, dict):
            return result

        return {
            "booking_id": str(result.booking_id),
            "service": result.service_name,
            "staff": result.staff_name,
            "date": result.date.isoformat(),
            "start_time": result.start_time.strftime("%H:%M"),
            "end_time": result.end_time.strftime("%H:%M"),
            "duration_minutes": result.duration_minutes,
            "price": result.price,
            "currency": result.currency,
            "status": "confirmed",
            "message": "Booking has been updated successfully.",
        }
