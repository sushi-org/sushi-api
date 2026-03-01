from __future__ import annotations

import dataclasses
import datetime as _dt
from uuid import UUID

from app.domains.company.models import OverrideType
from app.domains.company.repositories.availability_override import AvailabilityOverrideRepository
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository


@dataclasses.dataclass
class SlotValidationResult:
    valid: bool
    error_code: str | None = None
    error_message: str | None = None
    end_time: _dt.time | None = None
    duration: int | None = None
    price: float | None = None
    currency: str | None = None


@dataclasses.dataclass
class AvailabilityResult:
    service_name: str
    duration_minutes: int
    slots_by_date: dict[str, list[dict]]


class SchedulingService:
    """Single source of truth for slot computation and validation.

    Consolidates logic previously duplicated across CheckAvailabilityTool,
    BookAppointmentTool, and EditBookingTool. Respects AvailabilityOverride
    (blocked days and modified hours).
    """

    def __init__(
        self,
        availability_repo: StaffAvailabilityRepository,
        override_repo: AvailabilityOverrideRepository,
        booking_repo: BookingRepository,
        service_repo: ServiceRepository,
    ) -> None:
        self._availability_repo = availability_repo
        self._override_repo = override_repo
        self._booking_repo = booking_repo
        self._service_repo = service_repo

    async def check_availability(
        self,
        service_id: UUID,
        branch_id: UUID,
        date_from: _dt.date,
        date_to: _dt.date,
        staff_id: UUID | None = None,
    ) -> AvailabilityResult:
        """Return available slots for a service across a date range."""
        service = await self._service_repo.get_by_id(service_id)
        if service is None:
            raise ValueError(f"Service {service_id} not found")

        candidates = [staff_id] if staff_id else None
        rows = await self._availability_repo.list_staff_schedule_context(
            candidates, service_id, branch_id
        )
        if not rows:
            return AvailabilityResult(
                service_name=service.name,
                duration_minutes=service.default_duration_minutes,
                slots_by_date={},
            )

        # Build lookup structures
        avail_map: dict[UUID, dict[int, list[tuple[_dt.time, _dt.time]]]] = {}
        staff_svc_map: dict[UUID, object] = {}
        staff_name_map: dict[UUID, str] = {}

        for staff_svc, avail_window, staff_name in rows:
            sid = staff_svc.staff_id
            staff_svc_map[sid] = staff_svc
            staff_name_map[sid] = staff_name
            avail_map.setdefault(sid, {}).setdefault(avail_window.day_of_week, []).append(
                (avail_window.start_time, avail_window.end_time)
            )

        valid_candidates = list(staff_svc_map.keys())

        # Fetch bookings for all candidates
        all_bookings = await self._booking_repo.list_by_staff_ids_date_range(
            valid_candidates, branch_id, date_from, date_to
        )
        booked_map: dict[tuple[UUID, _dt.date], list[tuple[_dt.time, _dt.time]]] = {}
        for b in all_bookings:
            booked_map.setdefault((b.staff_id, b.date), []).append((b.start_time, b.end_time))

        # Compute free windows per date
        result_by_date: dict[str, list[dict]] = {}
        current_date = date_from
        while current_date <= date_to:
            day_of_week = current_date.weekday()
            date_str = current_date.isoformat()
            staff_avail = []

            for sid in valid_candidates:
                staff_svc = staff_svc_map[sid]
                duration = staff_svc.duration_override or service.default_duration_minutes
                windows = await self._resolve_windows(sid, branch_id, current_date, day_of_week, avail_map)
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

        return AvailabilityResult(
            service_name=service.name,
            duration_minutes=service.default_duration_minutes,
            slots_by_date=result_by_date,
        )

    async def validate_slot(
        self,
        staff_id: UUID,
        branch_id: UUID,
        date: _dt.date,
        start_time: _dt.time,
        end_time: _dt.time,
        exclude_booking_id: UUID | None = None,
    ) -> SlotValidationResult:
        """Validate a specific slot. Respects AvailabilityOverride."""
        # Check override first
        override = await self._override_repo.get_for_staff_branch_date(staff_id, branch_id, date)
        if override is not None:
            if override.type == OverrideType.blocked:
                return SlotValidationResult(
                    valid=False,
                    error_code="staff_unavailable",
                    error_message=f"The staff member is not available on {date.isoformat()}.",
                )
            # Modified hours: use override window
            windows: list[tuple[_dt.time, _dt.time]] = []
            if override.start_time and override.end_time:
                windows = [(override.start_time, override.end_time)]
        else:
            # Regular weekly schedule
            day_of_week = date.weekday()
            avail_rows = await self._availability_repo.list_by_staff_branch_day(
                staff_id, branch_id, day_of_week
            )
            windows = [(w.start_time, w.end_time) for w in avail_rows]

        if not windows:
            return SlotValidationResult(
                valid=False,
                error_code="staff_unavailable",
                error_message=f"The staff member is not available on {date.strftime('%A')}s.",
            )

        slot_covered = any(
            w_start <= start_time and w_end >= end_time
            for w_start, w_end in windows
        )
        if not slot_covered:
            window_strs = [
                f"{ws.strftime('%H:%M')}-{we.strftime('%H:%M')}" for ws, we in windows
            ]
            return SlotValidationResult(
                valid=False,
                error_code="outside_hours",
                error_message=(
                    f"The requested time {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} "
                    f"is outside the staff's available hours ({', '.join(window_strs)})."
                ),
            )

        overlapping = await self._booking_repo.find_overlapping(
            staff_id=staff_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            exclude_booking_id=exclude_booking_id,
        )
        if overlapping:
            return SlotValidationResult(
                valid=False,
                error_code="slot_unavailable",
                error_message="This slot is no longer available.",
            )

        return SlotValidationResult(valid=True, end_time=end_time)

    async def _resolve_windows(
        self,
        staff_id: UUID,
        branch_id: UUID,
        date: _dt.date,
        day_of_week: int,
        avail_map: dict[UUID, dict[int, list[tuple[_dt.time, _dt.time]]]],
    ) -> list[tuple[_dt.time, _dt.time]]:
        """Return effective availability windows for a staff member on a date,
        respecting AvailabilityOverride."""
        override = await self._override_repo.get_for_staff_branch_date(staff_id, branch_id, date)
        if override is not None:
            if override.type == OverrideType.blocked:
                return []
            if override.type == OverrideType.modified and override.start_time and override.end_time:
                return [(override.start_time, override.end_time)]
        return avail_map.get(staff_id, {}).get(day_of_week, [])


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
