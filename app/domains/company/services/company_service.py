from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException, status

from app.domains.company.models import Company
from app.domains.company.repositories.company import CompanyRepository
from app.domains.company.repositories.member import MemberRepository
from app.domains.company.schemas import CompanyCreate, CompanyUpdate


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class CompanyService:
    def __init__(self, repo: CompanyRepository, member_repo: MemberRepository | None = None) -> None:
        self.repo = repo
        self.member_repo = member_repo

    async def create(self, data: CompanyCreate) -> Company:
        slug = _slugify(data.name)
        existing = await self.repo.get_by_slug(slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A company named '{existing.name}' already exists. "
                       f"Ask an existing member to invite you.",
            )

        company = await self.repo.create(
            name=data.name,
            slug=slug,
            timezone=data.timezone,
        )

        if data.member_id and self.member_repo:
            await self.member_repo.update(data.member_id, company_id=company.id)

        return company

    async def get(self, company_id: UUID) -> Company:
        company = await self.repo.get_by_id(company_id)
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        return company

    async def update(self, company_id: UUID, data: CompanyUpdate) -> Company:
        updated = await self.repo.update(company_id, **data.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        return updated
