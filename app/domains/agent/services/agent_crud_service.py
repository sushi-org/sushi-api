from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.config import Config
from app.domains.agent.defaults import DEFAULT_REPLY_TEMPLATES
from app.domains.agent.models import AgentStatus, KnowledgeEntryStatus, ReplyTemplateTrigger
from app.domains.agent.repositories.agent import AgentRepository
from app.domains.agent.repositories.knowledge_entry import KnowledgeEntryRepository
from app.domains.agent.repositories.reply_template import ReplyTemplateRepository
from app.domains.agent.schemas import (
    AgentUpsert,
    KnowledgeEntryCreate,
    KnowledgeEntryUpdate,
    ReplyTemplateResponse,
    ReplyTemplateUpsert,
)


class AgentCrudService:
    def __init__(
        self,
        agent_repo: AgentRepository,
        knowledge_repo: KnowledgeEntryRepository,
        template_repo: ReplyTemplateRepository,
    ) -> None:
        self.agent_repo = agent_repo
        self.knowledge_repo = knowledge_repo
        self.template_repo = template_repo

    # ── Agent ─────────────────────────────────────────────────────────────

    async def get_agent(self, branch_id: UUID):
        return await self.agent_repo.get_by_branch_id(branch_id)

    async def upsert_agent(self, branch_id: UUID, company_id: UUID, data: AgentUpsert):
        existing = await self.agent_repo.get_by_branch_id(branch_id)
        if existing is None:
            defaults = {
                "name": "AI Receptionist",
                "system_prompt": "You are a friendly and professional AI receptionist.",
                "model": Config.OPENROUTER_DEFAULT_MODEL,
                "status": AgentStatus.active,
            }
            overrides = data.model_dump(exclude_unset=True)
            merged = {**defaults, **overrides}
            return await self.agent_repo.create(
                branch_id=branch_id,
                company_id=company_id,
                **merged,
            )
        else:
            kwargs = data.model_dump(exclude_unset=True)
            if kwargs:
                return await self.agent_repo.update(existing.id, **kwargs)
            return existing

    async def delete_agent(self, branch_id: UUID) -> bool:
        agent = await self.agent_repo.get_by_branch_id(branch_id)
        if agent is None:
            return False
        return await self.agent_repo.delete(agent.id)

    # ── Knowledge entries ─────────────────────────────────────────────────

    async def list_knowledge_entries(self, branch_id: UUID):
        agent = await self._require_agent(branch_id)
        return await self.knowledge_repo.list_by_agent(agent.id)

    async def create_knowledge_entry(self, branch_id: UUID, data: KnowledgeEntryCreate):
        agent = await self._require_agent(branch_id)
        max_order = 0
        entries = await self.knowledge_repo.list_by_agent(agent.id)
        if entries:
            max_order = max(e.sort_order for e in entries)
        return await self.knowledge_repo.create(
            agent_id=agent.id,
            question=data.question,
            answer=data.answer,
            category=data.category,
            sort_order=max_order + 1,
        )

    async def update_knowledge_entry(self, entry_id: UUID, data: KnowledgeEntryUpdate):
        kwargs = data.model_dump(exclude_unset=True)
        return await self.knowledge_repo.update(entry_id, **kwargs)

    async def delete_knowledge_entry(self, entry_id: UUID) -> bool:
        return await self.knowledge_repo.delete(entry_id)

    # ── Reply templates ───────────────────────────────────────────────────

    async def list_templates_with_defaults(self, branch_id: UUID) -> list[ReplyTemplateResponse]:
        agent = await self._require_agent(branch_id)
        custom_templates = await self.template_repo.list_by_agent(agent.id)
        custom_by_trigger = {t.trigger.value: t for t in custom_templates if t.status == KnowledgeEntryStatus.active}

        result: list[ReplyTemplateResponse] = []
        for trigger_val in ReplyTemplateTrigger:
            custom = custom_by_trigger.get(trigger_val.value)
            if custom:
                result.append(ReplyTemplateResponse(
                    trigger=trigger_val,
                    name=custom.name,
                    content=custom.content,
                    is_custom=True,
                ))
            else:
                default = DEFAULT_REPLY_TEMPLATES.get(trigger_val.value, {})
                result.append(ReplyTemplateResponse(
                    trigger=trigger_val,
                    name=default.get("name", trigger_val.value),
                    content=default.get("content", ""),
                    is_custom=False,
                ))
        return result

    async def upsert_template(self, branch_id: UUID, trigger: ReplyTemplateTrigger, data: ReplyTemplateUpsert):
        agent = await self._require_agent(branch_id)
        existing = await self.template_repo.get_active_by_trigger(agent.id, trigger.value)
        if existing:
            await self.template_repo.update(existing.id, name=data.name, content=data.content)
            await self.template_repo.session.refresh(existing)
            return ReplyTemplateResponse(
                trigger=trigger, name=existing.name, content=existing.content, is_custom=True
            )
        else:
            template = await self.template_repo.create(
                agent_id=agent.id, trigger=trigger, name=data.name, content=data.content
            )
            return ReplyTemplateResponse(
                trigger=trigger, name=template.name, content=template.content, is_custom=True
            )

    async def delete_template(self, branch_id: UUID, trigger: ReplyTemplateTrigger) -> bool:
        agent = await self._require_agent(branch_id)
        existing = await self.template_repo.get_active_by_trigger(agent.id, trigger.value)
        if existing is None:
            return False
        return await self.template_repo.delete(existing.id)

    # ── Internals ─────────────────────────────────────────────────────────

    async def _require_agent(self, branch_id: UUID):
        agent = await self.agent_repo.get_by_branch_id(branch_id)
        if agent is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No agent configured for this branch")
        return agent
