from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.agent.dependencies import get_agent_crud_service
from app.domains.agent.models import ReplyTemplateTrigger
from app.domains.agent.schemas import ReplyTemplateResponse, ReplyTemplateUpsert
from app.domains.agent.services.agent_crud_service import AgentCrudService

router = APIRouter(tags=["templates"])


@router.get("", response_model=list[ReplyTemplateResponse])
async def list_templates(
    company_id: UUID,
    branch_id: UUID,
    svc: AgentCrudService = Depends(get_agent_crud_service),
):
    return await svc.list_templates_with_defaults(branch_id)


@router.put("/{trigger}", response_model=ReplyTemplateResponse)
async def upsert_template(
    company_id: UUID,
    branch_id: UUID,
    trigger: ReplyTemplateTrigger,
    body: ReplyTemplateUpsert,
    svc: AgentCrudService = Depends(get_agent_crud_service),
):
    return await svc.upsert_template(branch_id, trigger, body)


@router.delete("/{trigger}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    company_id: UUID,
    branch_id: UUID,
    trigger: ReplyTemplateTrigger,
    svc: AgentCrudService = Depends(get_agent_crud_service),
):
    deleted = await svc.delete_template(branch_id, trigger)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No custom template for this trigger")
