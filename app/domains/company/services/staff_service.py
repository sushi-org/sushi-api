from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.domains.company.models import (
    AvailabilityOverride,
    Staff,
    StaffAvailability,
    StaffService as StaffServiceModel,
)
from app.domains.company.repositories.availability_override import AvailabilityOverrideRepository
from app.domains.company.repositories.branch import BranchRepository
from app.domains.company.repositories.staff import StaffRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository
from app.domains.company.repositories.staff_service import StaffServiceRepository
from app.domains.company.schemas import (
    AvailabilityOverrideCreate,
    StaffAvailabilityBulkSet,
    StaffCreate,
    StaffServiceCreate,
    StaffServiceUpdate,
    StaffUpdate,
)


class StaffService:
    def __init__(
        self,
        staff_repo: StaffRepository,
        staff_service_repo: StaffServiceRepository,
        availability_repo: StaffAvailabilityRepository,
        override_repo: AvailabilityOverrideRepository,
        branch_repo: BranchRepository,
    ) -> None:
        self.staff_repo = staff_repo
        self.staff_service_repo = staff_service_repo
        self.availability_repo = availability_repo
        self.override_repo = override_repo
        self.branch_repo = branch_repo

    # ── Staff CRUD ───────────────────────────────────────────────────

    async def list_staff(self, company_id: UUID) -> list[Staff]:
        return await self.staff_repo.list_by_company(company_id)

    async def get_staff(self, staff_id: UUID) -> Staff:
        staff = await self.staff_repo.get_by_id(staff_id)
        if staff is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
        return staff

    async def create_staff(self, company_id: UUID, data: StaffCreate) -> Staff:
        return await self.staff_repo.create(company_id=company_id, **data.model_dump())

    async def update_staff(self, staff_id: UUID, data: StaffUpdate) -> Staff:
        updated = await self.staff_repo.update(staff_id, **data.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
        return updated

    async def delete_staff(self, staff_id: UUID) -> None:
        deleted = await self.staff_repo.delete(staff_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

    # ── Staff Services ───────────────────────────────────────────────

    async def list_staff_services(self, staff_id: UUID) -> list[StaffServiceModel]:
        return await self.staff_service_repo.list_by_staff(staff_id)

    async def assign_service(self, staff_id: UUID, data: StaffServiceCreate) -> StaffServiceModel:
        existing = await self.staff_service_repo.get_by_staff_and_service(staff_id, data.service_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Staff already has this service assigned",
            )
        return await self.staff_service_repo.create(
            staff_id=staff_id,
            service_id=data.service_id,
            price_override=data.price_override,
            duration_override=data.duration_override,
        )

    async def update_staff_service(
        self, staff_id: UUID, service_id: UUID, data: StaffServiceUpdate
    ) -> StaffServiceModel:
        row = await self.staff_service_repo.get_by_staff_and_service(staff_id, service_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff service assignment not found"
            )
        updated = await self.staff_service_repo.update(row.id, **data.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff service not found")
        return updated

    async def remove_service(self, staff_id: UUID, service_id: UUID) -> None:
        deleted = await self.staff_service_repo.delete_by_staff_and_service(staff_id, service_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff service assignment not found"
            )

    # ── Availability ─────────────────────────────────────────────────

    async def get_availability(self, staff_id: UUID) -> list[StaffAvailability]:
        return await self.availability_repo.list_by_staff(staff_id)

    async def set_availability(
        self, staff_id: UUID, data: StaffAvailabilityBulkSet
    ) -> list[StaffAvailability]:
        branch = await self.branch_repo.get_by_id(data.branch_id)
        if branch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

        self._validate_slots_within_operating_hours(branch.operating_hours, data)

        slots = [s.model_dump() for s in data.slots]
        return await self.availability_repo.replace_for_staff_branch(staff_id, data.branch_id, slots)

    async def delete_availability(self, availability_id: UUID) -> None:
        deleted = await self.availability_repo.delete(availability_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Availability slot not found"
            )

    # ── Availability Overrides ───────────────────────────────────────

    async def list_overrides(self, staff_id: UUID) -> list[AvailabilityOverride]:
        return await self.override_repo.list_by_staff(staff_id)

    async def create_override(
        self, staff_id: UUID, data: AvailabilityOverrideCreate
    ) -> AvailabilityOverride:
        return await self.override_repo.create(staff_id=staff_id, **data.model_dump())

    async def delete_override(self, override_id: UUID) -> None:
        deleted = await self.override_repo.delete(override_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Override not found"
            )

    # ── Helpers ──────────────────────────────────────────────────────

    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    @classmethod
    def _validate_slots_within_operating_hours(
        cls, operating_hours: dict, data: StaffAvailabilityBulkSet
    ) -> None:
        for slot in data.slots:
            day_name = cls.DAY_NAMES[slot.day_of_week]
            day_hours = operating_hours.get(day_name)
            if day_hours is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Branch is closed on {day_name}; cannot set availability",
                )
            branch_open = _parse_time(day_hours["open"])
            branch_close = _parse_time(day_hours["close"])
            if slot.start_time < branch_open or slot.end_time > branch_close:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Slot {slot.start_time}-{slot.end_time} on {day_name} "
                        f"exceeds branch hours {day_hours['open']}-{day_hours['close']}"
                    ),
                )


def _parse_time(s: str):
    """Parse 'HH:MM' string into a datetime.time."""
    import datetime as _dt

    parts = s.split(":")
    return _dt.time(int(parts[0]), int(parts[1]))
