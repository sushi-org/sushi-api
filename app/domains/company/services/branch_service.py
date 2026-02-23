from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.domains.company.models import Branch
from app.domains.company.repositories.branch import BranchRepository
from app.domains.company.schemas import BranchCreate, BranchUpdate


class BranchService:
    def __init__(self, repo: BranchRepository) -> None:
        self.repo = repo

    async def list(self, company_id: UUID) -> list[Branch]:
        return await self.repo.list_by_company(company_id)

    async def get(self, branch_id: UUID) -> Branch:
        branch = await self.repo.get_by_id(branch_id)
        if branch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        return branch

    async def create(self, company_id: UUID, data: BranchCreate) -> Branch:
        payload = data.model_dump()
        payload["company_id"] = company_id
        if payload.get("operating_hours"):
            payload["operating_hours"] = {
                day: (slot.model_dump() if slot else None)
                for day, slot in data.operating_hours.items()
            }
        return await self.repo.create(**payload)

    async def update(self, branch_id: UUID, data: BranchUpdate) -> Branch:
        payload = data.model_dump(exclude_unset=True)
        if "operating_hours" in payload and payload["operating_hours"] is not None:
            payload["operating_hours"] = {
                day: (slot.model_dump() if hasattr(slot, "model_dump") else slot)
                for day, slot in data.operating_hours.items()  # type: ignore[union-attr]
            }
        updated = await self.repo.update(branch_id, **payload)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        return updated

    async def delete(self, branch_id: UUID) -> None:
        deleted = await self.repo.delete(branch_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
