from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.domains.agent.repositories.agent import AgentRepository
from app.domains.agent.repositories.knowledge_entry import KnowledgeEntryRepository
from app.domains.agent.repositories.reply_template import ReplyTemplateRepository
from app.domains.agent.repositories.tool_execution import ToolExecutionRepository
from app.domains.agent.services.agent_chat_service import AgentChatService
from app.domains.agent.services.agent_crud_service import AgentCrudService
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.branch import BranchRepository
from app.domains.company.repositories.company import CompanyRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff import StaffRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository
from app.domains.company.repositories.staff_service import StaffServiceRepository
from app.domains.messaging.repositories.message import MessageRepository


# ── Repositories ─────────────────────────────────────────────────────────


async def get_agent_repo(session: AsyncSession = Depends(get_session)) -> AgentRepository:
    return AgentRepository(session)


async def get_knowledge_entry_repo(session: AsyncSession = Depends(get_session)) -> KnowledgeEntryRepository:
    return KnowledgeEntryRepository(session)


async def get_reply_template_repo(session: AsyncSession = Depends(get_session)) -> ReplyTemplateRepository:
    return ReplyTemplateRepository(session)


async def get_tool_execution_repo(session: AsyncSession = Depends(get_session)) -> ToolExecutionRepository:
    return ToolExecutionRepository(session)


# ── Services ─────────────────────────────────────────────────────────────


async def get_agent_crud_service(
    agent_repo: AgentRepository = Depends(get_agent_repo),
    knowledge_repo: KnowledgeEntryRepository = Depends(get_knowledge_entry_repo),
    template_repo: ReplyTemplateRepository = Depends(get_reply_template_repo),
) -> AgentCrudService:
    return AgentCrudService(
        agent_repo=agent_repo,
        knowledge_repo=knowledge_repo,
        template_repo=template_repo,
    )


async def _get_message_repo(session: AsyncSession = Depends(get_session)) -> MessageRepository:
    return MessageRepository(session)


async def get_agent_chat_service(
    agent_repo: AgentRepository = Depends(get_agent_repo),
    knowledge_repo: KnowledgeEntryRepository = Depends(get_knowledge_entry_repo),
    template_repo: ReplyTemplateRepository = Depends(get_reply_template_repo),
    tool_execution_repo: ToolExecutionRepository = Depends(get_tool_execution_repo),
    message_repo: MessageRepository = Depends(_get_message_repo),
    session: AsyncSession = Depends(get_session),
) -> AgentChatService:
    company_repo = CompanyRepository(session)
    branch_repo = BranchRepository(session)
    service_repo = ServiceRepository(session)
    staff_repo = StaffRepository(session)
    staff_service_repo = StaffServiceRepository(session)
    staff_availability_repo = StaffAvailabilityRepository(session)
    booking_repo = BookingRepository(session)

    return AgentChatService(
        agent_repo=agent_repo,
        knowledge_repo=knowledge_repo,
        template_repo=template_repo,
        tool_execution_repo=tool_execution_repo,
        message_repo=message_repo,
        company_repo=company_repo,
        branch_repo=branch_repo,
        service_repo=service_repo,
        staff_repo=staff_repo,
        staff_service_repo=staff_service_repo,
        staff_availability_repo=staff_availability_repo,
        booking_repo=booking_repo,
    )
