from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domains.agent.services.agent_context_loader import AgentRunContext


class PromptSection(Protocol):
    """A single concern that contributes zero or more lines to the system prompt."""

    def render(self, ctx: AgentRunContext) -> str: ...
