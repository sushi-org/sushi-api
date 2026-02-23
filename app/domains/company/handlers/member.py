from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.domains.company.dependencies import get_member_service
from app.domains.company.schemas import MemberResponse
from app.domains.company.services.member_service import MemberService

router = APIRouter(tags=["members"])


@router.get("", response_model=list[MemberResponse])
async def list_members(
    company_id: UUID,
    svc: MemberService = Depends(get_member_service),
) -> list[MemberResponse]:
    members = await svc.list(company_id)
    return [MemberResponse.model_validate(m) for m in members]


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    company_id: UUID,
    member_id: UUID,
    svc: MemberService = Depends(get_member_service),
) -> None:
    await svc.remove(member_id)
