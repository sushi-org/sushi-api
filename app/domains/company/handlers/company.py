from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.domains.company.dependencies import get_company_service
from app.domains.company.schemas import CompanyCreate, CompanyResponse, CompanyUpdate
from app.domains.company.services.company_service import CompanyService

router = APIRouter(tags=["companies"])


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate,
    svc: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    company = await svc.create(body)
    return CompanyResponse.model_validate(company)


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    svc: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    company = await svc.get(company_id)
    return CompanyResponse.model_validate(company)


@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    body: CompanyUpdate,
    svc: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    company = await svc.update(company_id, body)
    return CompanyResponse.model_validate(company)
