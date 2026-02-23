from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.domains.company.dependencies import get_booking_service
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff import StaffRepository
from app.domains.company.schemas import (
    BookingCreate,
    BookingListResponse,
    BookingResponse,
    BookingUpdate,
)
from app.domains.company.services.booking_service import BookingService

router = APIRouter(tags=["bookings"])


@router.get("", response_model=list[BookingListResponse])
async def list_bookings(
    company_id: UUID,
    branch_id: UUID | None = None,
    svc: BookingService = Depends(get_booking_service),
    session: AsyncSession = Depends(get_session),
) -> list[BookingListResponse]:
    bookings = await svc.list_by_company(company_id, branch_id=branch_id)

    staff_repo = StaffRepository(session)
    service_repo = ServiceRepository(session)

    staff_cache: dict[UUID, str] = {}
    service_cache: dict[UUID, str] = {}

    results = []
    for b in bookings:
        if b.staff_id not in staff_cache:
            staff = await staff_repo.get_by_id(b.staff_id)
            staff_cache[b.staff_id] = staff.name if staff else "Unknown"
        if b.service_id not in service_cache:
            svc_obj = await service_repo.get_by_id(b.service_id)
            service_cache[b.service_id] = svc_obj.name if svc_obj else "Unknown"

        data = BookingResponse.model_validate(b).model_dump()
        data["staff_name"] = staff_cache[b.staff_id]
        data["service_name"] = service_cache[b.service_id]
        results.append(BookingListResponse(**data))

    results.sort(key=lambda r: (r.date, r.start_time), reverse=True)
    return results


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    company_id: UUID,
    body: BookingCreate,
    svc: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    booking = await svc.create(company_id, body)
    return BookingResponse.model_validate(booking)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    company_id: UUID,
    booking_id: UUID,
    svc: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    booking = await svc.get(booking_id)
    return BookingResponse.model_validate(booking)


@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    company_id: UUID,
    booking_id: UUID,
    body: BookingUpdate,
    svc: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    booking = await svc.update(booking_id, body)
    return BookingResponse.model_validate(booking)
