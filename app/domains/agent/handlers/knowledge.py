from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.agent.dependencies import get_agent_crud_service
from app.domains.agent.schemas import KnowledgeEntryCreate, KnowledgeEntryResponse, KnowledgeEntryUpdate
from app.domains.agent.services.agent_crud_service import AgentCrudService

router = APIRouter(tags=["knowledge"])


@router.get("", response_model=list[KnowledgeEntryResponse])
async def list_knowledge_entries(
    company_id: UUID,
    branch_id: UUID,
    svc: AgentCrudService = Depends(get_agent_crud_service),
):
    entries = await svc.list_knowledge_entries(branch_id)
    return [KnowledgeEntryResponse.model_validate(e) for e in entries]


@router.post("", response_model=KnowledgeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_entry(
    company_id: UUID,
    branch_id: UUID,
    body: KnowledgeEntryCreate,
    svc: AgentCrudService = Depends(get_agent_crud_service),
):
    entry = await svc.create_knowledge_entry(branch_id, body)
    return KnowledgeEntryResponse.model_validate(entry)


@router.put("/{entry_id}", response_model=KnowledgeEntryResponse)
async def update_knowledge_entry(
    company_id: UUID,
    branch_id: UUID,
    entry_id: UUID,
    body: KnowledgeEntryUpdate,
    svc: AgentCrudService = Depends(get_agent_crud_service),
):
    entry = await svc.update_knowledge_entry(entry_id, body)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge entry not found")
    return KnowledgeEntryResponse.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_entry(
    company_id: UUID,
    branch_id: UUID,
    entry_id: UUID,
    svc: AgentCrudService = Depends(get_agent_crud_service),
):
    deleted = await svc.delete_knowledge_entry(entry_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge entry not found")
