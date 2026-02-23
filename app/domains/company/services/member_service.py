from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.domains.company.models import Member
from app.domains.company.repositories.member import MemberRepository


class MemberService:
    def __init__(self, repo: MemberRepository) -> None:
        self.repo = repo

    async def list(self, company_id: UUID) -> list[Member]:
        return await self.repo.list_by_company(company_id)

    async def get(self, member_id: UUID) -> Member:
        member = await self.repo.get_by_id(member_id)
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        return member

    async def remove(self, member_id: UUID) -> None:
        deleted = await self.repo.delete(member_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
