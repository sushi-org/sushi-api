from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.domains.company.dependencies import get_staff_service
from app.domains.company.schemas import (
    AvailabilityOverrideCreate,
    AvailabilityOverrideResponse,
    StaffAvailabilityBulkSet,
    StaffAvailabilityResponse,
    StaffCreate,
    StaffResponse,
    StaffServiceCreate,
    StaffServiceResponse,
    StaffServiceUpdate,
    StaffUpdate,
)
from app.domains.company.services.staff_service import StaffService

router = APIRouter(tags=["staff"])

# ── Staff CRUD ───────────────────────────────────────────────────────────


@router.get("", response_model=list[StaffResponse])
async def list_staff(
    company_id: UUID,
    svc: StaffService = Depends(get_staff_service),
) -> list[StaffResponse]:
    staff = await svc.list_staff(company_id)
    return [StaffResponse.model_validate(s) for s in staff]


@router.post("", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    company_id: UUID,
    body: StaffCreate,
    svc: StaffService = Depends(get_staff_service),
) -> StaffResponse:
    staff = await svc.create_staff(company_id, body)
    return StaffResponse.model_validate(staff)


@router.get("/{staff_id}", response_model=StaffResponse)
async def get_staff(
    company_id: UUID,
    staff_id: UUID,
    svc: StaffService = Depends(get_staff_service),
) -> StaffResponse:
    staff = await svc.get_staff(staff_id)
    return StaffResponse.model_validate(staff)


@router.put("/{staff_id}", response_model=StaffResponse)
async def update_staff(
    company_id: UUID,
    staff_id: UUID,
    body: StaffUpdate,
    svc: StaffService = Depends(get_staff_service),
) -> StaffResponse:
    staff = await svc.update_staff(staff_id, body)
    return StaffResponse.model_validate(staff)


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff(
    company_id: UUID,
    staff_id: UUID,
    svc: StaffService = Depends(get_staff_service),
) -> None:
    await svc.delete_staff(staff_id)


# ── Staff Services ───────────────────────────────────────────────────────


@router.get("/{staff_id}/services", response_model=list[StaffServiceResponse])
async def list_staff_services(
    company_id: UUID,
    staff_id: UUID,
    svc: StaffService = Depends(get_staff_service),
) -> list[StaffServiceResponse]:
    rows = await svc.list_staff_services(staff_id)
    return [StaffServiceResponse.model_validate(r) for r in rows]


@router.post(
    "/{staff_id}/services",
    response_model=StaffServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_service(
    company_id: UUID,
    staff_id: UUID,
    body: StaffServiceCreate,
    svc: StaffService = Depends(get_staff_service),
) -> StaffServiceResponse:
    row = await svc.assign_service(staff_id, body)
    return StaffServiceResponse.model_validate(row)


@router.put("/{staff_id}/services/{service_id}", response_model=StaffServiceResponse)
async def update_staff_service(
    company_id: UUID,
    staff_id: UUID,
    service_id: UUID,
    body: StaffServiceUpdate,
    svc: StaffService = Depends(get_staff_service),
) -> StaffServiceResponse:
    row = await svc.update_staff_service(staff_id, service_id, body)
    return StaffServiceResponse.model_validate(row)


@router.delete("/{staff_id}/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_service(
    company_id: UUID,
    staff_id: UUID,
    service_id: UUID,
    svc: StaffService = Depends(get_staff_service),
) -> None:
    await svc.remove_service(staff_id, service_id)


# ── Staff Availability ───────────────────────────────────────────────────


@router.get("/{staff_id}/availability", response_model=list[StaffAvailabilityResponse])
async def get_availability(
    company_id: UUID,
    staff_id: UUID,
    svc: StaffService = Depends(get_staff_service),
) -> list[StaffAvailabilityResponse]:
    rows = await svc.get_availability(staff_id)
    return [StaffAvailabilityResponse.model_validate(r) for r in rows]


@router.post("/{staff_id}/availability", response_model=list[StaffAvailabilityResponse])
async def set_availability(
    company_id: UUID,
    staff_id: UUID,
    body: StaffAvailabilityBulkSet,
    svc: StaffService = Depends(get_staff_service),
) -> list[StaffAvailabilityResponse]:
    rows = await svc.set_availability(staff_id, body)
    return [StaffAvailabilityResponse.model_validate(r) for r in rows]


@router.delete(
    "/{staff_id}/availability/{availability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_availability(
    company_id: UUID,
    staff_id: UUID,
    availability_id: UUID,
    svc: StaffService = Depends(get_staff_service),
) -> None:
    await svc.delete_availability(availability_id)


# ── Availability Overrides ───────────────────────────────────────────────


@router.get(
    "/{staff_id}/availability/overrides",
    response_model=list[AvailabilityOverrideResponse],
)
async def list_overrides(
    company_id: UUID,
    staff_id: UUID,
    svc: StaffService = Depends(get_staff_service),
) -> list[AvailabilityOverrideResponse]:
    rows = await svc.list_overrides(staff_id)
    return [AvailabilityOverrideResponse.model_validate(r) for r in rows]


@router.post(
    "/{staff_id}/availability/overrides",
    response_model=AvailabilityOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_override(
    company_id: UUID,
    staff_id: UUID,
    body: AvailabilityOverrideCreate,
    svc: StaffService = Depends(get_staff_service),
) -> AvailabilityOverrideResponse:
    row = await svc.create_override(staff_id, body)
    return AvailabilityOverrideResponse.model_validate(row)


@router.delete(
    "/{staff_id}/availability/overrides/{override_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_override(
    company_id: UUID,
    staff_id: UUID,
    override_id: UUID,
    svc: StaffService = Depends(get_staff_service),
) -> None:
    await svc.delete_override(override_id)
