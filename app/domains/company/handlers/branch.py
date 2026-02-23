from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.domains.company.dependencies import get_branch_service
from app.domains.company.schemas import BranchCreate, BranchResponse, BranchUpdate
from app.domains.company.services.branch_service import BranchService

router = APIRouter(tags=["branches"])


@router.get("", response_model=list[BranchResponse])
async def list_branches(
    company_id: UUID,
    svc: BranchService = Depends(get_branch_service),
) -> list[BranchResponse]:
    branches = await svc.list(company_id)
    return [BranchResponse.model_validate(b) for b in branches]


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    company_id: UUID,
    body: BranchCreate,
    svc: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    branch = await svc.create(company_id, body)
    return BranchResponse.model_validate(branch)


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(
    company_id: UUID,
    branch_id: UUID,
    svc: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    branch = await svc.get(branch_id)
    return BranchResponse.model_validate(branch)


@router.put("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    company_id: UUID,
    branch_id: UUID,
    body: BranchUpdate,
    svc: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    branch = await svc.update(branch_id, body)
    return BranchResponse.model_validate(branch)


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(
    company_id: UUID,
    branch_id: UUID,
    svc: BranchService = Depends(get_branch_service),
) -> None:
    await svc.delete(branch_id)
