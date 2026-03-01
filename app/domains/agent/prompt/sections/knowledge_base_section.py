from __future__ import annotations

from app.domains.agent.services.agent_context_loader import AgentRunContext


class KnowledgeBaseSection:
    def render(self, ctx: AgentRunContext) -> str:
        if not ctx.knowledge_entries:
            return ""
        lines = ["\n--- Knowledge Base ---"]
        for entry in ctx.knowledge_entries:
            lines.append(f"Q: {entry.question}\nA: {entry.answer}")
        return "\n".join(lines)
