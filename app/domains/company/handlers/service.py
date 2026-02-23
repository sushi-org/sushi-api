from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.domains.company.dependencies import get_catalog_service
from app.domains.company.schemas import ServiceCreate, ServiceResponse, ServiceUpdate
from app.domains.company.services.catalog_service import CatalogService

router = APIRouter(tags=["services"])


@router.get("", response_model=list[ServiceResponse])
async def list_services(
    company_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
) -> list[ServiceResponse]:
    services = await svc.list(company_id)
    return [ServiceResponse.model_validate(s) for s in services]


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    company_id: UUID,
    body: ServiceCreate,
    svc: CatalogService = Depends(get_catalog_service),
) -> ServiceResponse:
    service = await svc.create(company_id, body)
    return ServiceResponse.model_validate(service)


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    company_id: UUID,
    service_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
) -> ServiceResponse:
    service = await svc.get(service_id)
    return ServiceResponse.model_validate(service)


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    company_id: UUID,
    service_id: UUID,
    body: ServiceUpdate,
    svc: CatalogService = Depends(get_catalog_service),
) -> ServiceResponse:
    service = await svc.update(service_id, body)
    return ServiceResponse.model_validate(service)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    company_id: UUID,
    service_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
) -> None:
    await svc.delete(service_id)
