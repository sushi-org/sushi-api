from fastapi import APIRouter

from app.domains.company.handlers.booking import router as booking_router
from app.domains.company.handlers.branch import router as branch_router
from app.domains.company.handlers.company import router as company_sub_router
from app.domains.company.handlers.invite import accept_router as invite_accept_router
from app.domains.company.handlers.invite import router as invite_router
from app.domains.company.handlers.member import router as member_router
from app.domains.company.handlers.service import router as service_router
from app.domains.company.handlers.staff import router as staff_router

company_router = APIRouter(prefix="/api/v1")

company_router.include_router(company_sub_router)
company_router.include_router(
    branch_router, prefix="/companies/{company_id}/branches", tags=["branches"]
)
company_router.include_router(
    service_router, prefix="/companies/{company_id}/services", tags=["services"]
)
company_router.include_router(
    staff_router, prefix="/companies/{company_id}/staff", tags=["staff"]
)
company_router.include_router(
    booking_router, prefix="/companies/{company_id}/bookings", tags=["bookings"]
)
company_router.include_router(
    member_router, prefix="/companies/{company_id}/members", tags=["members"]
)
company_router.include_router(
    invite_router, prefix="/companies/{company_id}/invites", tags=["invites"]
)
company_router.include_router(invite_accept_router)
