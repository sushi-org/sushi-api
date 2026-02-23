from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.db.base import get_session
from app.domains.auth.schemas import AuthSyncRequest, AuthSyncResponse
from app.domains.auth.service import AuthSyncService
from app.domains.company.repositories.company import CompanyRepository
from app.domains.company.repositories.member import MemberRepository

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def _get_auth_sync_service(
    session: AsyncSession = Depends(get_session),
) -> AuthSyncService:
    return AuthSyncService(
        member_repo=MemberRepository(session),
        company_repo=CompanyRepository(session),
    )


def _verify_sync_secret(authorization: str = Header(...)) -> None:
    expected = f"Bearer {Config.AUTH_SYNC_SECRET}"
    if not Config.AUTH_SYNC_SECRET or authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sync secret",
        )


@router.post("/sync", response_model=AuthSyncResponse, dependencies=[Depends(_verify_sync_secret)])
async def auth_sync(
    body: AuthSyncRequest,
    svc: AuthSyncService = Depends(_get_auth_sync_service),
) -> AuthSyncResponse:
    return await svc.sync(body)
