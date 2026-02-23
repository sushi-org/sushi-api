from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domains.company.models import (
    BookedVia,
    BookingStatus,
    BranchStatus,
    CompanyStatus,
    InviteStatus,
    MemberStatus,
    OverrideType,
    ServiceStatus,
    StaffStatus,
)


# ── Shared ───────────────────────────────────────────────────────────────


class OperatingHoursSlot(BaseModel):
    open: str
    close: str


class AvailabilitySlotInput(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time


# ── Company ──────────────────────────────────────────────────────────────


class CompanyCreate(BaseModel):
    name: str
    timezone: str = "UTC"
    member_id: uuid.UUID | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    timezone: str | None = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    domain: str | None
    timezone: str
    status: CompanyStatus
    created_at: datetime
    updated_at: datetime


# ── Branch ───────────────────────────────────────────────────────────────


class BranchCreate(BaseModel):
    name: str
    address: str
    phone: str | None = None
    timezone: str
    operating_hours: dict[str, OperatingHoursSlot | None]


class BranchUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    timezone: str | None = None
    operating_hours: dict[str, OperatingHoursSlot | None] | None = None
    status: BranchStatus | None = None


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    address: str
    phone: str | None
    timezone: str
    operating_hours: dict
    status: BranchStatus
    created_at: datetime
    updated_at: datetime


# ── Service (catalog offering) ───────────────────────────────────────────


class ServiceCreate(BaseModel):
    name: str
    description: str | None = None
    default_price: Decimal
    default_duration_minutes: int
    currency: str = "SGD"


class ServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_price: Decimal | None = None
    default_duration_minutes: int | None = None
    currency: str | None = None
    status: ServiceStatus | None = None


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    description: str | None
    default_price: Decimal
    default_duration_minutes: int
    currency: str
    status: ServiceStatus
    created_at: datetime
    updated_at: datetime


# ── Staff ────────────────────────────────────────────────────────────────


class StaffCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None


class StaffUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    status: StaffStatus | None = None


class StaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    avatar_url: str | None
    status: StaffStatus
    created_at: datetime
    updated_at: datetime


# ── StaffService ─────────────────────────────────────────────────────────


class StaffServiceCreate(BaseModel):
    service_id: uuid.UUID
    price_override: Decimal | None = None
    duration_override: int | None = None


class StaffServiceUpdate(BaseModel):
    price_override: Decimal | None = None
    duration_override: int | None = None


class StaffServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_id: uuid.UUID
    service_id: uuid.UUID
    price_override: Decimal | None
    duration_override: int | None
    created_at: datetime


# ── StaffAvailability ────────────────────────────────────────────────────


class StaffAvailabilityBulkSet(BaseModel):
    branch_id: uuid.UUID
    slots: list[AvailabilitySlotInput]


class StaffAvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_id: uuid.UUID
    branch_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    created_at: datetime


# ── AvailabilityOverride ─────────────────────────────────────────────────


class AvailabilityOverrideCreate(BaseModel):
    branch_id: uuid.UUID
    date: date
    type: OverrideType
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = None


class AvailabilityOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_id: uuid.UUID
    branch_id: uuid.UUID
    date: date
    type: OverrideType
    start_time: time | None
    end_time: time | None
    reason: str | None
    created_at: datetime


# ── Booking ──────────────────────────────────────────────────────────────


class BookingCreate(BaseModel):
    branch_id: uuid.UUID
    staff_id: uuid.UUID
    service_id: uuid.UUID
    customer_phone: str
    customer_name: str | None = None
    date: date
    start_time: time
    booked_via: BookedVia
    conversation_id: uuid.UUID | None = None
    notes: str | None = None


class BookingUpdate(BaseModel):
    status: BookingStatus | None = None
    notes: str | None = None


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    branch_id: uuid.UUID
    staff_id: uuid.UUID
    service_id: uuid.UUID
    customer_phone: str
    customer_name: str | None
    date: date
    start_time: time
    end_time: time
    duration_minutes: int
    price: Decimal
    currency: str
    status: BookingStatus
    booked_via: BookedVia
    conversation_id: uuid.UUID | None
    notes: str | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BookingListResponse(BookingResponse):
    staff_name: str
    service_name: str


# ── Member ───────────────────────────────────────────────────────────────


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    name: str
    email: str
    avatar_url: str | None
    status: MemberStatus
    created_at: datetime
    updated_at: datetime


# ── Invite ───────────────────────────────────────────────────────────────


class InviteCreate(BaseModel):
    expires_in_days: int = 7


class InviteAcceptRequest(BaseModel):
    code: str
    member_id: uuid.UUID


class InviteAcceptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: uuid.UUID
    company_name: str
    member_id: uuid.UUID


class InviteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    created_by: uuid.UUID
    used_by: uuid.UUID | None
    status: InviteStatus
    expires_at: datetime
    created_at: datetime
