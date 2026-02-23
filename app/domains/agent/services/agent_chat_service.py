from __future__ import annotations

import datetime as _dt
import json
import logging
import time
from uuid import UUID

from app.config import Config
from app.domains.agent.defaults import DEFAULT_REPLY_TEMPLATES, DEFAULT_TOOLS_ENABLED
from app.domains.agent.llm.client import chat_completion, get_response_text, parse_tool_calls
from app.domains.agent.models import AgentStatus, KnowledgeEntryStatus, ReplyTemplateTrigger
from app.domains.agent.repositories.agent import AgentRepository
from app.domains.agent.repositories.knowledge_entry import KnowledgeEntryRepository
from app.domains.agent.repositories.reply_template import ReplyTemplateRepository
from app.domains.agent.repositories.tool_execution import ToolExecutionRepository
from app.domains.agent.tools.base import BaseTool, ToolContext
from app.domains.agent.tools.book_appointment import BookAppointmentTool
from app.domains.agent.tools.cancel_booking import CancelBookingTool
from app.domains.agent.tools.check_availability import CheckAvailabilityTool
from app.domains.agent.tools.edit_booking import EditBookingTool
from app.domains.agent.tools.escalate import EscalateTool
from app.domains.agent.tools.list_bookings import ListBookingsTool
from app.domains.company.repositories.booking import BookingRepository
from app.domains.company.repositories.branch import BranchRepository
from app.domains.company.repositories.company import CompanyRepository
from app.domains.company.repositories.service import ServiceRepository
from app.domains.company.repositories.staff import StaffRepository
from app.domains.company.repositories.staff_availability import StaffAvailabilityRepository
from app.domains.company.repositories.staff_service import StaffServiceRepository
from app.domains.messaging.repositories.message import MessageRepository
from app.domains.pipeline.service import AgentResponse

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


