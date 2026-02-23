from __future__ import annotations

from typing import Any

from app.domains.agent.tools.base import BaseTool, ToolContext


class EscalateTool(BaseTool):
    @property
    def name(self) -> str:
        return "escalate"

    @property
    def description(self) -> str:
        return (
            "Escalate this conversation to a human team member. "
            "Use when you cannot help the customer or they request to speak with a person."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Brief explanation of why you are escalating"},
            },
            "required": ["reason"],
        }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict:
        return {
            "escalate": True,
            "reason": arguments.get("reason", "Customer requested human assistance"),
        }
