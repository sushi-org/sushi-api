from __future__ import annotations

import dataclasses
import datetime as _dt
from typing import Any
from uuid import UUID

from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.company.services.booking_service import AgentBookingResult, BookingService
from app.domains.company.services.scheduling_service import SchedulingService


class BookAppointmentTool(BaseTool):
    def __init__(self, booking_service: BookingService, scheduling_service: SchedulingService) -> None:
        self._booking_svc = booking_service
        self._scheduling_svc = scheduling_service

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

        result = await self._booking_svc.create_from_agent(
            branch_id=context.branch_id,
            company_id=context.company_id,
            staff_id=staff_id,
            service_id=service_id,
            date=date,
            start_time=start_time,
            customer_phone=context.customer_phone,
            customer_name=customer_name,
            conversation_id=context.conversation_id,
            scheduling_service=self._scheduling_svc,
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
        }
