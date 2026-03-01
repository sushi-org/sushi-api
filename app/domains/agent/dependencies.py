from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.domains.agent.repositories.agent import AgentRepository
from app.domains.agent.repositories.knowledge_entry import KnowledgeEntryRepository
from app.domains.agent.repositories.reply_template import ReplyTemplateRepository
from app.domains.agent.repositories.tool_execution import ToolExecutionRepository
from app.domains.agent.services.agent_crud_service import AgentCrudService
from app.domains.agent.services.agent_runner import AgentRunner
from app.domains.company.repositories.availability_override import AvailabilityOverrideRepository
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.branch import BranchRepository
from app.domains.company.repositories.company import CompanyRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff import StaffRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository
from app.domains.company.repositories.staff_service import StaffServiceRepository
from app.domains.company.services.booking_service import BookingService
from app.domains.company.services.scheduling_service import SchedulingService
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


def _get_scheduling_service(session: AsyncSession) -> SchedulingService:
    return SchedulingService(
        availability_repo=StaffAvailabilityRepository(session),
        override_repo=AvailabilityOverrideRepository(session),
        booking_repo=BookingRepository(session),
        service_repo=ServiceRepository(session),
    )


def _get_agent_booking_service(session: AsyncSession) -> BookingService:
    return BookingService(
        booking_repo=BookingRepository(session),
        staff_service_repo=StaffServiceRepository(session),
        availability_repo=StaffAvailabilityRepository(session),
        override_repo=AvailabilityOverrideRepository(session),
        service_repo=ServiceRepository(session),
        branch_repo=BranchRepository(session),
        staff_repo=StaffRepository(session),
    )


async def get_agent_runner(
    agent_repo: AgentRepository = Depends(get_agent_repo),
    knowledge_repo: KnowledgeEntryRepository = Depends(get_knowledge_entry_repo),
    template_repo: ReplyTemplateRepository = Depends(get_reply_template_repo),
    tool_execution_repo: ToolExecutionRepository = Depends(get_tool_execution_repo),
    message_repo: MessageRepository = Depends(_get_message_repo),
    session: AsyncSession = Depends(get_session),
) -> AgentRunner:
    from app.domains.agent.prompt.builder import SystemPromptBuilder
    from app.domains.agent.prompt.sections.business_context_section import BusinessContextSection
    from app.domains.agent.prompt.sections.customer_profile_section import CustomerProfileSection
    from app.domains.agent.prompt.sections.datetime_section import DateTimeSection
    from app.domains.agent.prompt.sections.knowledge_base_section import KnowledgeBaseSection
    from app.domains.agent.prompt.sections.reply_templates_section import ReplyTemplatesSection
    from app.domains.agent.prompt.sections.tool_rules_section import ToolRulesSection
    from app.domains.agent.services.agent_context_loader import AgentContextLoader
    from app.domains.agent.services.tool_executor import ToolExecutor
    from app.domains.agent.tools.book_appointment import BookAppointmentTool
    from app.domains.agent.tools.cancel_booking import CancelBookingTool
    from app.domains.agent.tools.check_availability import CheckAvailabilityTool
    from app.domains.agent.tools.edit_booking import EditBookingTool
    from app.domains.agent.tools.escalate import EscalateTool
    from app.domains.agent.tools.list_bookings import ListBookingsTool
    from app.domains.agent.tools.registry import ToolRegistry

    scheduling_svc = _get_scheduling_service(session)
    booking_svc = _get_agent_booking_service(session)

    # Tool registry — adding a new tool = one register() line here
    registry = ToolRegistry()
    registry.register("check_availability", lambda: CheckAvailabilityTool(scheduling_svc))
    registry.register("book_appointment", lambda: BookAppointmentTool(booking_svc, scheduling_svc))
    registry.register("edit_booking", lambda: EditBookingTool(booking_svc, scheduling_svc))
    registry.register("cancel_booking", lambda: CancelBookingTool(booking_svc))
    registry.register("list_bookings", lambda: ListBookingsTool(booking_svc))
    registry.register("escalate", lambda: EscalateTool())

    context_loader = AgentContextLoader(
        agent_repo=agent_repo,
        knowledge_repo=knowledge_repo,
        template_repo=template_repo,
        message_repo=message_repo,
        company_repo=CompanyRepository(session),
        branch_repo=BranchRepository(session),
        service_repo=ServiceRepository(session),
        staff_repo=StaffRepository(session),
        booking_repo=BookingRepository(session),
    )

    prompt_builder = SystemPromptBuilder(sections=[
        DateTimeSection(),
        ToolRulesSection(),
        CustomerProfileSection(),
        KnowledgeBaseSection(),
        ReplyTemplatesSection(),
        BusinessContextSection(),
    ])

    tool_executor = ToolExecutor(tool_execution_repo)

    return AgentRunner(
        context_loader=context_loader,
        prompt_builder=prompt_builder,
        tool_registry=registry,
        tool_executor=tool_executor,
        template_repo=template_repo,
    )
