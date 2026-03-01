from __future__ import annotations

import json
import logging
from uuid import UUID

from app.config import Config
from app.domains.agent.defaults import DEFAULT_REPLY_TEMPLATES, DEFAULT_TOOLS_ENABLED
from app.domains.agent.llm.client import chat_completion, get_response_text, parse_tool_calls
from app.domains.agent.prompt.builder import SystemPromptBuilder
from app.domains.agent.repositories.reply_template import ReplyTemplateRepository
from app.domains.agent.services.agent_context_loader import AgentContextLoader
from app.domains.agent.services.tool_executor import ToolExecutor
from app.domains.agent.tools.base import ToolContext
from app.domains.agent.tools.registry import ToolRegistry
from app.domains.pipeline.contracts import AgentResponse

logger = logging.getLogger(__name__)
MAX_TOOL_ROUNDS = 5


class AgentRunner:
    """Slim orchestrator for a single agent turn.

    Replaces AgentChatService. Constructor takes 5 collaborators instead of 12 repos.
    Satisfies AgentServiceProtocol from pipeline.
    """

    def __init__(
        self,
        context_loader: AgentContextLoader,
        prompt_builder: SystemPromptBuilder,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        template_repo: ReplyTemplateRepository,
    ) -> None:
        self.context_loader = context_loader
        self.prompt_builder = prompt_builder
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.template_repo = template_repo

    async def process(
        self,
        conversation_id: UUID,
        branch_id: UUID,
        customer_phone: str = "",
        customer_name: str | None = None,
        msg_id: str = "",
    ) -> AgentResponse:
        ctx = await self.context_loader.load(branch_id, conversation_id, customer_phone, customer_name)

        if ctx is None:
            logger.warning("Step 4 - msg=%s: No active agent, escalating", msg_id)
            return AgentResponse(
                text=await self.resolve_template(None, "escalation"),
                escalate=True,
                escalation_reason="No active agent for this branch",
            )

        logger.info(
            "Step 4 - msg=%s: Customer history — phone=%s name=%s is_returning=%s",
            msg_id, customer_phone, ctx.customer_name,
            ctx.customer_history.is_returning if ctx.customer_history else None,
        )

        system_prompt = self.prompt_builder.build(ctx)

        messages = [{"role": "system", "content": system_prompt}]
        for msg in ctx.recent_messages:
            role = "assistant" if msg.role.value in ("agent", "member") else "user"
            messages.append({"role": role, "content": msg.content})

        enabled = {**DEFAULT_TOOLS_ENABLED, **(ctx.agent.tools_enabled or {})}
        tools_map = self.tool_registry.build_enabled(enabled)
        tool_schemas = [t.to_openai_schema() for t in tools_map.values()] if tools_map else None

        tool_context = ToolContext(
            branch_id=branch_id,
            company_id=ctx.agent.company_id,
            conversation_id=conversation_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
        )

        escalate = False
        escalation_reason = None
        response = None

        for round_num in range(MAX_TOOL_ROUNDS):
            model = ctx.agent.model or Config.OPENROUTER_DEFAULT_MODEL
            logger.info("Step 4 - msg=%s: LLM round %d", msg_id, round_num + 1)
            response = await chat_completion(model, messages, tool_schemas, msg_id=msg_id)

            tool_calls = parse_tool_calls(response)
            if not tool_calls:
                logger.info("Step 6 - msg=%s: LLM done (no tools)", msg_id)
                break

            logger.info("Step 5 - msg=%s: Tools: %s", msg_id, ", ".join(tc["name"] for tc in tool_calls))

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
                    logger.warning("Step 5 - msg=%s: Unknown tool: %s", msg_id, tc["name"])
                    tool_result = {"error": f"Unknown tool: {tc['name']}"}
                else:
                    tool_result = await self.tool_executor.run(
                        tool=tool,
                        tool_name=tc["name"],
                        tool_call_id=tc["id"],
                        arguments=tc["arguments"],
                        context=tool_context,
                        conversation_id=conversation_id,
                        msg_id=msg_id,
                    )

                if tc["name"] == "escalate" and tool_result.get("escalate"):
                    escalate = True
                    escalation_reason = tool_result.get("reason")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(tool_result),
                })

        text = get_response_text(response) if response else None
        if not text:
            logger.warning("Step 6 - msg=%s: Empty response, escalating", msg_id)
            text = await self.resolve_template(
                ctx.agent.id if ctx else None, "escalation"
            )
            escalate = True
            escalation_reason = "Agent returned empty response"

        logger.info("Step 7 - msg=%s: Agent done (escalate=%s)", msg_id, escalate)
        return AgentResponse(text=text, escalate=escalate, escalation_reason=escalation_reason)

    async def resolve_template(self, agent_id: UUID | None, trigger: str) -> str:
        """Required by AgentServiceProtocol."""
        if agent_id is not None:
            custom = await self.template_repo.get_active_by_trigger(agent_id, trigger)
            if custom:
                return custom.content

        default = DEFAULT_REPLY_TEMPLATES.get(trigger)
        if default:
            return default["content"]

        return "Let me connect you with our team. Someone will be with you shortly."
