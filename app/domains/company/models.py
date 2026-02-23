from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


# ── Enums ────────────────────────────────────────────────────────────────


class CompanyStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"


class BranchStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class ServiceStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class StaffStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class OverrideType(str, enum.Enum):
    blocked = "blocked"
    modified = "modified"


class BookingStatus(str, enum.Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


class BookedVia(str, enum.Enum):
    agent = "agent"
    member = "member"


class MemberStatus(str, enum.Enum):
    active = "active"
    deactivated = "deactivated"


class InviteStatus(str, enum.Enum):
    active = "active"
    used = "used"
    revoked = "revoked"


# ── Models ───────────────────────────────────────────────────────────────


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(63), nullable=False, server_default="UTC")
    status: Mapped[CompanyStatus] = mapped_column(
        Enum(CompanyStatus, name="company_status", create_type=False),
        default=CompanyStatus.active, server_default=CompanyStatus.active.value, nullable=False
    )

    branches: Mapped[list[Branch]] = relationship(back_populates="company", cascade="all, delete-orphan")
    services: Mapped[list[Service]] = relationship(back_populates="company", cascade="all, delete-orphan")
    staff_members: Mapped[list[Staff]] = relationship(back_populates="company", cascade="all, delete-orphan")
    bookings: Mapped[list[Booking]] = relationship(back_populates="company", cascade="all, delete-orphan")
    members: Mapped[list[Member]] = relationship(back_populates="company", cascade="all, delete-orphan")
    invites: Mapped[list[Invite]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Branch(TimestampMixin, Base):
    __tablename__ = "branches"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(31), nullable=True)
    timezone: Mapped[str] = mapped_column(String(63), nullable=False)
    operating_hours: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[BranchStatus] = mapped_column(
        Enum(BranchStatus, name="branch_status", create_type=False),
        default=BranchStatus.active, server_default=BranchStatus.active.value, nullable=False
    )

    company: Mapped[Company] = relationship(back_populates="branches")
    staff_availabilities: Mapped[list[StaffAvailability]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    availability_overrides: Mapped[list[AvailabilityOverride]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    bookings: Mapped[list[Booking]] = relationship(back_populates="branch", cascade="all, delete-orphan")


class Service(TimestampMixin, Base):
    __tablename__ = "services"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    default_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="SGD")
    status: Mapped[ServiceStatus] = mapped_column(
        Enum(ServiceStatus, name="service_status", create_type=False),
        default=ServiceStatus.active, server_default=ServiceStatus.active.value, nullable=False
    )

    company: Mapped[Company] = relationship(back_populates="services")
    staff_services: Mapped[list[StaffService]] = relationship(back_populates="service", cascade="all, delete-orphan")
    bookings: Mapped[list[Booking]] = relationship(back_populates="service")


class Staff(TimestampMixin, Base):
    __tablename__ = "staff"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(31), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[StaffStatus] = mapped_column(
        Enum(StaffStatus, name="staff_status", create_type=False),
        default=StaffStatus.active, server_default=StaffStatus.active.value, nullable=False
    )

    company: Mapped[Company] = relationship(back_populates="staff_members")
    staff_services: Mapped[list[StaffService]] = relationship(
        back_populates="staff", cascade="all, delete-orphan"
    )
    availabilities: Mapped[list[StaffAvailability]] = relationship(
        back_populates="staff", cascade="all, delete-orphan"
    )
    availability_overrides: Mapped[list[AvailabilityOverride]] = relationship(
        back_populates="staff", cascade="all, delete-orphan"
    )
    bookings: Mapped[list[Booking]] = relationship(back_populates="staff")


class StaffService(TimestampMixin, Base):
    __tablename__ = "staff_services"
    __table_args__ = (
        UniqueConstraint("staff_id", "service_id", name="uq_staff_service"),
    )

    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price_override: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    duration_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

    staff: Mapped[Staff] = relationship(back_populates="staff_services")
    service: Mapped[Service] = relationship(back_populates="staff_services")


class StaffAvailability(TimestampMixin, Base):
    __tablename__ = "staff_availabilities"
    __table_args__ = (
        CheckConstraint("start_time < end_time", name="ck_availability_time_order"),
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="ck_availability_day_range"),
    )

    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    staff: Mapped[Staff] = relationship(back_populates="availabilities")
    branch: Mapped[Branch] = relationship(back_populates="staff_availabilities")


class AvailabilityOverride(TimestampMixin, Base):
    __tablename__ = "availability_overrides"

    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[OverrideType] = mapped_column(
        Enum(OverrideType, name="override_type", create_type=False), nullable=False
    )
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    staff: Mapped[Staff] = relationship(back_populates="availability_overrides")
    branch: Mapped[Branch] = relationship(back_populates="availability_overrides")


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("start_time < end_time", name="ck_booking_time_order"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_phone: Mapped[str] = mapped_column(String(31), nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status", create_type=False),
        default=BookingStatus.confirmed, server_default=BookingStatus.confirmed.value, nullable=False
    )
    booked_via: Mapped[BookedVia] = mapped_column(
        Enum(BookedVia, name="booked_via", create_type=False), nullable=False
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    company: Mapped[Company] = relationship(back_populates="bookings")
    branch: Mapped[Branch] = relationship(back_populates="bookings")
    staff: Mapped[Staff] = relationship(back_populates="bookings")
    service: Mapped[Service] = relationship(back_populates="bookings")


class Member(TimestampMixin, Base):
    __tablename__ = "members"

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[MemberStatus] = mapped_column(
        Enum(MemberStatus, name="member_status", create_type=False),
        default=MemberStatus.active, server_default=MemberStatus.active.value, nullable=False
    )

    company: Mapped[Company | None] = relationship(back_populates="members")
    created_invites: Mapped[list[Invite]] = relationship(
        back_populates="creator", foreign_keys="[Invite.created_by]"
    )


class Invite(TimestampMixin, Base):
    __tablename__ = "invites"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False
    )
    used_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus, name="invite_status", create_type=False),
        default=InviteStatus.active, server_default=InviteStatus.active.value, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    company: Mapped[Company] = relationship(back_populates="invites")
    creator: Mapped[Member] = relationship(back_populates="created_invites", foreign_keys=[created_by])
    redeemer: Mapped[Member | None] = relationship(foreign_keys=[used_by])