class AgentChatService:
    def __init__(
        self,
        agent_repo: AgentRepository,
        knowledge_repo: KnowledgeEntryRepository,
        template_repo: ReplyTemplateRepository,
        tool_execution_repo: ToolExecutionRepository,
        message_repo: MessageRepository,
        company_repo: CompanyRepository,
        branch_repo: BranchRepository,
        service_repo: ServiceRepository,
        staff_repo: StaffRepository,
        staff_service_repo: StaffServiceRepository,
        staff_availability_repo: StaffAvailabilityRepository,
        booking_repo: BookingRepository,
    ) -> None:
        self.agent_repo = agent_repo
        self.knowledge_repo = knowledge_repo
        self.template_repo = template_repo
        self.tool_execution_repo = tool_execution_repo
        self.message_repo = message_repo
        self.company_repo = company_repo
        self.branch_repo = branch_repo
        self.service_repo = service_repo
        self.staff_repo = staff_repo
        self.staff_service_repo = staff_service_repo
        self.staff_availability_repo = staff_availability_repo
        self.booking_repo = booking_repo

    async def process(
        self,
        conversation_id: UUID,
        branch_id: UUID,
        customer_phone: str = "",
        customer_name: str | None = None,
    ) -> AgentResponse:
        agent = await self.agent_repo.get_by_branch_id(branch_id)
        if agent is None or agent.status == AgentStatus.paused:
            return AgentResponse(
                text=await self.resolve_template(None, "escalation"),
                escalate=True,
                escalation_reason="No active agent for this branch",
            )

        recent_messages = await self.message_repo.get_recent(conversation_id, limit=20)
        knowledge_entries = await self.knowledge_repo.list_active_by_agent(agent.id)
        templates = await self._load_all_templates(agent.id)

        company = await self.company_repo.get_by_id(agent.company_id)
        branch = await self.branch_repo.get_by_id(branch_id)
        services = await self.service_repo.list_by(company_id=agent.company_id)
        active_services = [s for s in services if s.status.value == "active"]
        staff_list = await self.staff_repo.list_by(company_id=agent.company_id)
        active_staff = [s for s in staff_list if s.status.value == "active"]

        system_prompt = self._build_system_prompt(
            agent, knowledge_entries, templates, company, branch, active_services, active_staff
        )

        messages = [{"role": "system", "content": system_prompt}]
        for msg in recent_messages:
            role = "assistant" if msg.role.value in ("agent", "member") else "user"
            messages.append({"role": role, "content": msg.content})

        tools_map = self._build_tools(agent)
        tool_schemas = [t.to_openai_schema() for t in tools_map.values()] if tools_map else None

        tool_context = ToolContext(
            branch_id=branch_id,
            company_id=agent.company_id,
            conversation_id=conversation_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
        )

        escalate = False
        escalation_reason = None

        for _ in range(MAX_TOOL_ROUNDS):
            model = agent.model or Config.OPENROUTER_DEFAULT_MODEL
            response = await chat_completion(model, messages, tool_schemas)

            tool_calls = parse_tool_calls(response)
            if not tool_calls:
                break

            assistant_msg = response.choices[0].message
            messages.append({
                "role": "assistant",
                "content": assistant_msg.content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                    }
                    for tc in tool_calls
                ],
            })

            for tc in tool_calls:
                tool = tools_map.get(tc["name"])
                if tool is None:
                    tool_result = {"error": f"Unknown tool: {tc['name']}"}
                else:
                    start_ms = time.monotonic()
                    try:
                        tool_result = await tool.execute(tc["arguments"], tool_context)
                        exec_status = "success"
                    except Exception as exc:
                        logger.exception("Tool %s failed", tc["name"])
                        tool_result = {"error": str(exc)}
                        exec_status = "failure"
                    duration_ms = int((time.monotonic() - start_ms) * 1000)

                    await self.tool_execution_repo.create(
                        conversation_id=conversation_id,
                        tool=tc["name"],
                        input=tc["arguments"],
                        output=tool_result,
                        status=exec_status,
                        duration_ms=duration_ms,
                    )

                if tc["name"] == "escalate" and tool_result.get("escalate"):
                    escalate = True
                    escalation_reason = tool_result.get("reason")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(tool_result),
                })

        text = get_response_text(response)
        if not text:
            text = await self.resolve_template(agent.id, "escalation")
            escalate = True
            escalation_reason = "Agent returned empty response"

        return AgentResponse(text=text, escalate=escalate, escalation_reason=escalation_reason)

    async def resolve_template(self, agent_id: UUID | None, trigger: str) -> str:
        if agent_id is not None:
            custom = await self.template_repo.get_active_by_trigger(agent_id, trigger)
            if custom:
                return custom.content

        default = DEFAULT_REPLY_TEMPLATES.get(trigger)
        if default:
            return default["content"]

        return "Let me connect you with our team. Someone will be with you shortly."

    # ── Internals ─────────────────────────────────────────────────────────

    def _build_tools(self, agent) -> dict[str, BaseTool]:
        enabled = {**DEFAULT_TOOLS_ENABLED, **(agent.tools_enabled or {})}
        tools: dict[str, BaseTool] = {}

        if enabled.get("check_availability"):
            tools["check_availability"] = CheckAvailabilityTool(
                self.service_repo, self.staff_repo, self.staff_service_repo,
                self.staff_availability_repo, self.booking_repo,
            )
        if enabled.get("book_appointment"):
            tools["book_appointment"] = BookAppointmentTool(
                self.service_repo, self.staff_service_repo, self.booking_repo,
                self.staff_repo, self.staff_availability_repo,
            )
        if enabled.get("list_bookings"):
            tools["list_bookings"] = ListBookingsTool(
                self.booking_repo, self.service_repo, self.staff_repo,
            )
        if enabled.get("cancel_booking"):
            tools["cancel_booking"] = CancelBookingTool(self.booking_repo)
        if enabled.get("edit_booking"):
            tools["edit_booking"] = EditBookingTool(
                self.booking_repo, self.service_repo, self.staff_repo,
                self.staff_service_repo, self.staff_availability_repo,
            )
        if enabled.get("escalate"):
            tools["escalate"] = EscalateTool()

        return tools

    def _build_system_prompt(self, agent, knowledge_entries, templates, company, branch, services, staff) -> str:
        now = _dt.datetime.now()
        parts: list[str] = [agent.system_prompt]

        parts.append(f"\n--- Current Date & Time ---")
        parts.append(f"Today is {now.strftime('%A, %B %d, %Y')}. Current time is {now.strftime('%H:%M')}.")

        parts.append(
            "\n--- Tool Usage Rules ---\n"
            "You have tools available for managing appointments. Follow these rules strictly:\n"
            "- ALWAYS call check_availability before suggesting available times.\n"
            "- ALWAYS call book_appointment to book. NEVER confirm a booking unless the tool returned success.\n"
            "- To cancel or edit a booking, FIRST call list_bookings to find the booking, then call cancel_booking or edit_booking with the booking_id.\n"
            "- NEVER claim an action was performed unless the corresponding tool returned a successful result.\n"
            "- When calling tools, always use dates relative to today's date shown above."
        )

        if knowledge_entries:
            parts.append("\n--- Knowledge Base ---")
            for entry in knowledge_entries:
                parts.append(f"Q: {entry.question}\nA: {entry.answer}")

        if templates:
            parts.append("\n--- Response Templates ---")
            parts.append("Use these templates to structure your responses for the corresponding scenarios:")
            for trigger, content in templates.items():
                parts.append(f"When {trigger.replace('_', ' ')}: \"{content}\"")

        parts.append(f"\n--- Company & Branch Context ---")
        if company:
            parts.append(f"Company: {company.name}")
        if branch:
            parts.append(f"Branch: {branch.name}")
            if branch.address:
                parts.append(f"Address: {branch.address}")
            if branch.operating_hours:
                parts.append(f"Operating Hours: {json.dumps(branch.operating_hours)}")

        if services:
            parts.append("\nServices offered:")
            for svc in services:
                price_str = f"${svc.default_price}" if svc.default_price else "N/A"
                parts.append(f"  - {svc.name} (ID: {svc.id}, {price_str}, {svc.default_duration_minutes}min)")

        if staff:
            parts.append("\nStaff:")
            for s in staff:
                parts.append(f"  - {s.name} (ID: {s.id})")

        return "\n".join(parts)

    async def _load_all_templates(self, agent_id: UUID) -> dict[str, str]:
        custom = await self.template_repo.list_by_agent(agent_id)
        custom_map = {t.trigger.value: t.content for t in custom if t.status == KnowledgeEntryStatus.active}

        result: dict[str, str] = {}
        for trigger_val in ReplyTemplateTrigger:
            key = trigger_val.value
            if key in custom_map:
                result[key] = custom_map[key]
            elif key in DEFAULT_REPLY_TEMPLATES:
                result[key] = DEFAULT_REPLY_TEMPLATES[key]["content"]
        return result
