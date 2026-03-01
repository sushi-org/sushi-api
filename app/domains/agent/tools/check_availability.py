from __future__ import annotations

import datetime as _dt
from typing import Any
from uuid import UUID

from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.company.services.scheduling_service import SchedulingService


class CheckAvailabilityTool(BaseTool):
    def __init__(self, scheduling_service: SchedulingService) -> None:
        self._scheduling = scheduling_service

    @property
    def name(self) -> str:
        return "check_availability"

    @property
    def description(self) -> str:
        return "Check available appointment slots for a service at this branch."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "service_id": {"type": "string", "description": "UUID of the service"},
                "staff_id": {"type": "string", "description": "UUID of preferred staff, or null for any"},
                "date_from": {"type": "string", "format": "date", "description": "Start of date range (YYYY-MM-DD)"},
                "date_to": {"type": "string", "format": "date", "description": "End of date range (YYYY-MM-DD)"},
            },
            "required": ["service_id", "date_from", "date_to"],
        }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict:
        service_id = UUID(arguments["service_id"])
        staff_id = UUID(arguments["staff_id"]) if arguments.get("staff_id") else None
        date_from = _dt.date.fromisoformat(arguments["date_from"])
        date_to = _dt.date.fromisoformat(arguments["date_to"])

        try:
            result = await self._scheduling.check_availability(
                service_id=service_id,
                branch_id=context.branch_id,
                date_from=date_from,
                date_to=date_to,
                staff_id=staff_id,
            )
        except ValueError as e:
            return {"error": "service_not_found", "message": str(e)}

        if not result.slots_by_date:
            return {"availability": [], "message": "No staff assigned to this service"}

        return {
            "service": result.service_name,
            "duration_minutes": result.duration_minutes,
            "availability": [
                {"date": date, "staff": staff}
                for date, staff in result.slots_by_date.items()
            ],
        }
