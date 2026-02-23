from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.agent.dependencies import get_agent_crud_service
from app.domains.agent.schemas import AgentResponse, AgentUpsert
from app.domains.agent.services.agent_crud_service import AgentCrudService

router = APIRouter()


@router.get("", response_model=AgentResponse)
async def get_agent(
    company_id: UUID,
    branch_id: UUID,
    svc: AgentCrudService = Depends(get_agent_crud_service),
):
    agent = await svc.get_agent(branch_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No agent configured for this branch")
    return AgentResponse.model_validate(agent)


@router.put("", response_model=AgentResponse)
async def upsert_agent(
    company_id: UUID,
    branch_id: UUID,
    body: AgentUpsert,
    svc: AgentCrudService = Depends(get_agent_crud_service),
):
    agent = await svc.upsert_agent(branch_id, company_id, body)
    return AgentResponse.model_validate(agent)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    company_id: UUID,
    branch_id: UUID,
    svc: AgentCrudService = Depends(get_agent_crud_service),
):
    deleted = await svc.delete_agent(branch_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No agent configured for this branch")
