from __future__ import annotations

import datetime as _dt

from app.domains.agent.services.agent_context_loader import AgentRunContext


class DateTimeSection:
    def render(self, ctx: AgentRunContext) -> str:
        now = _dt.datetime.now()
        return (
            f"\n--- Current Date & Time ---\n"
            f"Today is {now.strftime('%A, %B %d, %Y')}. "
            f"Current time is {now.strftime('%H:%M')}."
        )
