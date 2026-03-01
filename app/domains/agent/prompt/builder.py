from __future__ import annotations

from app.domains.agent.prompt.base import PromptSection
from app.domains.agent.services.agent_context_loader import AgentRunContext


class SystemPromptBuilder:
    """Assembles a system prompt from an ordered list of PromptSection objects.

    Usage:
        builder = SystemPromptBuilder(sections=[
            DateTimeSection(),
            ToolRulesSection(),
            CustomerProfileSection(),
            KnowledgeBaseSection(),
            ReplyTemplatesSection(),
            BusinessContextSection(),
        ])
        prompt = builder.build(ctx)
    """

    def __init__(self, sections: list[PromptSection]) -> None:
        self._sections = sections

    def build(self, ctx: AgentRunContext) -> str:
        parts: list[str] = [ctx.agent.system_prompt]
        for section in self._sections:
            block = section.render(ctx)
            if block:
                parts.append(block)
        return "\n".join(parts)
