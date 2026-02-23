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


class CheckAvailabilityTool(BaseTool):
    def __init__(
        self,
        service_repo: ServiceRepository,
        staff_repo: StaffRepository,
        staff_service_repo: StaffServiceRepository,
        staff_availability_repo: StaffAvailabilityRepository,
        booking_repo: BookingRepository,
    ) -> None:
        self._service_repo = service_repo
        self._staff_repo = staff_repo
        self._staff_service_repo = staff_service_repo
        self._availability_repo = staff_availability_repo
        self._booking_repo = booking_repo

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

        service = await self._service_repo.get_by_id(service_id)
        if service is None:
            return {"error": "service_not_found", "message": "Service not found"}

        # Resolve candidate staff
        if staff_id:
            candidates = [staff_id]
        else:
            staff_services = await self._staff_service_repo.list_by(service_id=service_id)
            candidates = [ss.staff_id for ss in staff_services]

        if not candidates:
            return {"slots": [], "message": "No staff assigned to this service"}

        slots: list[dict] = []
        current_date = date_from
        while current_date <= date_to:
            day_of_week = current_date.weekday()

            for sid in candidates:
                staff_svc = await self._staff_service_repo.get_by_staff_and_service(sid, service_id)
                if staff_svc is None:
                    continue

                duration = staff_svc.duration_override or service.default_duration_minutes

                windows = await self._availability_repo.list_by_staff_branch_day(
                    sid, context.branch_id, day_of_week
                )
                if not windows:
                    continue

                bookings = await self._booking_repo.list_by_staff_date_range(
                    sid, context.branch_id, current_date, current_date
                )
                booked_ranges = [(b.start_time, b.end_time) for b in bookings]

                staff_obj = await self._staff_repo.get_by_id(sid)
                staff_name = staff_obj.name if staff_obj else "Unknown"

                for window in windows:
                    free_ranges = _subtract_bookings(window.start_time, window.end_time, booked_ranges)
                    for free_start, free_end in free_ranges:
                        slot_start = free_start
                        while True:
                            slot_end_dt = _dt.datetime.combine(_dt.date.today(), slot_start) + _dt.timedelta(minutes=duration)
                            slot_end = slot_end_dt.time()
                            if slot_end > free_end:
                                break
                            slots.append({
                                "date": current_date.isoformat(),
                                "staff_id": str(sid),
                                "staff_name": staff_name,
                                "start": slot_start.strftime("%H:%M"),
                                "end": slot_end.strftime("%H:%M"),
                            })
                            # Slide by 30-minute increments
                            slot_start = (_dt.datetime.combine(_dt.date.today(), slot_start) + _dt.timedelta(minutes=30)).time()

            current_date += _dt.timedelta(days=1)

        return {"slots": slots}


def _subtract_bookings(
    window_start: _dt.time,
    window_end: _dt.time,
    bookings: list[tuple[_dt.time, _dt.time]],
) -> list[tuple[_dt.time, _dt.time]]:
    """Subtract booked ranges from a single availability window, returning free sub-windows."""
    free: list[tuple[_dt.time, _dt.time]] = [(window_start, window_end)]

    for b_start, b_end in sorted(bookings):
        new_free: list[tuple[_dt.time, _dt.time]] = []
        for f_start, f_end in free:
            if b_end <= f_start or b_start >= f_end:
                new_free.append((f_start, f_end))
            else:
                if f_start < b_start:
                    new_free.append((f_start, b_start))
                if b_end < f_end:
                    new_free.append((b_end, f_end))
        free = new_free

    return free
