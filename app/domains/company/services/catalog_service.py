from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.domains.company.models import Service
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.schemas import ServiceCreate, ServiceUpdate


class CatalogService:
    """Service layer for the Service (bookable offering) entity."""

    def __init__(self, repo: ServiceRepository) -> None:
        self.repo = repo

    async def list(self, company_id: UUID) -> list[Service]:
        return await self.repo.list_by_company(company_id)

    async def get(self, service_id: UUID) -> Service:
        svc = await self.repo.get_by_id(service_id)
        if svc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        return svc

    async def create(self, company_id: UUID, data: ServiceCreate) -> Service:
        return await self.repo.create(company_id=company_id, **data.model_dump())

    async def update(self, service_id: UUID, data: ServiceUpdate) -> Service:
        updated = await self.repo.update(service_id, **data.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        return updated

    async def delete(self, service_id: UUID) -> None:
        deleted = await self.repo.delete(service_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
