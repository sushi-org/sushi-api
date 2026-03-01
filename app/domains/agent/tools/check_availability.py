from __future__ import annotations

import datetime as _dt
from typing import Any
from uuid import UUID

from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository


class CheckAvailabilityTool(BaseTool):
    def __init__(
        self,
        service_repo: ServiceRepository,
        staff_availability_repo: StaffAvailabilityRepository,
        booking_repo: BookingRepository,
    ) -> None:
        self._service_repo = service_repo
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

        # Resolve candidates: specific staff or None (let the JOIN filter by service_id)
        candidates = [staff_id] if staff_id else None

        # Query 1: JOIN staff_services + staff_availabilities + staff
        rows = await self._availability_repo.list_staff_schedule_context(
            candidates, service_id, context.branch_id
        )
        if not rows:
            return {"availability": [], "message": "No staff assigned to this service"}

        # Build lookup structures from rows
        avail_map: dict[UUID, dict[int, list[tuple[_dt.time, _dt.time]]]] = {}
        staff_svc_map: dict[UUID, Any] = {}
        staff_name_map: dict[UUID, str] = {}

        for staff_svc, avail_window, staff_name in rows:
            sid = staff_svc.staff_id
            staff_svc_map[sid] = staff_svc
            staff_name_map[sid] = staff_name
            avail_map.setdefault(sid, {}).setdefault(avail_window.day_of_week, []).append(
                (avail_window.start_time, avail_window.end_time)
            )

        valid_candidates = list(staff_svc_map.keys())

        # Query 2: all bookings for all valid staff across the full date range
        all_bookings = await self._booking_repo.list_by_staff_ids_date_range(
            valid_candidates, context.branch_id, date_from, date_to
        )
        booked_map: dict[tuple[UUID, _dt.date], list[tuple[_dt.time, _dt.time]]] = {}
        for b in all_bookings:
            booked_map.setdefault((b.staff_id, b.date), []).append((b.start_time, b.end_time))

        # Pure in-memory free-window collection (compressed, not per-slot)
        result_by_date: dict[str, list[dict]] = {}
        current_date = date_from
        while current_date <= date_to:
            day_of_week = current_date.weekday()
            date_str = current_date.isoformat()
            staff_avail = []
            for sid in valid_candidates:
                staff_svc = staff_svc_map[sid]
                duration = staff_svc.duration_override or service.default_duration_minutes
                windows = avail_map.get(sid, {}).get(day_of_week, [])
                booked_ranges = booked_map.get((sid, current_date), [])
                free_windows = []
                for window_start, window_end in windows:
                    for free_start, free_end in _subtract_bookings(window_start, window_end, booked_ranges):
                        window_minutes = (
                            _dt.datetime.combine(_dt.date.min, free_end)
                            - _dt.datetime.combine(_dt.date.min, free_start)
                        ).seconds // 60
                        if window_minutes >= duration:
                            free_windows.append(
                                f"{free_start.strftime('%H:%M')}-{free_end.strftime('%H:%M')}"
                            )
                if free_windows:
                    staff_avail.append({
                        "staff_id": str(sid),
                        "staff_name": staff_name_map.get(sid, "Unknown"),
                        "windows": free_windows,
                    })
            if staff_avail:
                result_by_date[date_str] = staff_avail
            current_date += _dt.timedelta(days=1)

        return {
            "service": service.name,
            "duration_minutes": service.default_duration_minutes,
            "availability": [
                {"date": date, "staff": staff}
                for date, staff in result_by_date.items()
            ],
        }


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
