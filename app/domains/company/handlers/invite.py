from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.domains.company.dependencies import get_invite_service
from app.domains.company.schemas import (
    InviteAcceptRequest,
    InviteAcceptResponse,
    InviteCreate,
    InviteResponse,
)
from app.domains.company.services.invite_service import InviteService

router = APIRouter(tags=["invites"])

accept_router = APIRouter(prefix="/invites", tags=["invites"])


@router.get("", response_model=list[InviteResponse])
async def list_invites(
    company_id: UUID,
    svc: InviteService = Depends(get_invite_service),
) -> list[InviteResponse]:
    invites = await svc.list_active(company_id)
    return [InviteResponse.model_validate(i) for i in invites]


@router.post("", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    company_id: UUID,
    body: InviteCreate,
    member_id: UUID = Header(..., alias="x-member-id"),
    svc: InviteService = Depends(get_invite_service),
) -> InviteResponse:
    invite = await svc.create(company_id, member_id, body)
    return InviteResponse.model_validate(invite)


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    company_id: UUID,
    invite_id: UUID,
    svc: InviteService = Depends(get_invite_service),
) -> None:
    await svc.revoke(invite_id)


@accept_router.post("/accept", response_model=InviteAcceptResponse)
async def accept_invite(
    body: InviteAcceptRequest,
    svc: InviteService = Depends(get_invite_service),
) -> InviteAcceptResponse:
    invite, member = await svc.accept(body.code, body.member_id)
    return InviteAcceptResponse(
        company_id=invite.company_id,
        company_name=member.company.name if member.company else "",
        member_id=member.id,
    )
