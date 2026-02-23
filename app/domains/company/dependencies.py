from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.domains.company.repositories.availability_override import AvailabilityOverrideRepository
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.branch import BranchRepository
from app.domains.company.repositories.company import CompanyRepository
from app.domains.company.repositories.invite import InviteRepository
from app.domains.company.repositories.member import MemberRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff import StaffRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository
from app.domains.company.repositories.staff_service import StaffServiceRepository
from app.domains.company.services.booking_service import BookingService
from app.domains.company.services.branch_service import BranchService
from app.domains.company.services.catalog_service import CatalogService
from app.domains.company.services.company_service import CompanyService
from app.domains.company.services.invite_service import InviteService
from app.domains.company.services.member_service import MemberService
from app.domains.company.services.staff_service import StaffService


# ── Repositories ─────────────────────────────────────────────────────────


async def get_company_repo(session: AsyncSession = Depends(get_session)) -> CompanyRepository:
    return CompanyRepository(session)


async def get_branch_repo(session: AsyncSession = Depends(get_session)) -> BranchRepository:
    return BranchRepository(session)


async def get_service_repo(session: AsyncSession = Depends(get_session)) -> ServiceRepository:
    return ServiceRepository(session)


async def get_staff_repo(session: AsyncSession = Depends(get_session)) -> StaffRepository:
    return StaffRepository(session)


async def get_staff_service_repo(session: AsyncSession = Depends(get_session)) -> StaffServiceRepository:
    return StaffServiceRepository(session)


async def get_availability_repo(session: AsyncSession = Depends(get_session)) -> StaffAvailabilityRepository:
    return StaffAvailabilityRepository(session)


async def get_override_repo(session: AsyncSession = Depends(get_session)) -> AvailabilityOverrideRepository:
    return AvailabilityOverrideRepository(session)


async def get_booking_repo(session: AsyncSession = Depends(get_session)) -> BookingRepository:
    return BookingRepository(session)


async def get_member_repo(session: AsyncSession = Depends(get_session)) -> MemberRepository:
    return MemberRepository(session)


async def get_invite_repo(session: AsyncSession = Depends(get_session)) -> InviteRepository:
    return InviteRepository(session)


# ── Services ─────────────────────────────────────────────────────────────


async def get_company_service(
    repo: CompanyRepository = Depends(get_company_repo),
    member_repo: MemberRepository = Depends(get_member_repo),
) -> CompanyService:
    return CompanyService(repo, member_repo)


async def get_branch_service(
    repo: BranchRepository = Depends(get_branch_repo),
) -> BranchService:
    return BranchService(repo)


async def get_catalog_service(
    repo: ServiceRepository = Depends(get_service_repo),
) -> CatalogService:
    return CatalogService(repo)


async def get_staff_service(
    staff_repo: StaffRepository = Depends(get_staff_repo),
    staff_service_repo: StaffServiceRepository = Depends(get_staff_service_repo),
    availability_repo: StaffAvailabilityRepository = Depends(get_availability_repo),
    override_repo: AvailabilityOverrideRepository = Depends(get_override_repo),
    branch_repo: BranchRepository = Depends(get_branch_repo),
) -> StaffService:
    return StaffService(staff_repo, staff_service_repo, availability_repo, override_repo, branch_repo)


async def get_booking_service(
    booking_repo: BookingRepository = Depends(get_booking_repo),
    staff_service_repo: StaffServiceRepository = Depends(get_staff_service_repo),
    availability_repo: StaffAvailabilityRepository = Depends(get_availability_repo),
    override_repo: AvailabilityOverrideRepository = Depends(get_override_repo),
    service_repo: ServiceRepository = Depends(get_service_repo),
    branch_repo: BranchRepository = Depends(get_branch_repo),
) -> BookingService:
    return BookingService(
        booking_repo, staff_service_repo, availability_repo, override_repo, service_repo, branch_repo
    )


async def get_member_service(
    repo: MemberRepository = Depends(get_member_repo),
) -> MemberService:
    return MemberService(repo)


async def get_invite_service(
    repo: InviteRepository = Depends(get_invite_repo),
    member_repo: MemberRepository = Depends(get_member_repo),
) -> InviteService:
    return InviteService(repo, member_repo)
