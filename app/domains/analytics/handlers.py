from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.domains.analytics.schemas import HomeAnalyticsResponse
from app.domains.analytics.service import AnalyticsService

router = APIRouter(
    prefix="/api/v1/companies/{company_id}/analytics",
    tags=["analytics"],
)


@router.get("/home", response_model=HomeAnalyticsResponse)
async def get_home_analytics(
    company_id: UUID,
    branch_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> HomeAnalyticsResponse:
    svc = AnalyticsService(session)
    data = await svc.get_home_analytics(company_id, branch_id)
    return HomeAnalyticsResponse(**data)
