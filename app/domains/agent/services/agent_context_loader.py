from __future__ import annotations

import dataclasses
import datetime as _dt
from collections import Counter
from uuid import UUID

from app.domains.agent.defaults import DEFAULT_REPLY_TEMPLATES
from app.domains.agent.models import AgentStatus, KnowledgeEntry, KnowledgeEntryStatus, ReplyTemplateTrigger
from app.domains.agent.repositories.agent import AgentRepository
from app.domains.agent.repositories.knowledge_entry import KnowledgeEntryRepository
from app.domains.agent.repositories.reply_template import ReplyTemplateRepository
from app.domains.company.models import Booking, BookingStatus, Branch, Company, Service, Staff
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.branch import BranchRepository
from app.domains.company.repositories.company import CompanyRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff import StaffRepository
from app.domains.messaging.repositories.message import MessageRepository

_MILESTONE_VISITS = {5, 10, 25, 50, 100}


@dataclasses.dataclass
class CustomerHistory:
    """Derived profile from booking history."""

    is_returning: bool
    visit_count: int
    last_visit_date: _dt.date | None
    weeks_since_last_visit: int | None
    preferred_service_name: str | None
    preferred_service_id: UUID | None
    preferred_staff_name: str | None
    preferred_staff_id: UUID | None
    preferred_day_of_week: str | None
    next_visit_number: int

    @classmethod
    def from_bookings(cls, bookings: list[Booking]) -> CustomerHistory | None:
        """Derive a customer profile from their booking history.

        Returns None if the customer has no bookings at all.
        """
        if not bookings:
            return None

        completed = [b for b in bookings if b.status == BookingStatus.completed]
        visit_count = len(completed)
        is_returning = visit_count > 0

        last_visit_date = completed[0].date if completed else None
        weeks_since = None
        if last_visit_date:
            weeks_since = (_dt.date.today() - last_visit_date).days // 7

        preferred_service_name: str | None = None
        preferred_service_id: UUID | None = None
        preferred_staff_name: str | None = None
        preferred_staff_id: UUID | None = None
        preferred_day_of_week: str | None = None

        if completed:
            top_service_id = Counter(b.service_id for b in completed).most_common(1)[0][0]
            for b in completed:
                if b.service_id == top_service_id:
                    preferred_service_id = b.service_id
                    preferred_service_name = b.service.name if b.service else None
                    break

            top_staff_id = Counter(b.staff_id for b in completed).most_common(1)[0][0]
            for b in completed:
                if b.staff_id == top_staff_id:
                    preferred_staff_id = b.staff_id
                    preferred_staff_name = b.staff.name if b.staff else None
                    break

            preferred_day_of_week = Counter(
                b.date.strftime("%A") for b in completed
            ).most_common(1)[0][0]

        return cls(
            is_returning=is_returning,
            visit_count=visit_count,
            last_visit_date=last_visit_date,
            weeks_since_last_visit=weeks_since,
            preferred_service_name=preferred_service_name,
            preferred_service_id=preferred_service_id,
            preferred_staff_name=preferred_staff_name,
            preferred_staff_id=preferred_staff_id,
            preferred_day_of_week=preferred_day_of_week,
            next_visit_number=visit_count + 1,
        )


@dataclasses.dataclass
class AgentRunContext:
    """All data needed for a single agent invocation."""

    agent: object  # Agent model
    company: Company | None
    branch: Branch | None
    active_services: list[Service]
    active_staff: list[Staff]
    knowledge_entries: list[KnowledgeEntry]
    templates: dict[str, str]  # trigger -> resolved content
    recent_messages: list  # Message ORM objects
    customer_history: CustomerHistory | None
    customer_name: str | None
    customer_phone: str
    is_new_conversation: bool


class AgentContextLoader:
    """Loads all data required for one agent run. Single responsibility: data fetching."""

    def __init__(
        self,
        agent_repo: AgentRepository,
        knowledge_repo: KnowledgeEntryRepository,
        template_repo: ReplyTemplateRepository,
        message_repo: MessageRepository,
        company_repo: CompanyRepository,
        branch_repo: BranchRepository,
        service_repo: ServiceRepository,
        staff_repo: StaffRepository,
        booking_repo: BookingRepository,
    ) -> None:
        self._agent_repo = agent_repo
        self._knowledge_repo = knowledge_repo
        self._template_repo = template_repo
        self._message_repo = message_repo
        self._company_repo = company_repo
        self._branch_repo = branch_repo
        self._service_repo = service_repo
        self._staff_repo = staff_repo
        self._booking_repo = booking_repo

    async def load(
        self,
        branch_id: UUID,
        conversation_id: UUID,
        customer_phone: str,
        customer_name: str | None,
    ) -> AgentRunContext | None:
        """Returns None if no active agent for the branch."""
        agent = await self._agent_repo.get_by_branch_id(branch_id)
        if agent is None or agent.status == AgentStatus.paused:
            return None

        recent_messages = await self._message_repo.get_recent(conversation_id, limit=20)
        knowledge_entries = await self._knowledge_repo.list_active_by_agent(agent.id)
        templates = await self._load_all_templates(agent.id)

        company = await self._company_repo.get_by_id(agent.company_id)
        branch = await self._branch_repo.get_by_id(branch_id)
        services = await self._service_repo.list_by(company_id=agent.company_id)
        active_services = [s for s in services if s.status.value == "active"]
        staff_list = await self._staff_repo.list_by(company_id=agent.company_id)
        active_staff = [s for s in staff_list if s.status.value == "active"]

        past_bookings = await self._booking_repo.list_past_by_phone(agent.company_id, customer_phone)
        customer_history = CustomerHistory.from_bookings(past_bookings)

        resolved_name = customer_name
        if resolved_name is None and past_bookings:
            for b in past_bookings:
                if b.customer_name:
                    resolved_name = b.customer_name
                    break

        is_new_conversation = not any(
            m.role.value in ("agent", "member") for m in recent_messages
        )

        return AgentRunContext(
            agent=agent,
            company=company,
            branch=branch,
            active_services=active_services,
            active_staff=active_staff,
            knowledge_entries=knowledge_entries,
            templates=templates,
            recent_messages=recent_messages,
            customer_history=customer_history,
            customer_name=resolved_name,
            customer_phone=customer_phone,
            is_new_conversation=is_new_conversation,
        )

    async def _load_all_templates(self, agent_id: UUID) -> dict[str, str]:
        custom = await self._template_repo.list_by_agent(agent_id)
        custom_map = {t.trigger.value: t.content for t in custom if t.status == KnowledgeEntryStatus.active}

        result: dict[str, str] = {}
        for trigger_val in ReplyTemplateTrigger:
            key = trigger_val.value
            if key in custom_map:
                result[key] = custom_map[key]
            elif key in DEFAULT_REPLY_TEMPLATES:
                result[key] = DEFAULT_REPLY_TEMPLATES[key]["content"]
        return result
