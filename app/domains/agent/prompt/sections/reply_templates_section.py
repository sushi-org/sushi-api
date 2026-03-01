from __future__ import annotations

from app.domains.agent.services.agent_context_loader import AgentRunContext


class ReplyTemplatesSection:
    def render(self, ctx: AgentRunContext) -> str:
        if not ctx.templates:
            return ""

        skip_greeting = (
            ctx.customer_history is not None
            and ctx.customer_history.is_returning
            and ctx.is_new_conversation
        )

        lines = [
            "\n--- Response Templates ---",
            "Use these templates to structure your responses for the corresponding scenarios:",
        ]
        for trigger, content in ctx.templates.items():
            if skip_greeting and trigger == "greeting":
                continue
            lines.append(f"When {trigger.replace('_', ' ')}: \"{content}\"")
        return "\n".join(lines)
